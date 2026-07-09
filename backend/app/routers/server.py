import asyncio
import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.schemas import ServerStartRequest, ServerStatus
from app.services.factorio_process import FactorioProcess
from app.services.resource_monitor import ResourceMonitor
from app.services.log_service import LogService

router = APIRouter(prefix="/api/server", tags=["server"])


@router.get("/status")
async def get_status():
    proc = FactorioProcess.get_instance()
    status = proc.get_status()
    return status


@router.post("/start")
async def start_server(req: ServerStartRequest = None):
    proc = FactorioProcess.get_instance()
    save_filename = req.save_filename if req else None
    result = await proc.start(save_filename)
    return result


@router.post("/stop")
async def stop_server():
    proc = FactorioProcess.get_instance()
    result = await proc.stop()
    return result


@router.post("/restart")
async def restart_server(req: ServerStartRequest = None):
    proc = FactorioProcess.get_instance()
    save_filename = req.save_filename if req else None
    result = await proc.restart(save_filename)
    return result


@router.post("/save")
async def save_server():
    proc = FactorioProcess.get_instance()
    result = await proc.save()
    return result


@router.get("/resources")
async def get_resources():
    monitor = ResourceMonitor.get_instance()
    proc = FactorioProcess.get_instance()
    status = proc.get_status()
    system = monitor.get_system_resources()
    process = monitor.get_process_resources(status.get("pid"))
    return {"system": system, "process": process}


@router.websocket("/ws/status")
async def ws_status(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            proc = FactorioProcess.get_instance()
            status = proc.get_status()
            monitor = ResourceMonitor.get_instance()
            system = monitor.get_system_resources()
            process = monitor.get_process_resources(status.get("pid"))
            await websocket.send_json({
                "server": status,
                "system": system,
                "process": process,
            })
            await asyncio.sleep(3)
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
