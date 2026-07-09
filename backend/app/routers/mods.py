from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import FileResponse

from app.services.mod_service import ModService
from app.schemas import ModToggleRequest

router = APIRouter(prefix="/api/mods", tags=["mods"])


@router.get("")
async def list_mods():
    svc = ModService.get_instance()
    mods = await svc.list_mods()
    return {"mods": mods}


@router.post("/upload")
async def upload_mod(file: UploadFile = File(...)):
    if not file.filename or not file.filename.endswith(".zip"):
        raise HTTPException(status_code=400, detail="只支持 .zip 格式的 Mod 文件")
    svc = ModService.get_instance()
    content = await file.read()
    result = await svc.upload_mod(file.filename, content)
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error", "上传失败"))
    return result


@router.get("/download/{filename}")
async def download_mod(filename: str):
    import os
    svc = ModService.get_instance()
    mods_dir = await svc._get_mods_dir()
    safe_name = os.path.basename(filename)
    filepath = os.path.join(mods_dir, safe_name)
    if not os.path.isfile(filepath):
        raise HTTPException(status_code=404, detail=f"Mod 文件不存在: {safe_name}")
    return FileResponse(filepath, filename=safe_name, media_type="application/zip")


@router.delete("/{filename}")
async def delete_mod(filename: str):
    svc = ModService.get_instance()
    result = await svc.delete_mod(filename)
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error", "删除失败"))
    return result


@router.post("/toggle")
async def toggle_mod(req: ModToggleRequest):
    svc = ModService.get_instance()
    result = await svc.toggle_mod(req.filename, req.enabled)
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error", "操作失败"))
    return result


@router.post("/toggle-all")
async def toggle_all_mods(enabled: bool = True):
    svc = ModService.get_instance()
    result = await svc.toggle_all_mods(enabled)
    if not result.get("success"):
        raise HTTPException(status_code=500, detail="批量操作失败")
    return result
