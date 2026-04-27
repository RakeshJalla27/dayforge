#!/usr/bin/env python3
"""
DayForge Life Planner — Local Server
Multi-profile support backed by PostgreSQL.
Run: python3 server.py  →  http://localhost:8765
"""

import json
import os
import urllib.error
import urllib.request
from http.server import HTTPServer, SimpleHTTPRequestHandler

from dotenv import load_dotenv

import db.migrate as migrate
from db.connection import close_pool, init_pool
from db.queries import habits as habits_q
from db.queries import learning as learning_q
from db.queries import overrides as overrides_q
from db.queries import profiles as profiles_q
from db.queries import schedule as schedule_q

load_dotenv()

PORT       = int(os.environ.get("PORT", 8765))
PUBLIC_DIR = os.path.join(os.path.dirname(__file__), "public")

# Maps API key names to (reader, writer) query functions
_READERS = {
    "schedule":      schedule_q.get_schedule,
    "habits":        habits_q.get_habits,
    "habits-config": habits_q.get_habit_config,
    "learning":      learning_q.get_learning,
    "topics-config": learning_q.get_topic_config,
    "overrides":     overrides_q.get_overrides,
}
_WRITERS = {
    "schedule":      schedule_q.save_schedule,
    "habits":        habits_q.save_habits,
    "habits-config": habits_q.save_habit_config,
    "learning":      learning_q.save_learning,
    "topics-config": learning_q.save_topic_config,
    "overrides":     overrides_q.save_overrides,
}


# ── Anthropic ────────────────────────────────────────────────────────────

def get_api_key() -> str:
    return os.environ.get("ANTHROPIC_API_KEY", "").strip()


