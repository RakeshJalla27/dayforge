from db.connection import get_pool


def _row_to_dict(r) -> dict:
    return {
        "id":       r[0],
        "name":     r[1],
        "color":    r[2],
        "dob":      str(r[3]) if r[3] else None,
        "gender":   r[4],
        "kid_mode": bool(r[5]),
    }


def list_profiles() -> list[dict]:
    with get_pool().connection() as conn:
        rows = conn.execute(
            "SELECT id, name, color, dob, gender, kid_mode FROM profiles ORDER BY created_at"
        ).fetchall()
    return [_row_to_dict(r) for r in rows]


def create_profile(id_: str, name: str, color: str,
                   dob: str | None = None,
                   gender: str | None = None,
                   kid_mode: bool = False) -> dict:
    with get_pool().connection() as conn:
        row = conn.execute(
            """INSERT INTO profiles (id, name, color, dob, gender, kid_mode)
               VALUES (%s, %s, %s, %s, %s, %s)
               RETURNING id, name, color, dob, gender, kid_mode""",
            (id_, name, color, dob or None, gender or None, kid_mode),
        ).fetchone()
    return _row_to_dict(row)


def update_profile(id_: str, name: str, color: str,
                   dob: str | None = None,
                   gender: str | None = None,
                   kid_mode: bool = False) -> dict:
    with get_pool().connection() as conn:
        row = conn.execute(
            """UPDATE profiles
               SET name=%s, color=%s, dob=%s, gender=%s, kid_mode=%s
               WHERE id=%s
               RETURNING id, name, color, dob, gender, kid_mode""",
            (name, color, dob or None, gender or None, kid_mode, id_),
        ).fetchone()
    return _row_to_dict(row)


def delete_profile(id_: str) -> None:
    with get_pool().connection() as conn:
        conn.execute("DELETE FROM profiles WHERE id = %s", (id_,))


def count_profiles() -> int:
    with get_pool().connection() as conn:
        return conn.execute("SELECT COUNT(*) FROM profiles").fetchone()[0]


def profile_exists(id_: str) -> bool:
    with get_pool().connection() as conn:
        return conn.execute(
            "SELECT 1 FROM profiles WHERE id = %s", (id_,)
        ).fetchone() is not None
