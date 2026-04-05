# DayForge

A personal life-planning web app for managing daily schedules, habits, and learning goals. Runs entirely on a Raspberry Pi, backed by PostgreSQL.

---

## Features

| Feature | Description |
|---------|-------------|
| **Today** | Hour-by-hour timeline with a live "now" indicator showing your current block |
| **Week** | 7-day schedule overview; AI-generated focus/tip per day via "Plan My Week" |
| **Habits** | 28-day heatmap with streak counter; one-click check-off per day |
| **Learning** | Progress bars toward hour targets; session logging with notes |
| **Edit** | Full CRUD for schedule time blocks across weekday / Saturday / Sunday templates |
| **Profiles** | Multiple user profiles, each with independent data |

---

## Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.13, stdlib HTTP server |
| Database | PostgreSQL 16 |
| Python driver | psycopg3 (`psycopg[binary,pool]`) |
| Package manager | [uv](https://docs.astral.sh/uv/) |
| Containers | Docker + Docker Compose |
| Frontend | Vanilla JS/HTML/CSS — single file, no build step |

---

## Requirements

- [Docker](https://docs.docker.com/engine/install/) and Docker Compose v2
- [uv](https://docs.astral.sh/uv/) (for local dev without Docker)
- An `ANTHROPIC_API_KEY` (optional — only needed for "Plan My Week")

---

## Raspberry Pi Setup

### 1. Install Docker on the Pi

```bash
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
# Log out and back in, then verify:
docker run --rm hello-world
```

### 2. Clone the repo and configure

```bash
git clone <repo-url> dayforge
cd dayforge
cp .env.example .env
```

Edit `.env` — the only required change is a strong `DB_PASSWORD`:

```dotenv
DB_PASSWORD=choose_a_strong_password
ANTHROPIC_API_KEY=sk-ant-...   # optional
```

### 3. (First time only) Import existing JSON data

If you have existing data in `data/profiles/`, import it into Postgres before starting the full app:

```bash
# Start only the database
docker compose up -d db

# Wait for Postgres to be ready, then import
docker compose run --rm \
  -e DATABASE_URL=postgresql://dayforge:${DB_PASSWORD}@db:5432/dayforge \
  app python db/import_json.py
```

Skip this step if you have no prior data.

### 4. Start the app

```bash
docker compose up -d
```

Open **http://\<pi-ip-address\>:8765** from any device on your network.

To find your Pi's IP: `hostname -I`

### 5. Auto-start on boot

Docker's `restart: unless-stopped` policy means the app comes back automatically after a reboot. No extra configuration needed.

### 6. Useful commands

```bash
docker compose logs -f app      # tail app logs
docker compose logs -f db       # tail Postgres logs
docker compose restart app      # restart after a code change
docker compose pull             # pull latest images
docker compose down             # stop everything (data persists in pgdata volume)
docker compose down -v          # stop AND wipe all data (destructive)
```

---

## Running on Mac (for testing)

The same Docker Compose setup used on the Pi works identically on Mac. This is the recommended way to test before deploying to the Pi — same images, same flow, no surprises.

### 1. Install Docker Desktop

Download from [docker.com/products/docker-desktop](https://www.docker.com/products/docker-desktop/) and start it.

### 2. Configure and start

```bash
cp .env.example .env
# Edit .env — set DB_PASSWORD to anything, e.g. DB_PASSWORD=testpass

docker compose up -d
```

Open **http://localhost:8765**.

### 3. Import existing data (if any)

```bash
docker compose up -d db   # start db only first

docker compose run --rm \
  -e DATABASE_URL=postgresql://dayforge:${DB_PASSWORD}@db:5432/dayforge \
  app python db/import_json.py

docker compose up -d      # start everything
```

### 4. Iterating on code

After editing `server.py` or anything in `db/`:

```bash
docker compose up -d --build app    # rebuild image and restart
```

After editing `public/index.html` (frontend only):

```bash
# No restart needed — just hard-refresh the browser (Cmd+Shift+R)
```

---

## Local Development (Mac/Linux, without Docker)

### Install uv

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Install dependencies

```bash
uv sync        # installs runtime + dev deps into .venv
```

### Start a local Postgres

```bash
# Using Docker (easiest):
docker run -d --name dayforge-db \
  -e POSTGRES_DB=dayforge \
  -e POSTGRES_USER=dayforge \
  -e POSTGRES_PASSWORD=yourpassword \
  -p 5432:5432 \
  postgres:16-alpine
```

### Configure and run

```bash
cp .env.example .env
# Edit .env:
#   DATABASE_URL=postgresql://dayforge:yourpassword@localhost:5432/dayforge

# Import existing JSON data (if any)
uv run python db/import_json.py

# Start the server
uv run python server.py
```

Open **http://localhost:8765**.

---

## Dependency Management

```bash
uv add <package>              # add runtime dependency
uv add --group dev <package>  # add dev-only dependency
uv sync                       # sync .venv with pyproject.toml
uv run ruff check server.py   # lint
uv run ruff format server.py  # format
```

---

## Project Structure

```
dayforge/
├── server.py                   # HTTP server + REST API
├── pyproject.toml              # project config, dependencies, ruff settings
├── Dockerfile                  # ARM64 + AMD64 compatible image
├── compose.yml                 # app + postgres services
├── .env.example                # config template (copy to .env)
├── public/
│   └── index.html              # entire frontend (HTML + CSS + JS)
├── db/
│   ├── connection.py           # psycopg3 connection pool
│   ├── migrate.py              # migration runner (runs on every startup)
│   ├── import_json.py          # one-time JSON → Postgres import script
│   ├── migrations/
│   │   └── 0001_initial.sql    # full schema
│   └── queries/
│       ├── profiles.py
│       ├── schedule.py
│       ├── habits.py
│       └── learning.py
└── data/                       # legacy JSON files (unused after import)
```

---

## Database Schema

### Active tables

| Table | Purpose |
|-------|---------|
| `profiles` | User profiles |
| `schedule_blocks` | Time blocks per day type (weekday / saturday / sunday) |
| `habit_config` | Habit definitions per profile |
| `habit_logs` | Daily check-offs (`profile_id, date, habit_id, completed`) |
| `topic_config` | Learning topic definitions per profile |
| `learning_sessions` | Learning log (`topic_id, date, hours, notes`) |
| `schema_migrations` | Tracks which SQL migrations have been applied |

### Future tables (already in schema, ready to use)

| Table | Purpose |
|-------|---------|
| `body_metrics` | Any body measurement over time (`metric, value, unit, date`) — weight, BMI, body fat %, waist, etc. |
| `workout_sessions` | Workout session header (name, date, duration) |
| `workout_sets` | Individual sets per exercise (reps, weight_kg, duration_sec) |

`body_metrics` uses an entity-attribute-value pattern so adding a new measurement (sleep score, HRV, etc.) requires no schema change — just log it with a new `metric` name.

---

## REST API

All endpoints served on `http://localhost:8765`.

### Profiles

| Method | Path | Body | Response |
|--------|------|------|----------|
| `GET` | `/api/profiles` | — | `[{id, name, color}]` |
| `POST` | `/api/profiles` | `{name, color}` | `{id, name, color}` |
| `DELETE` | `/api/profiles/{id}` | — | `{ok: true}` |

Deleting the last profile returns `400`.

### Profile data

| Method | Path | Body | Response |
|--------|------|------|----------|
| `GET` | `/api/{profileId}/{key}` | — | JSON data |
| `POST` | `/api/{profileId}/{key}` | JSON data | `{ok: true}` |

Valid `{key}` values: `schedule`, `habits`, `habits-config`, `learning`, `topics-config`

### AI week plan

| Method | Path | Response |
|--------|------|----------|
| `POST` | `/api/{profileId}/plan-week` | `{summary, totalLearningHours, days[]}` |

Requires `ANTHROPIC_API_KEY`. Returns `400` if the key is missing.

---

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `DATABASE_URL` | Yes | Postgres connection string |
| `DB_PASSWORD` | Yes (Docker) | Password for the Postgres container |
| `PORT` | No | HTTP port (default: `8765`) |
| `ANTHROPIC_API_KEY` | No | Enables "Plan My Week" AI feature |

---

## Backups

Postgres data lives in the `pgdata` Docker volume. To back it up:

```bash
# Dump to a file
docker compose exec db pg_dump -U dayforge dayforge > backup_$(date +%F).sql

# Restore from a dump
docker compose exec -T db psql -U dayforge dayforge < backup_2026-04-05.sql
```

---

## TODO

- Cloud deployment (AWS EC2 + RDS) once the Pi setup is stable
- Analytics endpoints for habits and learning trends
- Health & workout tracking UI (schema is already in place)
- Viz dashboard for learning progress and physical metrics
