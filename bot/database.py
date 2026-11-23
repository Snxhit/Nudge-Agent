import os
import aiosqlite
from datetime import datetime, timezone
from pathlib import Path
from bot.config import config
from contextlib import asynccontextmanager

SCHEMA_PATH = Path(__file__).with_name("schema.sql")

@asynccontextmanager
async def get_db():
    db_dir = os.path.dirname(config.database_path)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)

    db = await aiosqlite.connect(config.database_path)
    db.row_factory = aiosqlite.Row
    await db.execute("PRAGMA journal_mode=WAL;")
    await db.execute("PRAGMA foreign_keys=ON;")
    try:
        yield db
    finally:
        await db.close()

def utc_now() -> datetime:
    return datetime.now(timezone.utc)

def to_iso(dt: datetime) -> datetime:
    # todo: strftime() thingy
    return dt.astimezone(timezone.utc)

async def init_db() -> None:
    schema_sql = SCHEMA_PATH.read_text(encoding="utf-8")
    async with get_db() as db:
        await db.executescript(schema_sql)
        await db.commit()

async def get_or_create_account(platform: str, platform_uid: str | int, chat_id: str | int, username: str | None = None) -> int:
    p_uid = str(platform_uid)
    c_id = str(chat_id)
    now = to_iso(utc_now())

    async with get_db() as db:
        cursor = await db.execute(
            "SELECT account_id FROM platform_links WHERE platform = ? AND platform_user_id = ?",
            (platform, p_uid),
        )
        row = await cursor.fetchone()
        if row:
            account_id = row["account_id"]
            await db.execute(
                """
                UPDATE platform_links
                SET chat_id = ?, username = ?
                WHERE platform = ? AND platform_user_id = ?
                """,
                (c_id, username, platform, p_uid),
            )
            await db.commit()
            return account_id

        acc_cursor = await db.execute(
            "INSERT INTO accounts (timezone, created_at) VALUES ('UTC', ?)",
            (now,),
        )
        account_id = acc_cursor.lastrowid

        await db.execute(
            """
            INSERT INTO platforms_links (platforms, platform_user_id, chat_id, username, account_id, linked_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (platform, p_uid, c_id, username, account_id, now),
        )

        await db.commit()
        return account_id