from fastapi import APIRouter
from app.database import get_db
from app.schemas import SettingsUpdate
from app.config import DEFAULT_FACTORIO_DIR, DEFAULT_SAVES_DIR, DEFAULT_BACKUPS_DIR, DEFAULT_LOGS_DIR

router = APIRouter(prefix="/api/config", tags=["config"])

_PATH_DEFAULTS = {
    "factorio_dir": DEFAULT_FACTORIO_DIR,
    "saves_dir": DEFAULT_SAVES_DIR,
    "backups_dir": DEFAULT_BACKUPS_DIR,
    "logs_dir": DEFAULT_LOGS_DIR,
}


@router.get("")
async def get_config():
    db = await get_db()
    cursor = await db.execute("SELECT * FROM settings WHERE id = 1")
    row = await cursor.fetchone()
    if not row:
        return {}
    row_dict = dict(row)
    for field, default in _PATH_DEFAULTS.items():
        if not row_dict.get(field):
            row_dict[field] = default
    row_dict["require_user_verification"] = bool(row_dict["require_user_verification"])
    row_dict["auto_pause"] = bool(row_dict.get("auto_pause", 1))
    return row_dict


@router.put("")
async def update_config(req: SettingsUpdate):
    db = await get_db()
    updates = []
    params = []

    field_map = {
        "factorio_dir": "factorio_dir",
        "saves_dir": "saves_dir",
        "backups_dir": "backups_dir",
        "logs_dir": "logs_dir",
        "server_port": "server_port",
        "game_password": "game_password",
        "max_players": "max_players",
        "autosave_interval": "autosave_interval",
        "autosave_slots": "autosave_slots",
    }

    for py_field, db_field in field_map.items():
        value = getattr(req, py_field, None)
        if value is not None:
            updates.append(f"{db_field} = ?")
            params.append(value)

    if req.require_user_verification is not None:
        updates.append("require_user_verification = ?")
        params.append(1 if req.require_user_verification else 0)

    if req.auto_pause is not None:
        updates.append("auto_pause = ?")
        params.append(1 if req.auto_pause else 0)

    if updates:
        await db.execute(
            f"UPDATE settings SET {', '.join(updates)} WHERE id = 1", params
        )
        await db.commit()

    cursor = await db.execute("SELECT * FROM settings WHERE id = 1")
    row = await cursor.fetchone()
    row_dict = dict(row) if row else {}
    row_dict["require_user_verification"] = bool(row_dict.get("require_user_verification", True))
    row_dict["auto_pause"] = bool(row_dict.get("auto_pause", 1))
    return row_dict
