import asyncio
import logging
import os
import shutil
import time
from typing import Callable

from app.database import get_db
from app.config import DEFAULT_FACTORIO_DIR, DEFAULT_SAVES_DIR, DEFAULT_BACKUPS_DIR, DEFAULT_LOGS_DIR

logger = logging.getLogger("factorio_manager.process")


class FactorioProcess:
    _instance: "FactorioProcess | None" = None

    def __init__(self):
        self.process: asyncio.subprocess.Process | None = None
        self.start_time: float = 0
        self.current_save: str = ""
        self.online_players: list[str] = []
        self._log_callbacks: list[Callable] = []
        self._reader_task: asyncio.Task | None = None
        self._status_task: asyncio.Task | None = None

    @classmethod
    def get_instance(cls) -> "FactorioProcess":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def add_log_callback(self, cb: Callable):
        self._log_callbacks.append(cb)

    def remove_log_callback(self, cb: Callable):
        if cb in self._log_callbacks:
            self._log_callbacks.remove(cb)

    async def _get_settings(self) -> dict:
        db = await get_db()
        cursor = await db.execute("SELECT * FROM settings WHERE id = 1")
        row = await cursor.fetchone()
        return dict(row) if row else {}

    def _resolve_paths(self, settings: dict) -> dict:
        factorio_dir = settings.get("factorio_dir") or DEFAULT_FACTORIO_DIR
        saves_dir = settings.get("saves_dir") or DEFAULT_SAVES_DIR
        backups_dir = settings.get("backups_dir") or DEFAULT_BACKUPS_DIR
        logs_dir = settings.get("logs_dir") or DEFAULT_LOGS_DIR

        if not os.path.isabs(saves_dir):
            saves_dir = os.path.join(factorio_dir, saves_dir)
        if not os.path.isabs(backups_dir):
            backups_dir = os.path.join(factorio_dir, backups_dir)
        if not os.path.isabs(logs_dir):
            logs_dir = os.path.join(factorio_dir, logs_dir)

        return {
            "factorio_dir": factorio_dir,
            "saves_dir": saves_dir,
            "backups_dir": backups_dir,
            "logs_dir": logs_dir,
            "server_port": settings.get("server_port", 34197),
            "game_password": settings.get("game_password", ""),
            "max_players": settings.get("max_players", 10),
            "require_user_verification": settings.get("require_user_verification", True),
            "autosave_interval": settings.get("autosave_interval", 5),
            "autosave_slots": settings.get("autosave_slots", 5),
        }

    def _find_binary(self, factorio_dir: str) -> str | None:
        candidates = [
            os.path.join(factorio_dir, "bin", "x64", "factorio.exe"),
            os.path.join(factorio_dir, "bin", "x64", "factorio"),
        ]
        for path in candidates:
            if os.path.isfile(path):
                return path
        return None

    async def start(self, save_filename: str | None = None) -> dict:
        if self.process and self.process.returncode is None:
            return {"success": False, "error": "服务器已在运行中"}

        settings = await self._get_settings()
        paths = self._resolve_paths(settings)
        factorio_dir = paths["factorio_dir"]

        if not factorio_dir or not os.path.isdir(factorio_dir):
            return {"success": False, "error": f"Factorio 目录不存在: {factorio_dir}"}

        binary = self._find_binary(factorio_dir)
        if not binary:
            return {"success": False, "error": f"找不到 Factorio 可执行文件，请检查安装目录: {factorio_dir}"}

        saves_dir = paths["saves_dir"]
        os.makedirs(saves_dir, exist_ok=True)

        cmd = [
            binary,
            "--start-server",
        ]

        if save_filename:
            save_path = os.path.join(saves_dir, save_filename)
            if not os.path.isfile(save_path):
                return {"success": False, "error": f"存档文件不存在: {save_filename}"}
            cmd.append(save_filename)
            self.current_save = save_filename
        else:
            saves = [f for f in os.listdir(saves_dir) if f.endswith(".zip")]
            if saves:
                latest = max(
                    [os.path.join(saves_dir, s) for s in saves],
                    key=os.path.getmtime,
                )
                save_name = os.path.basename(latest)
                cmd.append(save_name)
                self.current_save = save_name
            else:
                cmd.append("--create")
                cmd.append(os.path.join(saves_dir, "new_save.zip"))
                self.current_save = "new_save.zip"

        cmd.extend([
            "--port", str(paths["server_port"]),
            "--server-settings",
            os.path.join(factorio_dir, "server-settings.json"),
        ])

        if paths["game_password"]:
            cmd.extend(["--game-password", paths["game_password"]])

        config_dir = os.path.join(factorio_dir, "config")
        config_path = os.path.join(config_dir, "config-server.ini")
        if os.path.isfile(config_path):
            cmd.extend(["--config", config_path])

        write_data_dir = factorio_dir
        cmd.extend(["--server-id", os.path.join(write_data_dir, "server-id.json")])

        logger.info("启动 Factorio 服务器: %s", " ".join(cmd))

        try:
            self.process = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
                cwd=factorio_dir,
            )
            self.start_time = time.time()
            self.online_players = []

            self._reader_task = asyncio.create_task(self._read_output())

            await asyncio.sleep(2)
            if self.process.returncode is not None:
                error_msg = f"Factorio 进程启动后立即退出，返回码: {self.process.returncode}"
                logger.error(error_msg)
                self.process = None
                return {"success": False, "error": error_msg}

            logger.info("Factorio 服务器已启动, PID: %d", self.process.pid)
            return {"success": True, "pid": self.process.pid}

        except Exception as e:
            error_msg = f"启动 Factorio 服务器失败: {str(e)}"
            logger.error(error_msg, exc_info=True)
            self.process = None
            return {"success": False, "error": error_msg}

    async def _read_output(self):
        if not self.process or not self.process.stdout:
            return
        try:
            while True:
                line = await self.process.stdout.readline()
                if not line:
                    break
                text = line.decode("utf-8", errors="replace").rstrip()
                if text:
                    self._parse_players(text)
                    for cb in self._log_callbacks:
                        try:
                            cb(text)
                        except Exception:
                            pass
        except Exception as e:
            logger.error("读取 Factorio 输出时出错: %s", e, exc_info=True)
        finally:
            logger.info("Factorio 进程输出流已结束")

    def _parse_players(self, line: str):
        lower = line.lower()
        if "joined the game" in lower:
            parts = line.split()
            if parts:
                player = parts[0].strip(":")
                if player and player not in self.online_players:
                    self.online_players.append(player)
        elif "left the game" in lower:
            parts = line.split()
            if parts:
                player = parts[0].strip(":")
                if player in self.online_players:
                    self.online_players.remove(player)

    async def stop(self) -> dict:
        if not self.process or self.process.returncode is not None:
            return {"success": False, "error": "服务器未在运行"}

        try:
            self.process.stdin.write(b"/quit\n")
            await self.process.stdin.drain()
            try:
                await asyncio.wait_for(self.process.wait(), timeout=15)
            except asyncio.TimeoutError:
                self.process.kill()
                await self.process.wait()

            logger.info("Factorio 服务器已停止")
            self.process = None
            self.online_players = []
            return {"success": True}

        except Exception as e:
            error_msg = f"停止 Factorio 服务器失败: {str(e)}"
            logger.error(error_msg, exc_info=True)
            try:
                self.process.kill()
            except Exception:
                pass
            self.process = None
            self.online_players = []
            return {"success": False, "error": error_msg}

    async def restart(self, save_filename: str | None = None) -> dict:
        if self.process and self.process.returncode is None:
            stop_result = await self.stop()
            if not stop_result.get("success"):
                return stop_result
            await asyncio.sleep(2)
        return await self.start(save_filename)

    async def send_command(self, command: str) -> dict:
        if not self.process or self.process.returncode is not None:
            return {"success": False, "error": "服务器未在运行，无法发送命令"}

        try:
            self.process.stdin.write(f"{command}\n".encode())
            await self.process.stdin.drain()
            logger.info("已发送命令: %s", command)
            return {"success": True}
        except Exception as e:
            error_msg = f"发送命令失败: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {"success": False, "error": error_msg}

    async def save(self) -> dict:
        return await self.send_command("/server-save")

    async def kick(self, player: str, reason: str = "") -> dict:
        cmd = f"/kick {player}"
        if reason:
            cmd += f" {reason}"
        return await self.send_command(cmd)

    async def ban(self, player: str, reason: str = "") -> dict:
        cmd = f"/ban {player}"
        if reason:
            cmd += f" {reason}"
        return await self.send_command(cmd)

    async def announce(self, message: str) -> dict:
        return await self.send_command(f"/announce {message}")

    def get_status(self) -> dict:
        running = self.process is not None and self.process.returncode is None
        uptime = int(time.time() - self.start_time) if running and self.start_time else 0
        return {
            "running": running,
            "uptime_seconds": uptime,
            "online_players": list(self.online_players) if running else [],
            "current_save": self.current_save if running else "",
            "pid": self.process.pid if running else None,
        }
