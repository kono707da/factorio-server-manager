import aiosqlite
import os
from app.config import DATABASE_PATH, DATA_DIR

_db: aiosqlite.Connection | None = None


async def get_db() -> aiosqlite.Connection:
    global _db
    if _db is None:
        os.makedirs(DATA_DIR, exist_ok=True)
        _db = await aiosqlite.connect(DATABASE_PATH)
        _db.row_factory = aiosqlite.Row
        await _db.execute("PRAGMA journal_mode=WAL")
        await _db.execute("PRAGMA foreign_keys=ON")
    return _db


async def init_db():
    db = await get_db()
    await db.executescript("""
        CREATE TABLE IF NOT EXISTS settings (
            id INTEGER PRIMARY KEY DEFAULT 1,
            factorio_dir TEXT NOT NULL DEFAULT '',
            saves_dir TEXT NOT NULL DEFAULT '',
            backups_dir TEXT NOT NULL DEFAULT '',
            logs_dir TEXT NOT NULL DEFAULT '',
            server_port INTEGER NOT NULL DEFAULT 34197,
            game_password TEXT DEFAULT '',
            max_players INTEGER NOT NULL DEFAULT 10,
            require_user_verification INTEGER NOT NULL DEFAULT 1,
            autosave_interval INTEGER NOT NULL DEFAULT 5,
            autosave_slots INTEGER NOT NULL DEFAULT 5
        );

        CREATE TABLE IF NOT EXISTS backup_config (
            id INTEGER PRIMARY KEY DEFAULT 1,
            enabled INTEGER NOT NULL DEFAULT 0,
            interval_hours INTEGER NOT NULL DEFAULT 6,
            max_backups INTEGER NOT NULL DEFAULT 10,
            last_backup_at TEXT
        );

        CREATE TABLE IF NOT EXISTS backup_record (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL,
            source_save TEXT NOT NULL,
            file_size INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS version_info (
            id INTEGER PRIMARY KEY DEFAULT 1,
            current_version TEXT NOT NULL DEFAULT '',
            install_path TEXT NOT NULL DEFAULT '',
            installed_at TEXT NOT NULL DEFAULT (datetime('now'))
        );

        INSERT OR IGNORE INTO settings (id) VALUES (1);
        INSERT OR IGNORE INTO backup_config (id) VALUES (1);
        INSERT OR IGNORE INTO version_info (id) VALUES (1);
    """)
    await db.commit()


async def close_db():
    global _db
    if _db:
        await _db.close()
        _db = None
