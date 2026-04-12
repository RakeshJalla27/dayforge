-- Per-date schedule overrides
-- When a date has an entry here, it takes precedence over the default
-- weekday/saturday/sunday schedule for that profile.

CREATE TABLE IF NOT EXISTS schedule_overrides (
    id         SERIAL PRIMARY KEY,
    profile_id TEXT    NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    date       DATE    NOT NULL,
    blocks     JSONB   NOT NULL DEFAULT '[]',
    UNIQUE (profile_id, date)
);

CREATE INDEX IF NOT EXISTS idx_overrides_profile ON schedule_overrides (profile_id);
