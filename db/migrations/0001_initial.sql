-- ── Profiles ────────────────────────────────────────────────────────────
CREATE TABLE profiles (
    id         TEXT        PRIMARY KEY,
    name       TEXT        NOT NULL,
    color      TEXT        NOT NULL DEFAULT '#3b82f6',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ── Schedule ─────────────────────────────────────────────────────────────
CREATE TABLE schedule_blocks (
    id         BIGSERIAL PRIMARY KEY,
    profile_id TEXT      NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    day_type   TEXT      NOT NULL CHECK (day_type IN ('weekday', 'saturday', 'sunday')),
    start_time TIME      NOT NULL,
    end_time   TIME      NOT NULL,
    name       TEXT      NOT NULL,
    category   TEXT      NOT NULL
);

CREATE INDEX idx_schedule_profile ON schedule_blocks (profile_id, day_type);

-- ── Habits ───────────────────────────────────────────────────────────────
CREATE TABLE habit_config (
    id         TEXT    NOT NULL,
    profile_id TEXT    NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    name       TEXT    NOT NULL,
    icon       TEXT,
    duration   TEXT,
    sort_order INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (id, profile_id)
);

CREATE TABLE habit_logs (
    profile_id TEXT    NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    date       DATE    NOT NULL,
    habit_id   TEXT    NOT NULL,
    completed  BOOLEAN NOT NULL DEFAULT false,
    PRIMARY KEY (profile_id, date, habit_id)
);

CREATE INDEX idx_habit_logs_profile_date ON habit_logs (profile_id, date);

-- ── Learning ─────────────────────────────────────────────────────────────
CREATE TABLE topic_config (
    id          TEXT      NOT NULL,
    profile_id  TEXT      NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    name        TEXT      NOT NULL,
    priority    INTEGER   NOT NULL DEFAULT 1,
    color       TEXT      NOT NULL DEFAULT '#3b82f6',
    target_hours NUMERIC(6,1) NOT NULL DEFAULT 0,
    active_days INTEGER[] NOT NULL DEFAULT '{}',
    sort_order  INTEGER   NOT NULL DEFAULT 0,
    PRIMARY KEY (id, profile_id)
);

CREATE TABLE learning_sessions (
    id         BIGSERIAL    PRIMARY KEY,
    profile_id TEXT         NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    topic_id   TEXT         NOT NULL,
    date       DATE         NOT NULL,
    hours      NUMERIC(4,2) NOT NULL,
    notes      TEXT,
    logged_at  TIMESTAMPTZ  NOT NULL DEFAULT now()
);

CREATE INDEX idx_learning_profile_topic ON learning_sessions (profile_id, topic_id, date);

-- ── Health (ready for future use) ────────────────────────────────────────
CREATE TABLE body_metrics (
    id         BIGSERIAL    PRIMARY KEY,
    profile_id TEXT         NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    date       DATE         NOT NULL,
    metric     TEXT         NOT NULL,
    value      NUMERIC(8,2) NOT NULL,
    unit       TEXT,
    notes      TEXT,
    logged_at  TIMESTAMPTZ  NOT NULL DEFAULT now()
);

CREATE INDEX idx_body_metrics_profile ON body_metrics (profile_id, metric, date);

CREATE TABLE workout_sessions (
    id           BIGSERIAL   PRIMARY KEY,
    profile_id   TEXT        NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    date         DATE        NOT NULL,
    name         TEXT        NOT NULL,
    duration_min INTEGER,
    notes        TEXT,
    logged_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE workout_sets (
    id           BIGSERIAL    PRIMARY KEY,
    session_id   BIGINT       NOT NULL REFERENCES workout_sessions(id) ON DELETE CASCADE,
    exercise     TEXT         NOT NULL,
    set_number   INTEGER      NOT NULL,
    reps         INTEGER,
    weight_kg    NUMERIC(5,2),
    duration_sec INTEGER,
    notes        TEXT
);

CREATE INDEX idx_workout_sessions_profile ON workout_sessions (profile_id, date);
