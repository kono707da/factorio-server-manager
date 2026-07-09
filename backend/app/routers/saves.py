import os
from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import FileResponse

from app.services.save_service import SaveService
from app.services.factorio_process import FactorioProcess
from app.schemas import SaveSwitchRequest

router = APIRouter(prefix="/api/saves", tags=["saves"])


@router.get("")
async def list_saves():
    svc = SaveService.get_instance()
    proc = FactorioProcess.get_instance()
    status = proc.get_status()
    saves = await svc.list_saves(active_save=status.get("current_save", ""))
    return {"saves": saves}


@router.post("/upload")
async def upload_save(file: UploadFile = File(...)):
    if not file.filename or not file.filename.endswith(".zip"):
        raise HTTPException(status_code=400, detail="只支持 .zip 格式的存档文件")
    svc = SaveService.get_instance()
    content = await file.read()
    result = await svc.upload_save(file.filename, content)
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error", "上传失败"))
    return result


@router.get("/download/{filename}")
async def download_save(filename: str):
    svc = SaveService.get_instance()
    filepath, error = await svc.download_save(filename)
    if error:
        raise HTTPException(status_code=404, detail=error)
    return FileResponse(filepath, filename=filename, media_type="application/zip")


@router.delete("/{filename}")
async def delete_save(filename: str):
    svc = SaveService.get_instance()
    result = await svc.delete_save(filename)
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error", "删除失败"))
    return result


@router.post("/switch")
async def switch_save(req: SaveSwitchRequest):
    proc = FactorioProcess.get_instance()
    status = proc.get_status()
    if status["running"]:
        result = await proc.restart(save_filename=req.filename)
        if result.get("success"):
            return {"success": True, "message": f"已切换存档到 {req.filename} 并重启服务器"}
        return result
    proc.current_save = req.filename
    return {"success": True, "message": f"已设置下次启动使用存档: {req.filename}"}


@router.post("/create")
async def create_save(save_name: str = "new_save"):
    svc = SaveService.get_instance()
    result = await svc.create_save(save_name)
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error", "创建存档失败"))
    return result
