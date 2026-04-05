#!/usr/bin/env python3
"""
One-time migration: import existing JSON data files → PostgreSQL.

Run ONCE after setting up the database:
    uv run python db/import_json.py

Safe to re-run — skips profiles that already exist in the database.
"""

import json
import os
import sys

# Make sure the project root is on the path when run directly
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from dotenv import load_dotenv

load_dotenv()

import db.migrate as migrate
from db.connection import close_pool, init_pool
from db.queries import habits as habits_q
from db.queries import learning as learning_q
from db.queries import profiles as profiles_q
from db.queries import schedule as schedule_q

DATA_DIR     = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
PROFILES_DIR = os.path.join(DATA_DIR, "profiles")


def _load_json(path: str, default):
    if not os.path.exists(path):
        return default
    with open(path) as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            print(f"  [warn] Could not parse {path}, skipping")
            return default


def import_profile(profile: dict) -> None:
    pid   = profile["id"]
    name  = profile["name"]
    color = profile.get("color", "#3b82f6")
    pdir  = os.path.join(PROFILES_DIR, pid)

    if profiles_q.profile_exists(pid):
        print(f"  [import] Profile '{name}' ({pid}) exists — overwriting data")
    else:
        profiles_q.create_profile(pid, name, color)
        print(f"  [import] Profile: {name} ({pid})")

    # Schedule
    schedule = _load_json(os.path.join(pdir, "schedule.json"), {})
    if schedule:
        schedule_q.save_schedule(pid, schedule)
        total = sum(len(v) for v in schedule.values() if isinstance(v, list))
        print(f"    schedule      → {total} blocks")

    # Habits config
    habits_cfg = _load_json(os.path.join(pdir, "habits-config.json"), [])
    if habits_cfg:
        habits_q.save_habit_config(pid, habits_cfg)
        print(f"    habits-config → {len(habits_cfg)} habits")

    # Habit logs
    habits = _load_json(os.path.join(pdir, "habits.json"), {})
    if habits:
        habits_q.save_habits(pid, habits)
        print(f"    habit logs    → {len(habits)} days")

    # Topics config
    topics_cfg = _load_json(os.path.join(pdir, "topics-config.json"), [])
    if topics_cfg:
        learning_q.save_topic_config(pid, topics_cfg)
        print(f"    topics-config → {len(topics_cfg)} topics")

    # Learning sessions
    learning = _load_json(os.path.join(pdir, "learning.json"), {})
    if learning:
        learning_q.save_learning(pid, learning)
        total_sessions = sum(
            len(v.get("sessions", [])) for v in learning.values()
        )
        print(f"    learning      → {total_sessions} sessions")


def main():
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        raise SystemExit(
            "\n  ERROR: DATABASE_URL not set. Copy .env.example → .env first.\n"
        )

    profiles_file = os.path.join(DATA_DIR, "profiles.json")
    if not os.path.exists(profiles_file):
        raise SystemExit(
            f"\n  ERROR: {profiles_file} not found.\n"
            "  Nothing to import — no existing JSON data detected.\n"
        )

    profiles = _load_json(profiles_file, [])
    if not profiles:
        raise SystemExit("\n  No profiles found in profiles.json.\n")

    print("\n  [db] Running migrations...")
    migrate.run(db_url)

    print("  [db] Connecting...")
    init_pool()

    print(f"\n  Importing {len(profiles)} profile(s) from {DATA_DIR}/\n")
    for profile in profiles:
        import_profile(profile)

    close_pool()
    print("\n  Done. You can now start the server and your data will be intact.\n")


if __name__ == "__main__":
    main()
