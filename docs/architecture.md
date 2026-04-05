# DayForge — Architecture & Flow Diagrams

Diagrams are written in [Mermaid](https://mermaid.js.org/). They render natively in GitHub, VS Code (with the Markdown Preview Mermaid extension), and Obsidian.

---

## 1. System Architecture

How the pieces fit together at the highest level.

```mermaid
graph TD
    subgraph Client["Client (Browser — any device on the network)"]
        UI["public/index.html\nHTML + CSS + Vanilla JS"]
    end

    subgraph Docker["Docker Compose (Mac / Raspberry Pi)"]
        direction TB
        App["app container\nPython HTTP Server\nport 8765"]
        DB["db container\nPostgreSQL 16\nport 5432 (internal)"]
        App -- "psycopg3\nConnectionPool" --> DB
    end

    Anthropic["Anthropic API\nclaude-haiku-4-5\n(Plan My Week — optional)"]

    UI -- "HTTP REST\nlocalhost:8765" --> App
    App -- "HTTPS (only when\nPlan My Week used)" --> Anthropic
```

**Key points:**
- The browser and the server are on the same local network — no internet required for normal use.
- PostgreSQL is never exposed outside Docker; only the app container can reach it.
- Anthropic is the only external dependency, and only when the AI planning feature is used.

---

## 2. Docker Compose Startup Sequence

What happens from `docker compose up -d` to a ready server.

```mermaid
sequenceDiagram
    actor User
    participant DC  as Docker Compose
    participant DB  as db container<br/>(postgres:16-alpine)
    participant App as app container<br/>(Python)
    participant PG  as PostgreSQL process

    User->>DC: docker compose up -d

    DC->>DB: Start db container
    DB->>PG: Init data directory (first run)<br/>or load pgdata volume (subsequent)
    loop healthcheck every 5s
        DC->>PG: pg_isready -U dayforge
    end
    PG-->>DC: healthy

    DC->>App: Start app container (depends_on: db healthy)
    App->>App: load_dotenv() — read .env
    App->>PG: db/migrate.py — apply pending *.sql files
    Note over App,PG: schema_migrations table tracks<br/>which files have already run
    App->>App: init_pool() — open psycopg3 ConnectionPool
    App->>PG: COUNT(*) FROM profiles
    alt database is empty (first run)
        App->>PG: INSERT default profile "Rakesh"
    end
    App->>App: HTTPServer.serve_forever()<br/>on 0.0.0.0:8765

    User->>App: Open http://pi-ip:8765
    App-->>User: Serve public/index.html
```

---

## 3. Internal Server Architecture

How a request moves through `server.py` and the `db/` layer.

```mermaid
graph TD
    Req["Incoming HTTP Request"]

    subgraph server.py
        Handler["Handler\nSimpleHTTPRequestHandler"]
        Router["Router\ndo_GET / do_POST / do_DELETE"]

        subgraph "Static files"
            Static["Serve public/\nindex.html, assets"]
        end

        subgraph "API routes"
            ProfileCRUD["Profile CRUD\nGET /api/profiles\nPOST /api/profiles\nDELETE /api/profiles/id"]
            DataRW["Data Read/Write\nGET /api/profileId/key\nPOST /api/profileId/key"]
            PlanWeek["Plan My Week\nPOST /api/profileId/plan-week"]
        end
    end

    subgraph "db/queries/"
        QP["profiles.py"]
        QS["schedule.py"]
        QH["habits.py"]
        QL["learning.py"]
    end

    Pool["db/connection.py\nConnectionPool\nmin=1 max=5"]
    PG[("PostgreSQL")]
    Claude["Anthropic API\nClaude Haiku"]

    Req --> Handler
    Handler -->|"/api/*"| Router
    Handler -->|"everything else"| Static

    Router --> ProfileCRUD
    Router --> DataRW
    Router --> PlanWeek

    ProfileCRUD --> QP
    DataRW -->|"_READERS / _WRITERS\ndispatch dict"| QP & QS & QH & QL

    QP & QS & QH & QL --> Pool --> PG
    PlanWeek -->|"build_week_prompt()\ncall_claude()"| Claude
```

**The dispatch dicts** in `server.py` are the key extensibility point:
```python
_READERS = { "schedule": schedule_q.get_schedule, "habits": habits_q.get_habits, ... }
_WRITERS = { "schedule": schedule_q.save_schedule, "habits": habits_q.save_habits, ... }
```
Adding a new data domain = new migration + new query module + two lines in these dicts. Nothing else changes.

---

## 4. API Request Lifecycle

A complete round-trip for the most common operation: reading profile data.

```mermaid
sequenceDiagram
    participant B  as Browser
    participant S  as server.py
    participant Q  as queries/habits.py
    participant P  as ConnectionPool
    participant DB as PostgreSQL

    B->>S: GET /api/rakesh/habits

    S->>S: _route_get()
    S->>S: parts = ["rakesh", "habits"]
    S->>S: key = "habits" → valid in _READERS

    S->>Q: habits_q.get_habits("rakesh")
    Q->>P: pool.connection()
    P->>DB: SELECT date, habit_id, completed<br/>FROM habit_logs<br/>WHERE profile_id = 'rakesh'<br/>ORDER BY date
    DB-->>P: rows [(2026-04-05, exercise, true), ...]
    P-->>Q: rows

    Q->>Q: Build dict<br/>{"2026-04-05": {"exercise": true}}
    Q-->>S: dict

    S->>S: json.dumps(dict)
    S-->>B: 200 OK  Content-Type: application/json
```

**Write path** (e.g. POST /api/rakesh/habits) uses DELETE + INSERT in a single transaction — full replacement, matching the old JSON-overwrite behaviour. The frontend always sends the full payload.

---

## 5. Database Schema

Entity-relationship diagram showing all tables and their foreign keys.

```mermaid
erDiagram
    profiles {
        text    id          PK
        text    name
        text    color
        timestamptz created_at
    }

    schedule_blocks {
        bigserial  id         PK
        text       profile_id FK
        text       day_type
        time       start_time
        time       end_time
        text       name
        text       category
    }

    habit_config {
        text    id         PK
        text    profile_id PK
        text    name
        text    icon
        text    duration
        int     sort_order
    }

    habit_logs {
        text    profile_id PK
        date    date       PK
        text    habit_id   PK
        boolean completed
    }

    topic_config {
        text     id           PK
        text     profile_id   PK
        text     name
        int      priority
        text     color
        numeric  target_hours
        int[]    active_days
        int      sort_order
    }

    learning_sessions {
        bigserial   id         PK
        text        profile_id FK
        text        topic_id
        date        date
        numeric     hours
        text        notes
        timestamptz logged_at
    }

    body_metrics {
        bigserial   id         PK
        text        profile_id FK
        date        date
        text        metric
        numeric     value
        text        unit
        text        notes
        timestamptz logged_at
    }

    workout_sessions {
        bigserial   id           PK
        text        profile_id   FK
        date        date
        text        name
        int         duration_min
        text        notes
        timestamptz logged_at
    }

    workout_sets {
        bigserial id           PK
        bigint    session_id   FK
        text      exercise
        int       set_number
        int       reps
        numeric   weight_kg
        int       duration_sec
        text      notes
    }

    profiles         ||--o{ schedule_blocks   : "has"
    profiles         ||--o{ habit_config      : "has"
    profiles         ||--o{ habit_logs        : "has"
    profiles         ||--o{ topic_config      : "has"
    profiles         ||--o{ learning_sessions : "has"
    profiles         ||--o{ body_metrics      : "has"
    profiles         ||--o{ workout_sessions  : "has"
    workout_sessions ||--o{ workout_sets      : "has"
```

**Notes:**
- `habit_config` and `topic_config` use composite PKs `(id, profile_id)` — same habit/topic ID can exist across different profiles.
- `habit_logs` PK is `(profile_id, date, habit_id)` — one row per habit per day, no duplicates possible.
- `body_metrics` is intentionally flexible: `metric` is a free-form string (`"weight_kg"`, `"bmi"`, `"chest_cm"`, etc.). New measurement types need no schema change.
- Tables `body_metrics`, `workout_sessions`, `workout_sets` are in the schema now but have no API endpoints yet.

---

## 6. Frontend Data Flow

How the single-page frontend loads data, renders tabs, and saves changes.

```mermaid
graph TD
    subgraph "Page Load"
        Load["Browser opens index.html"]
        FetchAll["Fetch all 5 endpoints in parallel\n/schedule  /habits  /habits-config\n/learning  /topics-config"]
        State["In-memory state object\nschedule, habitsData, habitsConfig\nlearningData, topicsConfig"]
        Load --> FetchAll --> State
    end

    subgraph "Tab rendering (read-only from state)"
        State --> Today["Today Tab\nTimeline for current day type\n(weekday / saturday / sunday)\nLive 'now' indicator refreshes every 30s"]
        State --> Week["Week Tab\n7-day grid\nOptional: POST plan-week → Claude Haiku"]
        State --> Habits["Habits Tab\n28-day heatmap per habit\nStreak counter"]
        State --> Learning["Learning Tab\nProgress bar: logged / target hours\nLast 3 sessions shown per topic"]
        State --> Edit["Edit Tab\nFull CRUD form for schedule blocks\nSeparate sub-tabs: Weekday / Sat / Sun"]
    end

    subgraph "User actions (write back to server)"
        Habits  -->|"Click day cell\nToggle complete"| SaveHabits["POST /api/profileId/habits\n(full payload, immediate)"]
        Learning -->|"Log Session modal\nhours + notes"| SaveLearning["POST /api/profileId/learning\n(full payload, immediate)"]
        Edit    -->|"Click 'Save Schedule'"| SaveSchedule["POST /api/profileId/schedule\n(full payload, explicit)"]
    end
```

**Save strategy:**
- Habits and Learning save **immediately and silently** on every user action (toggle, log session).
- Schedule saves only when the user explicitly clicks **Save Schedule** — because edits are in-progress forms that shouldn't auto-commit.

---

## 7. Migration System

How `db/migrate.py` ensures the schema stays in sync on every startup.

```mermaid
flowchart TD
    Start["server.py calls migrate.run(db_url)"]
    Connect["Open psycopg3 connection\n(autocommit=True)"]
    Table["CREATE TABLE IF NOT EXISTS schema_migrations"]
    Scan["Glob db/migrations/*.sql\nSort lexicographically"]

    Start --> Connect --> Table --> Scan

    Scan --> Loop

    Loop{"For each .sql file"}
    Check{"Already in\nschema_migrations?"}
    Skip["Skip"]
    Apply["BEGIN TRANSACTION\nExecute SQL\nINSERT INTO schema_migrations\nCOMMIT"]
    Next["Next file"]
    Done["All files processed\nReturn to main()"]

    Loop --> Check
    Check -->|"Yes"| Skip --> Next
    Check -->|"No"| Apply --> Next
    Next --> Loop
    Loop -->|"No more files"| Done
```

**Adding a new migration:**
1. Create `db/migrations/0002_your_change.sql`
2. Deploy (or restart the server)
3. It applies automatically — no manual `ALTER TABLE` needed.

Naming convention: `NNNN_description.sql` — the leading number controls order.

---

## 8. Component Map

Where to find each piece of functionality in the codebase.

```
┌─────────────────────────────────────────────────────────┐
│                      server.py                          │
│                                                         │
│  ┌─────────────────┐   ┌──────────────────────────────┐ │
│  │   HTTP routing  │   │     Anthropic integration    │ │
│  │  do_GET         │   │  get_api_key()               │ │
│  │  do_POST        │   │  call_claude()               │ │
│  │  do_DELETE      │   │  build_week_prompt()         │ │
│  │  do_OPTIONS     │   └──────────────────────────────┘ │
│  └────────┬────────┘                                    │
│           │ dispatches to                               │
│  ┌────────▼────────────────────────────────────────┐   │
│  │  _READERS / _WRITERS  (dispatch dicts)          │   │
│  └────────┬────────────────────────────────────────┘   │
└───────────┼─────────────────────────────────────────────┘
            │
┌───────────▼─────────────────────────────────────────────┐
│                    db/queries/                          │
│                                                         │
│  profiles.py      schedule.py                          │
│  ├ list_profiles  ├ get_schedule                        │
│  ├ create_profile ╰ save_schedule                       │
│  ├ delete_profile                                       │
│  ╰ count_profiles  habits.py                            │
│                   ├ get_habit_config                    │
│  learning.py      ├ save_habit_config                   │
│  ├ get_topic_config├ get_habits                         │
│  ├ save_topic_config╰ save_habits                       │
│  ├ get_learning                                         │
│  ╰ save_learning                                        │
│                                                         │
└───────────┬─────────────────────────────────────────────┘
            │ all queries use
┌───────────▼──────────────┐
│   db/connection.py       │
│   ConnectionPool         │
│   init_pool()            │
│   get_pool()             │
│   close_pool()           │
└───────────┬──────────────┘
            │
┌───────────▼──────────────┐
│   PostgreSQL             │
│   (Docker container)     │
└──────────────────────────┘
```

---

## Summary

| Concept | Where it lives |
|---------|---------------|
| HTTP routing | `server.py` — `Handler._route_get/post` |
| Dispatch to query functions | `server.py` — `_READERS` / `_WRITERS` dicts |
| Connection management | `db/connection.py` |
| Schema versioning | `db/migrate.py` + `db/migrations/*.sql` |
| Data access per domain | `db/queries/{profiles,schedule,habits,learning}.py` |
| AI week planning | `server.py` — `build_week_prompt()` + `call_claude()` |
| Entire frontend | `public/index.html` |
| Container orchestration | `compose.yml` |
| One-time data import | `db/import_json.py` |
