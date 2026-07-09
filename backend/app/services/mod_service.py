import json
import logging
import os
import zipfile
from datetime import datetime

from app.database import get_db
from app.config import DEFAULT_FACTORIO_DIR

logger = logging.getLogger("factorio_manager.mod_service")


class ModService:
    _instance: "ModService | None" = None

    @classmethod
    def get_instance(cls) -> "ModService":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    async def _get_factorio_dir(self) -> str:
        db = await get_db()
        cursor = await db.execute("SELECT factorio_dir FROM settings WHERE id = 1")
        row = await cursor.fetchone()
        factorio_dir = dict(row)["factorio_dir"] if row else DEFAULT_FACTORIO_DIR
        if not factorio_dir:
            factorio_dir = DEFAULT_FACTORIO_DIR
        return factorio_dir

    async def _get_mods_dir(self) -> str:
        return os.path.join(await self._get_factorio_dir(), "mods")

    def _get_mod_list_path(self, mods_dir: str) -> str:
        return os.path.join(mods_dir, "mod-list.json")

    def _read_mod_list(self, mods_dir: str) -> dict:
        path = self._get_mod_list_path(mods_dir)
        if os.path.isfile(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning("读取 mod-list.json 失败: %s", e)
        return {"mods": []}

    def _write_mod_list(self, mods_dir: str, data: dict):
        path = self._get_mod_list_path(mods_dir)
        os.makedirs(mods_dir, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        logger.info("已更新 mod-list.json")

    def _parse_mod_zip(self, filepath: str) -> dict | None:
        try:
            with zipfile.ZipFile(filepath, "r") as zf:
                info_files = [n for n in zf.namelist() if n.endswith("info.json")]
                if not info_files:
                    return None
                with zf.open(info_files[0]) as info_f:
                    info = json.loads(info_f.read().decode("utf-8"))
                    return {
                        "name": info.get("name", os.path.basename(filepath).replace(".zip", "")),
                        "version": info.get("version", ""),
                        "title": info.get("title", info.get("name", "")),
                        "author": info.get("author", ""),
                        "description": info.get("description", ""),
                        "factorio_version": info.get("factorio_version", ""),
                    }
        except Exception as e:
            logger.error("解析 mod zip 失败: %s - %s", filepath, e)
            return None

    def _parse_builtin_mod(self, mod_dir: str) -> dict | None:
        info_path = os.path.join(mod_dir, "info.json")
        if not os.path.isfile(info_path):
            return None
        try:
            with open(info_path, "r", encoding="utf-8") as f:
                info = json.load(f)
                return {
                    "name": info.get("name", os.path.basename(mod_dir)),
                    "version": info.get("version", ""),
                    "title": info.get("title", info.get("name", "")),
                    "author": info.get("author", "Factorio Team"),
                    "description": info.get("description", ""),
                    "factorio_version": info.get("factorio_version", ""),
                }
        except Exception as e:
            logger.error("解析内置 mod info.json 失败: %s - %s", mod_dir, e)
            return None

    async def list_mods(self) -> list[dict]:
        factorio_dir = await self._get_factorio_dir()
        mods_dir = os.path.join(factorio_dir, "mods")
        data_dir = os.path.join(factorio_dir, "data")

        mod_list_data = self._read_mod_list(mods_dir)
        mod_list = {m["name"]: m for m in mod_list_data.get("mods", [])}

        mods = []
        seen_names = set()

        # 1. 扫描 mods/ 目录下的 .zip 文件
        if os.path.isdir(mods_dir):
            for f in os.listdir(mods_dir):
                if not f.endswith(".zip"):
                    continue
                filepath = os.path.join(mods_dir, f)
                stat = os.stat(filepath)
                info = self._parse_mod_zip(filepath) or {}
                name = info.get("name", f.replace(".zip", ""))

                list_entry = mod_list.get(name, {})
                enabled = list_entry.get("enabled", True)

                mods.append({
                    "filename": f,
                    "name": name,
                    "version": info.get("version", ""),
                    "title": info.get("title", name),
                    "author": info.get("author", ""),
                    "description": info.get("description", ""),
                    "factorio_version": info.get("factorio_version", ""),
                    "enabled": enabled,
                    "is_builtin": False,
                    "size": stat.st_size,
                    "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                })
                seen_names.add(name)

        # 2. 扫描 data/ 目录下的内置 mod（base, elevated-rails, quality, space-age 等）
        if os.path.isdir(data_dir):
            for d in os.listdir(data_dir):
                mod_dir = os.path.join(data_dir, d)
                if not os.path.isdir(mod_dir):
                    continue
                info = self._parse_builtin_mod(mod_dir)
                if not info:
                    continue
                name = info["name"]
                if name in seen_names:
                    continue

                list_entry = mod_list.get(name, {})
                enabled = list_entry.get("enabled", True)

                mods.append({
                    "filename": "",
                    "name": name,
                    "version": info.get("version", ""),
                    "title": info.get("title", name),
                    "author": info.get("author", "Factorio Team"),
                    "description": info.get("description", ""),
                    "factorio_version": info.get("factorio_version", ""),
                    "enabled": enabled,
                    "is_builtin": True,
                    "size": 0,
                    "modified": "",
                })
                seen_names.add(name)

        # 3. 补充 mod-list.json 中存在但没有对应文件的 mod（如 base）
        for name, entry in mod_list.items():
            if name in seen_names:
                continue
            mods.append({
                "filename": "",
                "name": name,
                "version": "",
                "title": name,
                "author": "",
                "description": "",
                "factorio_version": "",
                "enabled": entry.get("enabled", True),
                "is_builtin": True,
                "size": 0,
                "modified": "",
            })

        mods.sort(key=lambda x: x["name"].lower())
        return mods

    async def upload_mod(self, filename: str, content: bytes) -> dict:
        mods_dir = await self._get_mods_dir()
        os.makedirs(mods_dir, exist_ok=True)

        safe_name = os.path.basename(filename)
        if not safe_name.endswith(".zip"):
            safe_name += ".zip"
        filepath = os.path.join(mods_dir, safe_name)

        try:
            with open(filepath, "wb") as f:
                f.write(content)
        except Exception as e:
            error_msg = f"Mod 上传失败: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {"success": False, "error": error_msg}

        info = self._parse_mod_zip(filepath)
        if info:
            mod_list_data = self._read_mod_list(mods_dir)
            mods = mod_list_data.get("mods", [])
            existing = next((m for m in mods if m["name"] == info["name"]), None)
            if not existing:
                mods.append({"name": info["name"], "enabled": True})
                mod_list_data["mods"] = mods
                self._write_mod_list(mods_dir, mod_list_data)

        logger.info("Mod 上传成功: %s", safe_name)
        return {"success": True, "filename": safe_name}

    async def delete_mod(self, filename: str) -> dict:
        mods_dir = await self._get_mods_dir()
        safe_name = os.path.basename(filename)
        filepath = os.path.join(mods_dir, safe_name)

        if not os.path.isfile(filepath):
            return {"success": False, "error": f"Mod 文件不存在: {safe_name}"}

        info = self._parse_mod_zip(filepath)
        mod_name = info.get("name", "") if info else ""

        try:
            os.remove(filepath)
        except Exception as e:
            error_msg = f"Mod 删除失败: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {"success": False, "error": error_msg}

        if mod_name:
            mod_list_data = self._read_mod_list(mods_dir)
            mods = mod_list_data.get("mods", [])
            mods = [m for m in mods if m["name"] != mod_name]
            mod_list_data["mods"] = mods
            self._write_mod_list(mods_dir, mod_list_data)

        logger.info("Mod 删除成功: %s", safe_name)
        return {"success": True}

    async def toggle_mod(self, name: str, enabled: bool) -> dict:
        mods_dir = await self._get_mods_dir()
        mod_list_data = self._read_mod_list(mods_dir)
        mods = mod_list_data.get("mods", [])

        existing = next((m for m in mods if m["name"] == name), None)
        if existing:
            existing["enabled"] = enabled
        else:
            mods.append({"name": name, "enabled": enabled})

        mod_list_data["mods"] = mods
        self._write_mod_list(mods_dir, mod_list_data)

        action = "启用" if enabled else "禁用"
        logger.info("Mod %s 已%s", name, action)
        return {"success": True, "name": name, "enabled": enabled}

    async def toggle_all_mods(self, enabled: bool) -> dict:
        mods_dir = await self._get_mods_dir()
        mod_list_data = self._read_mod_list(mods_dir)
        mods = mod_list_data.get("mods", [])

        for m in mods:
            if m["name"] != "base":
                m["enabled"] = enabled

        mod_list_data["mods"] = mods
        self._write_mod_list(mods_dir, mod_list_data)

        action = "启用" if enabled else "禁用"
        logger.info("所有 Mod 已%s", action)
        return {"success": True}
