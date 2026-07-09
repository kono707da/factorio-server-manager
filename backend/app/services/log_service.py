import asyncio
import json
import logging
import os
from typing import Callable

from app.database import get_db

logger = logging.getLogger("factorio_manager.log_service")


class LogService:
    _instance: "LogService | None" = None

    def __init__(self):
        self._subscribers: list[Callable] = []
        self._log_buffer: list[str] = []
        self._buffer_max = 2000

    @classmethod
    def get_instance(cls) -> "LogService":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def add_subscriber(self, cb: Callable):
        self._subscribers.append(cb)

    def remove_subscriber(self, cb: Callable):
        if cb in self._subscribers:
            self._subscribers.remove(cb)

    def push_log(self, line: str):
        self._log_buffer.append(line)
        if len(self._log_buffer) > self._buffer_max:
            self._log_buffer = self._log_buffer[-self._buffer_max:]
        dead = []
        for cb in self._subscribers:
            try:
                cb(line)
            except Exception:
                dead.append(cb)
        for cb in dead:
            self.remove_subscriber(cb)

    def get_buffer(self, limit: int = 200) -> list[str]:
        return self._log_buffer[-limit:]

    async def get_log_files(self) -> list[dict]:
        db = await get_db()
        cursor = await db.execute("SELECT logs_dir FROM settings WHERE id = 1")
        row = await cursor.fetchone()
        logs_dir = dict(row)["logs_dir"] if row else ""

        if not logs_dir:
            settings_cursor = await db.execute("SELECT factorio_dir FROM settings WHERE id = 1")
            settings_row = await settings_cursor.fetchone()
            if settings_row:
                logs_dir = os.path.join(dict(settings_row)["factorio_dir"], "logs")

        if not logs_dir or not os.path.isdir(logs_dir):
            return []

        files = []
        for f in sorted(os.listdir(logs_dir), reverse=True):
            if f.endswith(".log"):
                path = os.path.join(logs_dir, f)
                stat = os.stat(path)
                files.append({
                    "filename": f,
                    "size": stat.st_size,
                    "modified": os.path.getmtime(path),
                })
        return files

    async def get_log_content(
        self, filename: str | None = None, keyword: str = "", limit: int = 500
    ) -> dict:
        db = await get_db()
        cursor = await db.execute("SELECT logs_dir, factorio_dir FROM settings WHERE id = 1")
        row = await cursor.fetchone()
        if not row:
            return {"error": "未找到配置", "lines": []}

        row_dict = dict(row)
        logs_dir = row_dict["logs_dir"]
        if not logs_dir:
            logs_dir = os.path.join(row_dict["factorio_dir"], "logs")

        if not logs_dir or not os.path.isdir(logs_dir):
            return {"error": f"日志目录不存在: {logs_dir}", "lines": []}

        if filename:
            safe_name = os.path.basename(filename)
            filepath = os.path.join(logs_dir, safe_name)
        else:
            log_files = sorted(
                [f for f in os.listdir(logs_dir) if f.endswith(".log")],
                key=lambda f: os.path.getmtime(os.path.join(logs_dir, f)),
                reverse=True,
            )
            if not log_files:
                return {"error": "没有日志文件", "lines": []}
            filepath = os.path.join(logs_dir, log_files[0])

        if not os.path.isfile(filepath):
            return {"error": f"日志文件不存在: {filename}", "lines": []}

        try:
            with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()

            if keyword:
                lines = [l for l in lines if keyword.lower() in l.lower()]

            lines = lines[-limit:]
            return {
                "filename": os.path.basename(filepath),
                "total_lines": len(lines),
                "lines": [l.rstrip() for l in lines],
            }
        except Exception as e:
            logger.error("读取日志文件失败: %s", e, exc_info=True)
            return {"error": f"读取日志文件失败: {str(e)}", "lines": []}
