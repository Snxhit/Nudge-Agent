import os
import aiosqlite
from datetime import datetime, timezone, timedelta
from pathlib import Path
from bot.config import config
from contextlib import asynccontextmanager

SCHEMA_PATH = Path(__file__).with_name("schema.sql")

def utc_now() -> datetime:
    return datetime.now(timezone.utc)

def to_iso(dt: datetime) -> datetime:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def parse_iso(iso_str: str) -> datetime:
    clean = iso_str.strip().replace("Z", "+00:00")
    dt = datetime.fromisoformat(clean)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)

def _compute_lead_reminder_iso(due_dt: datetime) -> str | None:
    lead_dt = due_dt - timedelta(hours=6)
    if lead_dt > utc_now():
        return to_iso(lead_dt)
    return None

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
            INSERT INTO platform_links (platform, platform_user_id, chat_id, username, account_id, linked_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (platform, p_uid, c_id, username, account_id, now),
        )

        await db.commit()
        return account_id

async def insert_note(acc_id: int, title: str, content: str, category: str = "general") -> int:
    async with get_db() as db:
        cursor = await db.execute(
            """
            INSERT INTO notes (account_id, category, title, content, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (acc_id, category.lower().strip(), title.strip(), content.strip(), to_iso(utc_now()))
        )
        await db.commit()
        return cursor.lastrowid

async def query_notes(acc_id: int, keyword: str) -> list[dict]:
    pattern = f"%{keyword.strip()}%"
    async with get_db() as db:
        cursor = await db.execute(
            """
            SELECT id, category, title, content, created_at
            FROM notes
            WHERE account_id = ? AND (title LIKE ? OR content LIKE ? OR category LIKE ?)
            ORDER BY id DESC
            LIMIT 15
            """,
            (acc_id, pattern, pattern, pattern),
        )
        return [dict(r) for r in await cursor.fetchall()]

async def fetch_recent_notes(acc_id: int, limit: int = 10) -> list[dict]:
    async with get_db() as db:
        cursor = await db.execute(
            """
            SELECT id, category, title, content, created_at
            FROM notes
            WHERE account_id = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (acc_id, limit),
        )
        return [dict(r) for r in await cursor.fetchall()]

async def insert_reminder(acc_id: int, platform: str, chat_id: str | int, message: str, due_at_iso: str, todo_id: int | None = None):
    async with get_db() as db:
        cursor = await db.execute(
            """
            INSERT INTO reminders (account_id, todo_id, message, due_at, platform, chat_id, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (acc_id, todo_id, message.strip(), due_at_iso, platform, str(chat_id), to_iso(utc_now())),
        )
        await db.commit()
        return cursor.lastrowid

async def fetch_due_reminders(platform: str = "telegram") -> list[dict]:
    now_iso = to_iso(utc_now())

    async with get_db() as db:
        cursor = await db.execute(
            """
            SELECT id, account_id, todo_id, message, due_at, chat_id
            FROM reminders
            WHERE platform = ? AND is_sent = 0 AND due_at <= ?
            ORDER BY due_at ASC
            """,
            (platform, now_iso),
        )
        return [dict(r) for r in await cursor.fetchall()]

async def mark_reminder_sent(reminder_id: int):
    async with get_db() as db:
        await db.execute("UPDATE reminders SET is_sent = 1 WHERE id = ?", (reminder_id,))
        await db.commit()

async def insert_todo(acc_id: int, title: str, due_at_iso: str, platform: str, chat_id: str | int) -> dict:
    now_iso = to_iso(utc_now())
    due_dt = parse_iso(due_at_iso)
    normalized_due = to_iso(due_dt)
    lead_iso = _compute_lead_reminder_iso(due_dt)

    async with get_db() as db:
        cursor = await db.execute(
            """
            INSERT INTO todos (account_id, title, due_at, status, source_platform, source_chat_id, created_at)
            VALUES (?, ?, ?, 'active', ?, ?, ?)
            """,
            (acc_id, title.strip(), normalized_due, platform, str(chat_id), now_iso),
        )
        todo_id = cursor.lastrowid

        if lead_iso:
            await db.execute(
                """
                INSERT INTO reminders (account_id, todo_id, message, due_at, platform, chat_id, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (acc_id, todo_id, f"Todo due in 6 hours: {title.strip()}", lead_iso, platform, str(chat_id), now_iso),
            )

        await db.commit()
        return {
            "todo_id": todo_id,
            "title": title.strip(),
            "due_at_utc": normalized_due,
            "reminder_scheduled_utc": lead_iso,
        }

async def fetch_active_todos(acc_id: int) -> list[dict]:
    async with get_db() as db:
        cursor = await db.execute(
            """
            SELECT id, title, due_at, status, created_at
            FROM todos
            WHERE account_id = ? AND status IN ('active', 'overdue_prompted')
            ORDER BY due_at ASC
            """,
            (acc_id,),
        )
        return [dict(r) for r in await cursor.fetchall()]

async def update_todos(acc_id: int, todo_id: int, new_title: str | None = None, new_due_at: str | None = None) -> dict | None:
    async with get_db() as db:
        cursor = await db.execute("SELECT * FROM todos WHERE id = ? AND account_id = ?", (todo_id, acc_id))
        row = await cursor.fetchone()
        if not row:
            return None

        # todo: editing the todo

async def complete_todo(acc_id: int, todo_id: int) -> bool:
    async with get_db() as db:
        cursor = await db.execute(
            """
            UPDATE todos
            SET status = 'completed'
            WHERE id = ? AND account_id = ? AND status != 'completed'
            """,
            (todo_id, acc_id),
        )
        if cursor.rowcount == 0:
            return False

        await db.execute("DELETE FROM reminders WHERE todo_id = ? AND is_sent = 0", (todo_id,))
        await db.commit()
        return True

async def delete_todo(acc_id: int, todo_id: int) -> bool:
    async with get_db() as db:
        cursor = await db.execute("DELETE FROM todos WHERE id = ? AND account_id = ?", (todo_id, acc_id))
        await db.commit()
        return cursor.rowcount > 0