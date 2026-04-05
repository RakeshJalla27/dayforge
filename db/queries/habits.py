from db.connection import get_pool


# ── Habit config ─────────────────────────────────────────────────────────

def get_habit_config(profile_id: str) -> list[dict]:
    with get_pool().connection() as conn:
        rows = conn.execute(
            """
            SELECT id, name, icon, duration
            FROM   habit_config
            WHERE  profile_id = %s
            ORDER  BY sort_order, id
            """,
            (profile_id,),
        ).fetchall()
    return [{"id": r[0], "name": r[1], "icon": r[2], "dur": r[3]} for r in rows]


def save_habit_config(profile_id: str, habits: list[dict]) -> None:
    with get_pool().connection() as conn:
        with conn.transaction():
            conn.execute(
                "DELETE FROM habit_config WHERE profile_id = %s", (profile_id,)
            )
            for i, h in enumerate(habits):
                conn.execute(
                    """
                    INSERT INTO habit_config (id, profile_id, name, icon, duration, sort_order)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (h["id"], profile_id, h["name"], h.get("icon"), h.get("dur"), i),
                )


# ── Habit logs ───────────────────────────────────────────────────────────

def get_habits(profile_id: str) -> dict:
    with get_pool().connection() as conn:
        rows = conn.execute(
            """
            SELECT date, habit_id, completed
            FROM   habit_logs
            WHERE  profile_id = %s
            ORDER  BY date
            """,
            (profile_id,),
        ).fetchall()

    result: dict = {}
    for date, habit_id, completed in rows:
        key = str(date)  # datetime.date → "YYYY-MM-DD"
        if key not in result:
            result[key] = {}
        result[key][habit_id] = completed
    return result


def save_habits(profile_id: str, data: dict) -> None:
    # data shape: {"YYYY-MM-DD": {"habitId": bool, ...}}
    with get_pool().connection() as conn:
        with conn.transaction():
            conn.execute(
                "DELETE FROM habit_logs WHERE profile_id = %s", (profile_id,)
            )
            for date_str, habits in data.items():
                for habit_id, completed in habits.items():
                    conn.execute(
                        """
                        INSERT INTO habit_logs (profile_id, date, habit_id, completed)
                        VALUES (%s, %s, %s, %s)
                        """,
                        (profile_id, date_str, habit_id, completed),
                    )
