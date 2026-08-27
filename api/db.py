"""
api/db.py
─────────
Raw PostgreSQL query helpers using psycopg2 directly.
Avoids the need for Django ORM migrations on existing ETL-created tables.
"""

import os
import psycopg2
import psycopg2.extras
from django.conf import settings


def _get_conn():
    """Open a fresh psycopg2 connection from Django settings."""
    db = settings.DATABASES["default"]
    return psycopg2.connect(
        dbname   = db["NAME"],
        user     = db["USER"],
        password = db["PASSWORD"],
        host     = db["HOST"],
        port     = db["PORT"],
    )


def search_hardware(query: str, limit: int = 10) -> list[dict]:
    """
    Autocomplete search across cpu_name and gpu_name in hardware_specs.
    Returns list of {type, name} dicts, deduplicated and sorted.
    """
    q = f"%{query.lower().strip()}%"
    sql = """
        SELECT DISTINCT 'cpu' AS type, cpu_name AS name
        FROM hardware_specs
        WHERE LOWER(cpu_name) LIKE %s

        UNION

        SELECT DISTINCT 'gpu' AS type, gpu_name AS name
        FROM hardware_specs
        WHERE LOWER(gpu_name) LIKE %s

        ORDER BY name
        LIMIT %s;
    """
    with _get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, (q, q, limit))
            return [dict(r) for r in cur.fetchall()]


def get_hardware_row(cpu_name: str, gpu_name: str) -> dict | None:
    """
    Fetch the first hardware_specs row matching the given cpu+gpu names.
    Names are compared case-insensitively after normalization.
    Returns a plain dict or None if not found.
    """
    sql = """
        SELECT *
        FROM hardware_specs
        WHERE LOWER(cpu_name) = LOWER(%s)
          AND LOWER(gpu_name) = LOWER(%s)
        LIMIT 1;
    """
    with _get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, (cpu_name.strip(), gpu_name.strip()))
            row = cur.fetchone()
            return dict(row) if row else None


def get_game_genres(game_name: str) -> str:
    """
    Fetch igdb_genres for a game from the games table.
    Matches on game_name_clean (case-insensitive).
    Returns empty string if not found.
    """
    sql = """
        SELECT COALESCE(igdb_genres, '') AS igdb_genres
        FROM games
        WHERE LOWER(game_name_clean) = LOWER(%s)
           OR LOWER(game_name_raw)   = LOWER(%s)
        LIMIT 1;
    """
    with _get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, (game_name.strip(), game_name.strip()))
            row = cur.fetchone()
            return dict(row).get("igdb_genres", "") if row else ""


def list_games(limit: int = 50) -> list[str]:
    """Return all unique clean game names from the games table."""
    sql = "SELECT game_name_clean FROM games ORDER BY game_name_clean LIMIT %s;"
    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (limit,))
            return [r[0] for r in cur.fetchall()]


def get_all_hardware() -> dict:
    """
    Return every distinct CPU name and GPU name from hardware_specs.
    Used by the frontend to pre-load the full list for instant local filtering
    (country-selector pattern — load once, filter locally with zero network lag).

    Returns
    -------
    {
        "cpus": ["amd ryzen 5 1600x", ...],
        "gpus": ["nvidia geforce rtx 2080 ti", ...],
    }
    """
    sql_cpu = "SELECT DISTINCT cpu_name FROM hardware_specs ORDER BY cpu_name;"
    sql_gpu = "SELECT DISTINCT gpu_name FROM hardware_specs ORDER BY gpu_name;"
    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql_cpu)
            cpus = [r[0] for r in cur.fetchall()]
            cur.execute(sql_gpu)
            gpus = [r[0] for r in cur.fetchall()]
    return {"cpus": cpus, "gpus": gpus}
