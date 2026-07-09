import logging
import platform

import psutil

logger = logging.getLogger("factorio_manager.resource_monitor")


class ResourceMonitor:
    _instance: "ResourceMonitor | None" = None

    def __init__(self):
        pass

    @classmethod
    def get_instance(cls) -> "ResourceMonitor":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def get_system_resources(self) -> dict:
        try:
            cpu_percent = psutil.cpu_percent(interval=0.5)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage("/" if platform.system() != "Windows" else "C:\\")

            return {
                "cpu_percent": round(cpu_percent, 1),
                "memory_percent": round(memory.percent, 1),
                "memory_used_mb": round(memory.used / (1024 * 1024), 1),
                "memory_total_mb": round(memory.total / (1024 * 1024), 1),
                "disk_percent": round(disk.percent, 1),
                "disk_free_gb": round(disk.free / (1024 * 1024 * 1024), 2),
                "disk_total_gb": round(disk.total / (1024 * 1024 * 1024), 2),
            }
        except Exception as e:
            logger.error("获取系统资源信息失败: %s", e, exc_info=True)
            return {
                "cpu_percent": 0,
                "memory_percent": 0,
                "memory_used_mb": 0,
                "memory_total_mb": 0,
                "disk_percent": 0,
                "disk_free_gb": 0,
                "disk_total_gb": 0,
            }

    def get_process_resources(self, pid: int | None) -> dict | None:
        if not pid:
            return None
        try:
            proc = psutil.Process(pid)
            return {
                "cpu_percent": round(proc.cpu_percent(interval=0.5), 1),
                "memory_mb": round(proc.memory_info().rss / (1024 * 1024), 1),
                "threads": proc.num_threads(),
                "create_time": proc.create_time(),
            }
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return None
