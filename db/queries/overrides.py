import json

from db.connection import get_pool


def get_overrides(profile_id: str) -> dict:
    """Return all date overrides as {YYYY-MM-DD: [blocks]}."""
    with get_pool().connection() as conn:
        rows = conn.execute(
            "SELECT date, blocks FROM schedule_overrides WHERE profile_id = %s",
            (profile_id,),
        ).fetchall()
    return {str(date): blocks for date, blocks in rows}


def save_overrides(profile_id: str, data: dict) -> None:
    """Replace all overrides for this profile. data = {YYYY-MM-DD: [blocks]}."""
    with get_pool().connection() as conn:
        with conn.transaction():
            conn.execute(
                "DELETE FROM schedule_overrides WHERE profile_id = %s", (profile_id,)
            )
            for date_str, blocks in data.items():
                conn.execute(
                    """
                    INSERT INTO schedule_overrides (profile_id, date, blocks)
                    VALUES (%s, %s, %s)
                    """,
                    (profile_id, date_str, json.dumps(blocks)),
                )
