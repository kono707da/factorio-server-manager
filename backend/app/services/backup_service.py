import logging
import os
import shutil
from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.database import get_db
from app.config import DEFAULT_SAVES_DIR, DEFAULT_BACKUPS_DIR, DEFAULT_FACTORIO_DIR

logger = logging.getLogger("factorio_manager.backup_service")


class BackupService:
    _instance: "BackupService | None" = None

    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self._job_id = "factorio_backup"

    @classmethod
    def get_instance(cls) -> "BackupService":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    async def _get_dirs(self) -> tuple[str, str]:
        db = await get_db()
        cursor = await db.execute(
            "SELECT saves_dir, backups_dir, factorio_dir FROM settings WHERE id = 1"
        )
        row = await cursor.fetchone()
        if not row:
            return DEFAULT_SAVES_DIR, DEFAULT_BACKUPS_DIR
        row_dict = dict(row)
        factorio_dir = row_dict["factorio_dir"] or DEFAULT_FACTORIO_DIR
        saves_dir = row_dict["saves_dir"] or os.path.join(factorio_dir, "saves")
        backups_dir = row_dict["backups_dir"] or os.path.join(factorio_dir, "backups")
        if not os.path.isabs(saves_dir):
            saves_dir = os.path.join(factorio_dir, saves_dir)
        if not os.path.isabs(backups_dir):
            backups_dir = os.path.join(factorio_dir, backups_dir)
        return saves_dir, backups_dir

    async def get_config(self) -> dict:
        db = await get_db()
        cursor = await db.execute("SELECT * FROM backup_config WHERE id = 1")
        row = await cursor.fetchone()
        if not row:
            return {"enabled": False, "interval_hours": 6, "max_backups": 10, "last_backup_at": None}
        row_dict = dict(row)
        return {
            "enabled": bool(row_dict["enabled"]),
            "interval_hours": row_dict["interval_hours"],
            "max_backups": row_dict["max_backups"],
            "last_backup_at": row_dict["last_backup_at"],
        }

    async def update_config(self, enabled: bool | None = None, interval_hours: int | None = None, max_backups: int | None = None) -> dict:
        db = await get_db()
        updates = []
        params = []
        if enabled is not None:
            updates.append("enabled = ?")
            params.append(1 if enabled else 0)
        if interval_hours is not None:
            updates.append("interval_hours = ?")
            params.append(interval_hours)
        if max_backups is not None:
            updates.append("max_backups = ?")
            params.append(max_backups)

        if updates:
            await db.execute(
                f"UPDATE backup_config SET {', '.join(updates)} WHERE id = 1", params
            )
            await db.commit()

        config = await self.get_config()
        self._reschedule(config)
        return config

    def _reschedule(self, config: dict):
        if self.scheduler.get_job(self._job_id):
            self.scheduler.remove_job(self._job_id)

        if config["enabled"]:
            self.scheduler.add_job(
                self._do_backup,
                IntervalTrigger(hours=config["interval_hours"]),
                id=self._job_id,
                replace_existing=True,
            )
            logger.info("定时备份已启用，间隔 %d 小时", config["interval_hours"])

    async def start_scheduler(self):
        config = await self.get_config()
        if config["enabled"]:
            self._reschedule(config)
        if not self.scheduler.running:
            self.scheduler.start()
            logger.info("备份调度器已启动")

    async def stop_scheduler(self):
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)
            logger.info("备份调度器已停止")

    async def _do_backup(self):
        logger.info("开始执行定时备份...")
        result = await self.trigger_backup()
        if result.get("success"):
            logger.info("定时备份完成: %s", result.get("filename"))
        else:
            logger.error("定时备份失败: %s", result.get("error"))

    async def trigger_backup(self, source_save: str | None = None) -> dict:
        saves_dir, backups_dir = await self._get_dirs()
        if not saves_dir or not backups_dir:
            return {"success": False, "error": "存档目录或备份目录未配置"}

        os.makedirs(backups_dir, exist_ok=True)

        if not source_save:
            saves = [f for f in os.listdir(saves_dir) if f.endswith(".zip")] if os.path.isdir(saves_dir) else []
            if not saves:
                return {"success": False, "error": "没有找到存档文件"}
            source_save = max(
                saves, key=lambda f: os.path.getmtime(os.path.join(saves_dir, f))
            )

        source_path = os.path.join(saves_dir, source_save)
        if not os.path.isfile(source_path):
            return {"success": False, "error": f"存档文件不存在: {source_save}"}

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_name = os.path.splitext(source_save)[0]
        backup_filename = f"{base_name}_{timestamp}.zip"
        backup_path = os.path.join(backups_dir, backup_filename)

        try:
            shutil.copy2(source_path, backup_path)
            file_size = os.path.getsize(backup_path)

            db = await get_db()
            await db.execute(
                "INSERT INTO backup_record (filename, source_save, file_size) VALUES (?, ?, ?)",
                (backup_filename, source_save, file_size),
            )
            await db.execute(
                "UPDATE backup_config SET last_backup_at = ? WHERE id = 1",
                (datetime.now().isoformat(),),
            )
            await db.commit()

            await self._cleanup_old_backups()

            logger.info("备份成功: %s -> %s", source_save, backup_filename)
            return {"success": True, "filename": backup_filename, "size": file_size}

        except Exception as e:
            error_msg = f"备份失败: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {"success": False, "error": error_msg}

    async def _cleanup_old_backups(self):
        db = await get_db()
        cursor = await db.execute("SELECT max_backups FROM backup_config WHERE id = 1")
        row = await cursor.fetchone()
        if not row:
            return
        max_backups = dict(row)["max_backups"]

        cursor = await db.execute(
            "SELECT id, filename FROM backup_record ORDER BY created_at DESC"
        )
        records = [dict(r) for r in await cursor.fetchall()]

        if len(records) > max_backups:
            _, backups_dir = await self._get_dirs()
            for record in records[max_backups:]:
                if backups_dir:
                    filepath = os.path.join(backups_dir, record["filename"])
                    if os.path.isfile(filepath):
                        os.remove(filepath)
                await db.execute("DELETE FROM backup_record WHERE id = ?", (record["id"],))
            await db.commit()
            logger.info("清理了 %d 个旧备份", len(records) - max_backups)

    async def list_backups(self) -> list[dict]:
        db = await get_db()
        cursor = await db.execute(
            "SELECT id, filename, source_save, file_size, created_at FROM backup_record ORDER BY created_at DESC"
        )
        return [dict(r) for r in await cursor.fetchall()]

    async def download_backup(self, filename: str) -> tuple[str | None, str]:
        _, backups_dir = await self._get_dirs()
        if not backups_dir:
            return None, "备份目录未配置"

        safe_name = os.path.basename(filename)
        filepath = os.path.join(backups_dir, safe_name)

        if not os.path.isfile(filepath):
            return None, f"备份文件不存在: {safe_name}"

        return filepath, ""

    async def restore_backup(self, filename: str) -> dict:
        saves_dir, backups_dir = await self._get_dirs()
        if not saves_dir or not backups_dir:
            return {"success": False, "error": "存档目录或备份目录未配置"}

        os.makedirs(saves_dir, exist_ok=True)

        safe_name = os.path.basename(filename)
        backup_path = os.path.join(backups_dir, safe_name)

        if not os.path.isfile(backup_path):
            return {"success": False, "error": f"备份文件不存在: {safe_name}"}

        db = await get_db()
        cursor = await db.execute(
            "SELECT source_save FROM backup_record WHERE filename = ?", (safe_name,)
        )
        row = await cursor.fetchone()
        target_name = dict(row)["source_save"] if row else safe_name

        target_path = os.path.join(saves_dir, target_name)

        try:
            shutil.copy2(backup_path, target_path)
            logger.info("备份恢复成功: %s -> %s", safe_name, target_name)
            return {"success": True, "restored_to": target_name}
        except Exception as e:
            error_msg = f"备份恢复失败: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {"success": False, "error": error_msg}

    async def delete_backup(self, filename: str) -> dict:
        _, backups_dir = await self._get_dirs()
        if not backups_dir:
            return {"success": False, "error": "备份目录未配置"}

        safe_name = os.path.basename(filename)
        filepath = os.path.join(backups_dir, safe_name)

        try:
            if os.path.isfile(filepath):
                os.remove(filepath)
            db = await get_db()
            await db.execute("DELETE FROM backup_record WHERE filename = ?", (safe_name,))
            await db.commit()
            logger.info("备份删除成功: %s", safe_name)
            return {"success": True}
        except Exception as e:
            error_msg = f"备份删除失败: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {"success": False, "error": error_msg}
