import json
from datetime import datetime, timezone
from typing import Optional

import asyncpg


# ─────────────────────────── pool helper ────────────────────────────

_pool: asyncpg.Pool | None = None


async def get_pool() -> asyncpg.Pool:
    return _pool


async def set_pool(pool: asyncpg.Pool):
    global _pool
    _pool = pool


# ─────────────────────────── users ──────────────────────────────────

async def get_user(telegram_id: int) -> Optional[asyncpg.Record]:
    async with _pool.acquire() as conn:
        return await conn.fetchrow(
            "SELECT * FROM users WHERE telegram_id = $1", telegram_id
        )


async def create_user(
    telegram_id: int,
    phone: str,
    username: Optional[str],
    first_name: Optional[str],
    last_name: Optional[str],
    full_name: Optional[str],
    language_code: Optional[str],
    is_bot: bool,
    role: str = "client",
) -> asyncpg.Record:
    async with _pool.acquire() as conn:
        return await conn.fetchrow(
            """
            INSERT INTO users
                (telegram_id, phone, username, first_name, last_name,
                 full_name, language_code, is_bot, role)
            VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9)
            ON CONFLICT (telegram_id) DO UPDATE
                SET phone = EXCLUDED.phone
            RETURNING *
            """,
            telegram_id, phone, username, first_name, last_name,
            full_name, language_code, is_bot, role,
        )


async def update_last_ad(telegram_id: int, dt: datetime):
    async with _pool.acquire() as conn:
        await conn.execute(
            "UPDATE users SET last_ad_at = $1 WHERE telegram_id = $2", dt, telegram_id
        )


async def extend_subscription(telegram_id: int, until: datetime):
    async with _pool.acquire() as conn:
        await conn.execute(
            """
            UPDATE users
            SET subscription_until = $1
            WHERE telegram_id = $2
            """,
            until, telegram_id,
        )


async def get_all_users() -> list[asyncpg.Record]:
    async with _pool.acquire() as conn:
        return await conn.fetch(
            "SELECT * FROM users WHERE role IN ('client', 'admin') ORDER BY created_at DESC"
        )


async def get_user_by_id(user_id: int) -> Optional[asyncpg.Record]:
    """Get user by DB telegram_id (same as telegram_id in our schema)."""
    return await get_user(user_id)


async def set_role(telegram_id: int, role: str):
    async with _pool.acquire() as conn:
        await conn.execute(
            "UPDATE users SET role = $1 WHERE telegram_id = $2", role, telegram_id
        )


# ─────────────────────────── ads ────────────────────────────────────

async def create_ad(
    user_id: int,
    media_file_ids: list[str],
    text: Optional[str],
) -> asyncpg.Record:
    async with _pool.acquire() as conn:
        return await conn.fetchrow(
            """
            INSERT INTO ads (user_id, media_file_ids, text, status)
            VALUES ($1, $2::jsonb, $3, 'approved')
            RETURNING *
            """,
            user_id, json.dumps(media_file_ids), text,
        )


async def mark_ad_sent(ad_id: int, sent_at: datetime):
    async with _pool.acquire() as conn:
        await conn.execute(
            "UPDATE ads SET sent_at = $1 WHERE id = $2", sent_at, ad_id
        )


# ─────────────────────────── blackout ───────────────────────────────

async def add_blackout(start: datetime, end: datetime, created_by: int) -> asyncpg.Record:
    async with _pool.acquire() as conn:
        return await conn.fetchrow(
            """
            INSERT INTO blackout_periods (start_datetime, end_datetime, created_by)
            VALUES ($1, $2, $3)
            RETURNING *
            """,
            start, end, created_by,
        )


async def get_active_blackout(now: datetime) -> Optional[asyncpg.Record]:
    async with _pool.acquire() as conn:
        return await conn.fetchrow(
            """
            SELECT * FROM blackout_periods
            WHERE start_datetime <= $1 AND end_datetime >= $1
            LIMIT 1
            """,
            now,
        )


async def get_all_blackouts() -> list[asyncpg.Record]:
    async with _pool.acquire() as conn:
        return await conn.fetch(
            "SELECT * FROM blackout_periods ORDER BY start_datetime DESC LIMIT 20"
        )


async def delete_blackout(blackout_id: int):
    async with _pool.acquire() as conn:
        await conn.execute(
            "DELETE FROM blackout_periods WHERE id = $1", blackout_id
        )