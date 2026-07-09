from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.schemas import BackupConfigUpdate
from app.services.backup_service import BackupService

router = APIRouter(prefix="/api/backups", tags=["backups"])


@router.get("/config")
async def get_backup_config():
    svc = BackupService.get_instance()
    config = await svc.get_config()
    return config


@router.put("/config")
async def update_backup_config(req: BackupConfigUpdate):
    svc = BackupService.get_instance()
    config = await svc.update_config(
        enabled=req.enabled,
        interval_hours=req.interval_hours,
        max_backups=req.max_backups,
    )
    return config


@router.get("/list")
async def list_backups():
    svc = BackupService.get_instance()
    backups = await svc.list_backups()
    return {"backups": backups}


@router.post("/trigger")
async def trigger_backup():
    svc = BackupService.get_instance()
    result = await svc.trigger_backup()
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error", "备份失败"))
    return result


@router.get("/download/{filename}")
async def download_backup(filename: str):
    svc = BackupService.get_instance()
    filepath, error = await svc.download_backup(filename)
    if error:
        raise HTTPException(status_code=404, detail=error)
    return FileResponse(filepath, filename=filename, media_type="application/zip")


@router.post("/restore/{filename}")
async def restore_backup(filename: str):
    svc = BackupService.get_instance()
    result = await svc.restore_backup(filename)
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error", "恢复失败"))
    return result


@router.delete("/{filename}")
async def delete_backup(filename: str):
    svc = BackupService.get_instance()
    result = await svc.delete_backup(filename)
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error", "删除失败"))
    return result
