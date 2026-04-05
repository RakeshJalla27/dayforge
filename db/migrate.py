"""
Applies SQL migration files in db/migrations/ in lexicographic order.
Tracks applied migrations in a schema_migrations table so each file
runs exactly once.
"""

import glob
import os

import psycopg


def run(database_url: str) -> None:
    migrations_dir = os.path.join(os.path.dirname(__file__), "migrations")
    sql_files = sorted(glob.glob(os.path.join(migrations_dir, "*.sql")))

    with psycopg.connect(database_url, autocommit=True) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS schema_migrations (
                filename   TEXT        PRIMARY KEY,
                applied_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )
        """)

        for path in sql_files:
            filename = os.path.basename(path)
            already_applied = conn.execute(
                "SELECT 1 FROM schema_migrations WHERE filename = %s", (filename,)
            ).fetchone()

            if already_applied:
                continue

            with open(path) as f:
                sql = f.read()

            with conn.transaction():
                conn.execute(sql)
                conn.execute(
                    "INSERT INTO schema_migrations (filename) VALUES (%s)", (filename,)
                )

            print(f"  [db] Applied migration: {filename}")
