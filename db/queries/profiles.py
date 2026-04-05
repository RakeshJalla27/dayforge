from db.connection import get_pool


def list_profiles() -> list[dict]:
    with get_pool().connection() as conn:
        rows = conn.execute(
            "SELECT id, name, color FROM profiles ORDER BY created_at"
        ).fetchall()
    return [{"id": r[0], "name": r[1], "color": r[2]} for r in rows]


def create_profile(id_: str, name: str, color: str) -> None:
    with get_pool().connection() as conn:
        conn.execute(
            "INSERT INTO profiles (id, name, color) VALUES (%s, %s, %s)",
            (id_, name, color),
        )


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