def call_claude(prompt: str, api_key: str) -> str:
    payload = json.dumps({
        "model": "claude-haiku-4-5-20251001",
        "max_tokens": 2048,
        "messages": [{"role": "user", "content": prompt}],
    }).encode()

    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=payload,
        headers={
            "x-api-key":           api_key,
            "anthropic-version":   "2023-06-01",
            "content-type":        "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        result = json.loads(resp.read())
    return result["content"][0]["text"]


def build_week_prompt(body: dict) -> str:
    days    = body.get("days", [])
    topics  = body.get("topics", [])
    habits  = body.get("habits", [])
    today   = body.get("today", "")
    profile = body.get("profileName", "the user")

    day_lines = []
    for d in days:
        blocks = d.get("blocks", [])
        bl = ", ".join(
            f"{b['start']}–{b['end']} {b['name']} [{b['category']}]"
            for b in blocks
        ) or "No blocks"
        day_lines.append(f"  {d['label']} ({d['dayType']}): {bl}")

    topic_lines = []
    for t in topics:
        dn = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
        ds = ", ".join(dn[d] for d in t.get("days", []))
        topic_lines.append(
            f"  - {t['name']} (Priority {t['priority']}, {t['target']}h goal, "
            f"days: {ds}, {t.get('hours', 0):.1f}h logged)"
        )

    habit_lines = [f"  - {h['name']} ({h['dur']})" for h in habits]

    return f"""You are a personal productivity assistant planning a weekly schedule for {profile}.

Today is {today}.

WEEKLY SCHEDULE (actual time blocks per day):
{chr(10).join(day_lines)}

LEARNING TOPICS (priority order):
{chr(10).join(topic_lines)}

DAILY HABITS:
{chr(10).join(habit_lines)}

Generate a smart weekly plan. For each day return:
- "focus": primary theme or learning topic for the day
- "highlights": 2–4 key things happening (reference actual block names)
- "tip": one specific, actionable suggestion for that day

Respond ONLY with valid JSON, no extra text:
{{
  "summary": "one sentence overview of the week",
  "totalLearningHours": <number>,
  "days": [
    {{
      "date": "YYYY-MM-DD",
      "label": "Monday",
      "focus": "...",
      "highlights": ["...", "..."],
      "tip": "..."
    }}
  ]
}}"""


# ── HTTP Handler ─────────────────────────────────────────────────────────

class Handler(SimpleHTTPRequestHandler):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=PUBLIC_DIR, **kwargs)

    def log_message(self, fmt, *args):
        msg = fmt % args
        if "/api/" in msg:
            print(f"  {msg}")

    # ── Routing ──────────────────────────────────────────────────────────

    def do_GET(self):
        if self.path.startswith("/api/"):
            self._route_get()
        else:
            super().do_GET()

    def do_POST(self):
        if self.path.startswith("/api/"):
            self._route_post()
        else:
            self.send_error(404)

    def do_PATCH(self):
        if self.path.startswith("/api/profiles/"):
            self._handle_update_profile(self._read_body())
        else:
            self.send_error(404)

    def do_DELETE(self):
        if self.path.startswith("/api/profiles/"):
            self._handle_delete_profile()
        else:
            self.send_error(404)

    def do_OPTIONS(self):
        self.send_response(200)
        self._cors()
        self.end_headers()

    def _route_get(self):
        parts = self.path[len("/api/"):].strip("/").split("/")

        # GET /api/profiles
        if parts == ["profiles"]:
            self._json_ok(profiles_q.list_profiles())
            return

        # GET /api/{profileId}/{key}
        if len(parts) == 2:
            profile_id, key = parts
            self._read_profile_data(profile_id, key)
            return

        self._json_response(404, {"error": "Unknown route"})

    def _route_post(self):
        parts = self.path[len("/api/"):].strip("/").split("/")
        body  = self._read_body()

        # POST /api/profiles  →  create profile
        if parts == ["profiles"]:
            self._handle_create_profile(body)
            return

        # POST /api/{profileId}/plan-week
        if len(parts) == 2 and parts[1] == "plan-week":
            self._handle_plan_week(body)
            return

        # POST /api/{profileId}/{key}  →  save data
        if len(parts) == 2:
            profile_id, key = parts
            self._write_profile_data(profile_id, key, body)
            return

        self._json_response(404, {"error": "Unknown route"})

    # ── Profile CRUD ─────────────────────────────────────────────────────

    def _handle_create_profile(self, body: dict):
        name     = (body.get("name") or "").strip()
        color    = body.get("color", "#3b82f6")
        dob      = body.get("dob") or None
        gender   = body.get("gender") or None
        kid_mode = bool(body.get("kid_mode", False))
        if not name:
            self._json_response(400, {"error": "Name is required"})
            return

        pid = "".join(c.lower() if c.isalnum() else "_" for c in name)[:20]

        existing_ids = {p["id"] for p in profiles_q.list_profiles()}
        base, n = pid, 1
        while pid in existing_ids:
            pid = f"{base}_{n}"
            n += 1

        profile = profiles_q.create_profile(pid, name, color, dob, gender, kid_mode)
        self._json_ok(profile)

    def _handle_update_profile(self, body: dict):
        pid      = self.path[len("/api/profiles/"):].strip("/")
        name     = (body.get("name") or "").strip()
        color    = body.get("color", "#3b82f6")
        dob      = body.get("dob") or None
        gender   = body.get("gender") or None
        kid_mode = bool(body.get("kid_mode", False))
        if not name:
            self._json_response(400, {"error": "Name is required"})
            return
        if not profiles_q.profile_exists(pid):
            self._json_response(404, {"error": "Profile not found"})
            return
        profile = profiles_q.update_profile(pid, name, color, dob, gender, kid_mode)
        self._json_ok(profile)

    def _handle_delete_profile(self):
        pid = self.path[len("/api/profiles/"):].strip("/")

        if profiles_q.count_profiles() <= 1:
            self._json_response(400, {"error": "Cannot delete the last profile"})
            return

        profiles_q.delete_profile(pid)
        self._json_ok({"ok": True})

    # ── Profile data read / write ─────────────────────────────────────────

    def _read_profile_data(self, profile_id: str, key: str):
        if key not in _READERS:
            self._json_response(404, {"error": f"Unknown key: {key}"})
            return
        data = _READERS[key](profile_id)
        self._json_ok(data)

    def _write_profile_data(self, profile_id: str, key: str, data):
        if key not in _WRITERS:
            self._json_response(404, {"error": f"Unknown key: {key}"})
            return
        _WRITERS[key](profile_id, data)
        self._json_ok({"ok": True})

    # ── AI plan ──────────────────────────────────────────────────────────

    def _handle_plan_week(self, body: dict):
        api_key = get_api_key()
        if not api_key:
            self._json_response(400, {"error": "ANTHROPIC_API_KEY not set"})
            return
        try:
            raw  = call_claude(build_week_prompt(body), api_key)
            text = raw.strip()
            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
                text = text.strip()
            self._json_ok(json.loads(text))
        except urllib.error.HTTPError as e:
            err = e.read().decode()
            self._json_response(502, {"error": f"Anthropic error {e.code}: {err}"})
        except json.JSONDecodeError:
            self._json_response(500, {"error": "LLM returned invalid JSON. Try again."})
        except Exception as e:
            self._json_response(500, {"error": str(e)})

    # ── Helpers ──────────────────────────────────────────────────────────

    def _read_body(self) -> dict:
        length = int(self.headers.get("Content-Length", 0))
        raw    = self.rfile.read(length)
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {}

    def _json_ok(self, payload):
        self._json_response(200, payload)

    def _json_response(self, code: int, payload):
        body = json.dumps(payload).encode()
        self.send_response(code)
        self._cors()
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin",  "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")


# ── Entry point ──────────────────────────────────────────────────────────

def main():
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        raise SystemExit(
            "\n  ERROR: DATABASE_URL is not set.\n"
            "  Copy .env.example → .env and fill in your Postgres connection string.\n"
        )

    print("\n  [db] Running migrations...")
    migrate.run(db_url)

    print("  [db] Connecting pool...")
    init_pool()

    # Seed a default profile if the database is empty
    if profiles_q.count_profiles() == 0:
        profiles_q.create_profile("rakesh", "Rakesh", "#3b82f6", kid_mode=False)
        print("  [db] Created default profile: Rakesh")

    server     = HTTPServer(("0.0.0.0", PORT), Handler)
    key_status = "✓ found" if get_api_key() else "✗ not set"
    print(f"\n  DayForge Life Planner")
    print(f"  Server       → http://localhost:{PORT}")
    print(f"  Database     → {db_url.split('@')[-1]}")  # hide credentials
    print(f"  Anthropic    → {key_status}")
    print(f"  Press Ctrl+C to stop\n")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n  Server stopped.")
    finally:
        close_pool()


if __name__ == "__main__":
    main()
