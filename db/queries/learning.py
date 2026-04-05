from db.connection import get_pool


# ── Topic config ─────────────────────────────────────────────────────────

def get_topic_config(profile_id: str) -> list[dict]:
    with get_pool().connection() as conn:
        rows = conn.execute(
            """
            SELECT id, name, priority, color, target_hours, active_days
            FROM   topic_config
            WHERE  profile_id = %s
            ORDER  BY priority, sort_order
            """,
            (profile_id,),
        ).fetchall()
    return [
        {
            "id":       r[0],
            "name":     r[1],
            "priority": r[2],
            "color":    r[3],
            "target":   float(r[4]),
            "days":     r[5],  # list[int] from INTEGER[]
        }
        for r in rows
    ]


def save_topic_config(profile_id: str, topics: list[dict]) -> None:
    with get_pool().connection() as conn:
        with conn.transaction():
            conn.execute(
                "DELETE FROM topic_config WHERE profile_id = %s", (profile_id,)
            )
            for i, t in enumerate(topics):
                conn.execute(
                    """
                    INSERT INTO topic_config
                        (id, profile_id, name, priority, color, target_hours, active_days, sort_order)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        t["id"],
                        profile_id,
                        t["name"],
                        t.get("priority", 1),
                        t.get("color", "#3b82f6"),
                        t.get("target", 0),
                        t.get("days", []),
                        i,
                    ),
                )


# ── Learning sessions ────────────────────────────────────────────────────

def get_learning(profile_id: str) -> dict:
    with get_pool().connection() as conn:
        rows = conn.execute(
            """
            SELECT topic_id, date, hours, notes
            FROM   learning_sessions
            WHERE  profile_id = %s
            ORDER  BY topic_id, date
            """,
            (profile_id,),
        ).fetchall()

    result: dict = {}
    for topic_id, date, hours, notes in rows:
        if topic_id not in result:
            result[topic_id] = {"hours": 0.0, "sessions": []}
        h = float(hours)
        result[topic_id]["hours"] = round(result[topic_id]["hours"] + h, 2)
        result[topic_id]["sessions"].append({
            "date":  str(date),  # datetime.date → "YYYY-MM-DD"
            "hours": h,
            "notes": notes or "",
        })
    return result


def save_learning(profile_id: str, data: dict) -> None:
    # data shape: {topicId: {hours: N, sessions: [{date, hours, notes}]}}
    with get_pool().connection() as conn:
        with conn.transaction():
            conn.execute(
                "DELETE FROM learning_sessions WHERE profile_id = %s", (profile_id,)
            )
            for topic_id, topic_data in data.items():
                for session in topic_data.get("sessions", []):
                    conn.execute(
                        """
                        INSERT INTO learning_sessions
                            (profile_id, topic_id, date, hours, notes)
                        VALUES (%s, %s, %s, %s, %s)
                        """,
                        (
                            profile_id,
                            topic_id,
                            session["date"],
                            session["hours"],
                            session.get("notes", "") or None,
                        ),
                    )
