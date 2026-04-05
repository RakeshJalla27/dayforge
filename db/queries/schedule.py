from db.connection import get_pool


def get_schedule(profile_id: str) -> dict:
    with get_pool().connection() as conn:
        rows = conn.execute(
            """
            SELECT day_type, start_time, end_time, name, category
            FROM   schedule_blocks
            WHERE  profile_id = %s
            ORDER  BY day_type, start_time
            """,
            (profile_id,),
        ).fetchall()

    result: dict = {"weekday": [], "saturday": [], "sunday": []}
    for day_type, start, end, name, category in rows:
        # psycopg3 returns datetime.time objects; format as "HH:MM"
        result[day_type].append({
            "start":    str(start)[:5],
            "end":      str(end)[:5],
            "name":     name,
            "category": category,
        })
    return result


def save_schedule(profile_id: str, data: dict) -> None:
    with get_pool().connection() as conn:
        with conn.transaction():
            conn.execute(
                "DELETE FROM schedule_blocks WHERE profile_id = %s", (profile_id,)
            )
            for day_type in ("weekday", "saturday", "sunday"):
                for block in data.get(day_type, []):
                    conn.execute(
                        """
                        INSERT INTO schedule_blocks
                            (profile_id, day_type, start_time, end_time, name, category)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        """,
                        (
                            profile_id,
                            day_type,
                            block["start"],
                            block["end"],
                            block["name"],
                            block["category"],
                        ),
                    )
