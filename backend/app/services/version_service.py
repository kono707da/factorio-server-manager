import asyncio
import json
import logging
import os
import platform
import shutil
import tarfile
import tempfile
import zipfile

import aiohttp

from app.database import get_db
from app.services.factorio_process import FactorioProcess

logger = logging.getLogger("factorio_manager.version_service")

FACTORIO_API_URL = "https://factorio.com/api/latest-releases"
FACTORIO_DOWNLOAD_URL = "https://factorio.com/get-download/{version}/headless/{platform}"

_download_progress: dict = {"downloading": False, "progress": 0, "version": "", "error": ""}


class VersionService:
    _instance: "VersionService | None" = None

    def __init__(self):
        pass

    @classmethod
    def get_instance(cls) -> "VersionService":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    async def _get_factorio_dir(self) -> str:
        db = await get_db()
        cursor = await db.execute("SELECT factorio_dir FROM settings WHERE id = 1")
        row = await cursor.fetchone()
        return dict(row)["factorio_dir"] if row else ""

    def _detect_current_version(self, factorio_dir: str) -> str:
        info_path = ""
        candidates = [
            os.path.join(factorio_dir, "data", "base", "info.json"),
            os.path.join(factorio_dir, "data", "info.json"),
        ]
        for p in candidates:
            if os.path.isfile(p):
                info_path = p
                break

        if info_path:
            try:
                with open(info_path, "r", encoding="utf-8") as f:
                    info = json.load(f)
                return info.get("version", "")
            except Exception as e:
                logger.warning("读取版本信息失败: %s", e)

        changelog_path = os.path.join(factorio_dir, "data", "base", "changelog.txt")
        if os.path.isfile(changelog_path):
            try:
                with open(changelog_path, "r", encoding="utf-8", errors="replace") as f:
                    for line in f:
                        line = line.strip()
                        if line.startswith("Version:") or line.startswith("---------------------------------"):
                            if "Version:" in line:
                                return line.split("Version:")[1].strip().split()[0]
            except Exception as e:
                logger.warning("读取 changelog 失败: %s", e)

        return ""

    async def get_current_version(self) -> dict:
        factorio_dir = await self._get_factorio_dir()
        db = await get_db()

        current_version = self._detect_current_version(factorio_dir) if factorio_dir and os.path.isdir(factorio_dir) else ""

        if current_version:
            await db.execute(
                "UPDATE version_info SET current_version = ?, install_path = ? WHERE id = 1",
                (current_version, factorio_dir),
            )
            await db.commit()

        cursor = await db.execute("SELECT * FROM version_info WHERE id = 1")
        row = await cursor.fetchone()
        row_dict = dict(row) if row else {}

        return {
            "current_version": current_version or row_dict.get("current_version", ""),
            "install_path": factorio_dir or row_dict.get("install_path", ""),
            "installed_at": row_dict.get("installed_at", ""),
            "binary_exists": bool(factorio_dir and self._find_binary(factorio_dir)),
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

    async def get_latest_version(self) -> dict:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(FACTORIO_API_URL, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                    if resp.status != 200:
                        return {"error": f"请求 Factorio API 失败，状态码: {resp.status}"}
                    data = await resp.json()

            stable = data.get("stable", {}).get("headless", "")
            experimental = data.get("experimental", {}).get("headless", "")

            return {"stable": stable, "experimental": experimental}

        except asyncio.TimeoutError:
            return {"error": "请求 Factorio API 超时，请检查网络连接"}
        except Exception as e:
            logger.error("检查最新版本失败: %s", e, exc_info=True)
            return {"error": f"检查最新版本失败: {str(e)}"}

    async def install_version(self, version: str, channel: str = "stable") -> dict:
        global _download_progress

        if _download_progress["downloading"]:
            return {"success": False, "error": "已有下载任务正在进行中"}

        factorio_dir = await self._get_factorio_dir()
        if not factorio_dir:
            return {"success": False, "error": "Factorio 安装目录未配置"}

        proc = FactorioProcess.get_instance()
        if proc.get_status()["running"]:
            logger.info("安装前停止 Factorio 服务器...")
            stop_result = await proc.stop()
            if not stop_result.get("success"):
                return {"success": False, "error": f"停止服务器失败: {stop_result.get('error', '未知错误')}"}
            await asyncio.sleep(2)

        system = platform.system().lower()
        if system == "windows":
            plat = "win64"
        elif system == "linux":
            plat = "linux64"
        else:
            plat = "linux64"

        download_url = FACTORIO_DOWNLOAD_URL.format(version=version, platform=plat)

        _download_progress = {
            "downloading": True,
            "progress": 0,
            "version": version,
            "error": "",
        }

        try:
            with tempfile.TemporaryDirectory() as tmp_dir:
                archive_path = os.path.join(tmp_dir, f"factorio_headless_{version}.tar.xz")
                if system == "windows":
                    archive_path = os.path.join(tmp_dir, f"factorio_headless_{version}.zip")

                logger.info("开始下载 Factorio %s: %s", version, download_url)

                async with aiohttp.ClientSession() as session:
                    async with session.get(download_url, timeout=aiohttp.ClientTimeout(total=3600)) as resp:
                        if resp.status != 200:
                            _download_progress["downloading"] = False
                            _download_progress["error"] = f"下载失败，状态码: {resp.status}"
                            return {"success": False, "error": f"下载失败，HTTP {resp.status}"}

                        total = int(resp.headers.get("Content-Length", 0))
                        downloaded = 0

                        with open(archive_path, "wb") as f:
                            async for chunk in resp.content.iter_chunked(8192):
                                f.write(chunk)
                                downloaded += len(chunk)
                                if total > 0:
                                    _download_progress["progress"] = int(downloaded / total * 100)

                logger.info("下载完成，开始解压安装...")

                backup_dir = os.path.join(tmp_dir, "factorio_backup")
                preserve_items = ["saves", "config", "server-id.json", "player-data.json", "server-settings.json"]

                if os.path.isdir(factorio_dir):
                    os.makedirs(backup_dir, exist_ok=True)
                    for item in preserve_items:
                        src = os.path.join(factorio_dir, item)
                        if os.path.exists(src):
                            dst = os.path.join(backup_dir, item)
                            if os.path.isdir(src):
                                shutil.copytree(src, dst)
                            else:
                                shutil.copy2(src, dst)
                            logger.info("已备份: %s", item)

                    for item in os.listdir(factorio_dir):
                        item_path = os.path.join(factorio_dir, item)
                        try:
                            if os.path.isdir(item_path):
                                shutil.rmtree(item_path)
                            else:
                                os.remove(item_path)
                        except OSError as e:
                            logger.warning("清理旧文件失败(跳过): %s - %s", item, e)
                    logger.info("已清理 %s 目录内容", factorio_dir)

                extract_dir = os.path.join(tmp_dir, "extracted")
                os.makedirs(extract_dir, exist_ok=True)

                try:
                    if archive_path.endswith(".tar.xz"):
                        import lzma
                        with lzma.open(archive_path, "rb") as f:
                            with tarfile.open(fileobj=f) as tar:
                                tar.extractall(path=extract_dir)
                    elif archive_path.endswith(".zip"):
                        with zipfile.ZipFile(archive_path, "r") as zf:
                            zf.extractall(path=extract_dir)
                    else:
                        with tarfile.open(archive_path, "r:*") as tar:
                            tar.extractall(path=extract_dir)
                except Exception as extract_err:
                    if os.path.isdir(backup_dir):
                        for item in os.listdir(backup_dir):
                            src = os.path.join(backup_dir, item)
                            dst = os.path.join(factorio_dir, item)
                            if os.path.isdir(src):
                                shutil.copytree(src, dst)
                            else:
                                os.makedirs(os.path.dirname(dst), exist_ok=True)
                                shutil.copy2(src, dst)
                    raise extract_err

                extracted_factorio = os.path.join(extract_dir, "factorio")
                if not os.path.isdir(extracted_factorio):
                    subdirs = [d for d in os.listdir(extract_dir) if os.path.isdir(os.path.join(extract_dir, d))]
                    if len(subdirs) == 1:
                        extracted_factorio = os.path.join(extract_dir, subdirs[0])
                    else:
                        extracted_factorio = extract_dir

                for item in os.listdir(extracted_factorio):
                    src = os.path.join(extracted_factorio, item)
                    dst = os.path.join(factorio_dir, item)
                    if os.path.isdir(src):
                        shutil.copytree(src, dst)
                    else:
                        shutil.copy2(src, dst)
                logger.info("已将新版本文件复制到 %s", factorio_dir)

                if os.path.isdir(backup_dir):
                    for item in os.listdir(backup_dir):
                        src = os.path.join(backup_dir, item)
                        dst = os.path.join(factorio_dir, item)
                        if os.path.exists(dst):
                            if os.path.isdir(dst):
                                shutil.rmtree(dst)
                                shutil.copytree(src, dst)
                            else:
                                shutil.copy2(src, dst)
                        else:
                            if os.path.isdir(src):
                                shutil.copytree(src, dst)
                            else:
                                shutil.copy2(src, dst)
                    logger.info("已恢复备份数据")

                db = await get_db()
                await db.execute(
                    "UPDATE version_info SET current_version = ?, install_path = ?, installed_at = datetime('now') WHERE id = 1",
                    (version, factorio_dir),
                )
                await db.commit()

                _download_progress["downloading"] = False
                _download_progress["progress"] = 100
                logger.info("Factorio %s 安装完成", version)
                return {"success": True, "version": version}

        except Exception as e:
            _download_progress["downloading"] = False
            _download_progress["error"] = str(e)
            error_msg = f"安装 Factorio {version} 失败: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {"success": False, "error": error_msg}

    def get_install_status(self) -> dict:
        return {
            "downloading": _download_progress["downloading"],
            "progress": _download_progress["progress"],
            "version": _download_progress["version"],
            "error": _download_progress["error"],
        }
