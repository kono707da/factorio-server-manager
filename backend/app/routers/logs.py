import asyncio
import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query

from app.services.log_service import LogService
from app.services.factorio_process import FactorioProcess

router = APIRouter(prefix="/api/logs", tags=["logs"])


@router.get("/files")
async def get_log_files():
    svc = LogService.get_instance()
    files = await svc.get_log_files()
    return {"files": files}


@router.get("/content")
async def get_log_content(
    file: str = Query(default=None, description="日志文件名"),
    keyword: str = Query(default="", description="搜索关键词"),
    limit: int = Query(default=500, description="返回行数限制"),
):
    svc = LogService.get_instance()
    result = await svc.get_log_content(filename=file, keyword=keyword, limit=limit)
    return result


@router.websocket("/stream")
async def ws_log_stream(websocket: WebSocket):
    await websocket.accept()
    svc = LogService.get_instance()
    proc = FactorioProcess.get_instance()

    queue = asyncio.Queue()

    def on_log(line: str):
        try:
            queue.put_nowait(line)
        except Exception:
            pass

    svc.add_subscriber(on_log)

    try:
        for line in svc.get_buffer(limit=100):
            await websocket.send_text(line)

        while True:
            try:
                line = await asyncio.wait_for(queue.get(), timeout=30)
                await websocket.send_text(line)
            except asyncio.TimeoutError:
                try:
                    await websocket.send_text("")
                except Exception:
                    break
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        svc.remove_subscriber(on_log)
