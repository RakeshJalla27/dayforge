# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

MiFocus (branded "DayForge") is a personal life planning web app for tracking daily schedules, habits, and learning goals. Runs on a Raspberry Pi backed by PostgreSQL. No frontend build step — plain vanilla JS.

## Running the App

```bash
# Docker (Pi or any Linux box)
docker compose up -d

# Local dev
uv run python server.py    # requires DATABASE_URL in .env
bash start.sh              # same, with uv/python3 fallback
```

Opens on http://localhost:8765.

## Dependency Management (uv)

```bash
uv sync                      # install all deps into .venv
uv sync --group dev          # include dev deps (ruff)
uv add <package>             # add runtime dep → updates pyproject.toml
uv add --group dev <pkg>     # add dev dep
uv run ruff check server.py  # lint
uv run ruff format server.py # format
```

Runtime deps: `psycopg[binary,pool]`, `python-dotenv`. Dev deps: `ruff`.

## Environment

Copy `.env.example` → `.env`. Required variable: `DATABASE_URL`. Optional: `ANTHROPIC_API_KEY` (enables Plan My Week), `PORT` (default 8765).

## Database

PostgreSQL 16. Schema lives in `db/migrations/0001_initial.sql`. Migrations run automatically on startup via `db/migrate.py` — tracked in `schema_migrations` table.

One-time import of legacy JSON data:
```bash
uv run python db/import_json.py
```

## Architecture

**Backend** — `server.py` is a single-file Python HTTP server (stdlib only, no frameworks). Loads `.env` on startup, runs migrations, inits a psycopg3 connection pool, then serves requests.

**DB layer** (`db/`):
- `connection.py` — `ConnectionPool` (min 1, max 5); call `init_pool()` before use
- `migrate.py` — applies `db/migrations/*.sql` in lexicographic order, skipping already-applied files
- `queries/profiles.py`, `queries/schedule.py`, `queries/habits.py`, `queries/learning.py` — one module per domain; all functions take `profile_id` as first arg

**API routing** in `server.py` uses two dispatch dicts:
```python
_READERS = { "schedule": schedule_q.get_schedule, ... }
_WRITERS = { "schedule": schedule_q.save_schedule, ... }
```
Adding a new data domain = add migration + query module + two entries in these dicts.

**API routes:**

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/profiles` | List profiles |
| POST | `/api/profiles` | Create profile |
| DELETE | `/api/profiles/{id}` | Delete profile |
| GET | `/api/{profileId}/{key}` | Read profile data |
| POST | `/api/{profileId}/{key}` | Write profile data |
| POST | `/api/{profileId}/plan-week` | AI week plan via Claude Haiku |

Valid `{key}` values: `schedule`, `habits`, `habits-config`, `learning`, `topics-config`.

**Frontend** — `public/index.html` is the entire client. Plain vanilla JS. On load fetches all data for the active profile. Five tab views: Today, Week, Habits, Learning, Edit.

## Key Implementation Details

- POST writes use **replace-all semantics** (DELETE + INSERT in a transaction) to match the old JSON overwrite behaviour — the frontend sends the full payload every time.
- `psycopg3` returns `datetime.date` → `str(date)` = `"YYYY-MM-DD"`, `datetime.time` → `str(time)[:5]` = `"HH:MM"`, `decimal.Decimal` → `float()`. All conversions happen inside the query functions so `server.py` always serialises plain Python dicts.
- Time block colors: `wellness`, `learning`, `work`, `commute`, `chores`, `personal`, `blocked`, `sleep`.
- All date keys use ISO format `YYYY-MM-DD`.
- `body_metrics`, `workout_sessions`, `workout_sets` tables exist in the schema for future health tracking — not yet wired to the API.

## Docker

`compose.yml` runs `app` + `db` (postgres:16-alpine). `DATABASE_URL` is injected by compose and overrides any value in `.env`. The `pgdata` volume persists data across restarts.

```bash
docker compose up -d             # start
docker compose logs -f app       # logs
docker compose restart app       # after code change
docker compose exec db pg_dump -U dayforge dayforge > backup.sql  # backup
```
