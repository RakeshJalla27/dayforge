-- Add extended profile fields (non-destructive: existing rows get NULL/FALSE defaults)
ALTER TABLE profiles ADD COLUMN IF NOT EXISTS dob      DATE;
ALTER TABLE profiles ADD COLUMN IF NOT EXISTS gender   TEXT;
ALTER TABLE profiles ADD COLUMN IF NOT EXISTS kid_mode BOOLEAN NOT NULL DEFAULT FALSE;
