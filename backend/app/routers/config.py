from fastapi import APIRouter
from app.database import get_db
from app.schemas import SettingsUpdate

router = APIRouter(prefix="/api/config", tags=["config"])


@router.get("")
async def get_config():
    db = await get_db()
    cursor = await db.execute("SELECT * FROM settings WHERE id = 1")
    row = await cursor.fetchone()
    if not row:
        return {}
    row_dict = dict(row)
    row_dict["require_user_verification"] = bool(row_dict["require_user_verification"])
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

    if updates:
        await db.execute(
            f"UPDATE settings SET {', '.join(updates)} WHERE id = 1", params
        )
        await db.commit()

    cursor = await db.execute("SELECT * FROM settings WHERE id = 1")
    row = await cursor.fetchone()
    row_dict = dict(row) if row else {}
    row_dict["require_user_verification"] = bool(row_dict.get("require_user_verification", True))
    return row_dict
