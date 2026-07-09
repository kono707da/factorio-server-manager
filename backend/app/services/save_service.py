import logging
import os
import shutil
from datetime import datetime

from app.database import get_db

logger = logging.getLogger("factorio_manager.save_service")


class SaveService:
    _instance: "SaveService | None" = None

    def __init__(self):
        pass

    @classmethod
    def get_instance(cls) -> "SaveService":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    async def _get_saves_dir(self) -> str:
        db = await get_db()
        cursor = await db.execute("SELECT saves_dir, factorio_dir FROM settings WHERE id = 1")
        row = await cursor.fetchone()
        if not row:
            return ""
        row_dict = dict(row)
        saves_dir = row_dict["saves_dir"]
        if not saves_dir:
            saves_dir = os.path.join(row_dict["factorio_dir"], "saves")
        return saves_dir

    async def list_saves(self, active_save: str = "") -> list[dict]:
        saves_dir = await self._get_saves_dir()
        if not saves_dir or not os.path.isdir(saves_dir):
            logger.warning("存档目录不存在: %s", saves_dir)
            return []

        saves = []
        for f in os.listdir(saves_dir):
            if f.endswith(".zip"):
                path = os.path.join(saves_dir, f)
                stat = os.stat(path)
                saves.append({
                    "filename": f,
                    "size": stat.st_size,
                    "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    "is_active": f == active_save,
                })

        saves.sort(key=lambda x: x["modified"], reverse=True)
        return saves

    async def upload_save(self, filename: str, content: bytes) -> dict:
        saves_dir = await self._get_saves_dir()
        if not saves_dir:
            return {"success": False, "error": "存档目录未配置"}

        os.makedirs(saves_dir, exist_ok=True)
        safe_name = os.path.basename(filename)
        filepath = os.path.join(saves_dir, safe_name)

        try:
            with open(filepath, "wb") as f:
                f.write(content)
            logger.info("存档上传成功: %s", safe_name)
            return {"success": True, "filename": safe_name}
        except Exception as e:
            error_msg = f"存档上传失败: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {"success": False, "error": error_msg}

    async def download_save(self, filename: str) -> tuple[str | None, str]:
        saves_dir = await self._get_saves_dir()
        if not saves_dir:
            return None, "存档目录未配置"

        safe_name = os.path.basename(filename)
        filepath = os.path.join(saves_dir, safe_name)

        if not os.path.isfile(filepath):
            return None, f"存档文件不存在: {safe_name}"

        return filepath, ""

    async def delete_save(self, filename: str) -> dict:
        saves_dir = await self._get_saves_dir()
        if not saves_dir:
            return {"success": False, "error": "存档目录未配置"}

        safe_name = os.path.basename(filename)
        filepath = os.path.join(saves_dir, safe_name)

        if not os.path.isfile(filepath):
            return {"success": False, "error": f"存档文件不存在: {safe_name}"}

        try:
            os.remove(filepath)
            logger.info("存档删除成功: %s", safe_name)
            return {"success": True}
        except Exception as e:
            error_msg = f"存档删除失败: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {"success": False, "error": error_msg}

    async def create_save(self, save_name: str) -> dict:
        saves_dir = await self._get_saves_dir()
        if not saves_dir:
            return {"success": False, "error": "存档目录未配置"}

        os.makedirs(saves_dir, exist_ok=True)
        if not save_name.endswith(".zip"):
            save_name += ".zip"

        safe_name = os.path.basename(save_name)
        filepath = os.path.join(saves_dir, safe_name)

        if os.path.isfile(filepath):
            return {"success": False, "error": f"存档文件已存在: {safe_name}"}

        try:
            with open(filepath, "wb") as f:
                pass
            logger.info("空存档创建成功: %s", safe_name)
            return {"success": True, "filename": safe_name}
        except Exception as e:
            error_msg = f"创建存档失败: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {"success": False, "error": error_msg}
