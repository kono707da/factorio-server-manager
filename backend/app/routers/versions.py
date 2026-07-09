import asyncio

from fastapi import APIRouter

from app.schemas import VersionInstallRequest
from app.services.version_service import VersionService

router = APIRouter(prefix="/api/versions", tags=["versions"])


@router.get("/current")
async def get_current_version():
    svc = VersionService.get_instance()
    info = await svc.get_current_version()
    return info


@router.get("/latest")
async def get_latest_version():
    svc = VersionService.get_instance()
    info = await svc.get_latest_version()
    return info


@router.post("/install")
async def install_version(req: VersionInstallRequest):
    svc = VersionService.get_instance()
    status = svc.get_install_status()
    if status["downloading"]:
        return {"success": False, "error": "已有下载任务正在进行中"}
    asyncio.create_task(svc.install_version(req.version, req.channel))
    return {"success": True, "message": f"Factorio {req.version} 下载已开始"}


@router.get("/install-status")
async def get_install_status():
    svc = VersionService.get_instance()
    status = svc.get_install_status()
    return status
