import os
from psycopg_pool import ConnectionPool

_pool: ConnectionPool | None = None


def init_pool() -> None:
    global _pool
    url = os.environ["DATABASE_URL"]
    _pool = ConnectionPool(url, min_size=1, max_size=5, open=True)


def get_pool() -> ConnectionPool:
    if _pool is None:
        raise RuntimeError("Database pool not initialised — call init_pool() first")
    return _pool


def close_pool() -> None:
    global _pool
    if _pool is not None:
        _pool.close()
        _pool = None
