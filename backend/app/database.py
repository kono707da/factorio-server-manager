import aiosqlite
import os
from app.config import DATABASE_PATH, DATA_DIR, DEFAULT_FACTORIO_DIR, DEFAULT_SAVES_DIR, DEFAULT_BACKUPS_DIR, DEFAULT_LOGS_DIR

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
            factorio_dir TEXT NOT NULL DEFAULT '/opt/factorio',
            saves_dir TEXT NOT NULL DEFAULT '/opt/factorio/saves',
            backups_dir TEXT NOT NULL DEFAULT '/opt/factorio/backups',
            logs_dir TEXT NOT NULL DEFAULT '/opt/factorio/logs',
            server_port INTEGER NOT NULL DEFAULT 34197,
            game_password TEXT DEFAULT '',
            max_players INTEGER NOT NULL DEFAULT 10,
            require_user_verification INTEGER NOT NULL DEFAULT 1,
            autosave_interval INTEGER NOT NULL DEFAULT 5,
            autosave_slots INTEGER NOT NULL DEFAULT 5,
            factorio_username TEXT DEFAULT '',
            factorio_token TEXT DEFAULT '',
            auto_pause INTEGER NOT NULL DEFAULT 1
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

    await db.execute(
        "UPDATE settings SET factorio_dir = ? WHERE factorio_dir = '' OR factorio_dir IS NULL",
        [DEFAULT_FACTORIO_DIR],
    )
    await db.execute(
        "UPDATE settings SET saves_dir = ? WHERE saves_dir = '' OR saves_dir IS NULL",
        [DEFAULT_SAVES_DIR],
    )
    await db.execute(
        "UPDATE settings SET backups_dir = ? WHERE backups_dir = '' OR backups_dir IS NULL",
        [DEFAULT_BACKUPS_DIR],
    )
    await db.execute(
        "UPDATE settings SET logs_dir = ? WHERE logs_dir = '' OR logs_dir IS NULL",
        [DEFAULT_LOGS_DIR],
    )

    try:
        await db.execute("ALTER TABLE settings ADD COLUMN factorio_username TEXT DEFAULT ''")
    except Exception:
        pass
    try:
        await db.execute("ALTER TABLE settings ADD COLUMN factorio_token TEXT DEFAULT ''")
    except Exception:
        pass
    try:
        await db.execute("ALTER TABLE settings ADD COLUMN auto_pause INTEGER NOT NULL DEFAULT 1")
    except Exception:
        pass

    await db.commit()


async def close_db():
    global _db
    if _db:
        await _db.close()
        _db = None
