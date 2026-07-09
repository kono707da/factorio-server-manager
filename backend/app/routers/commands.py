from fastapi import APIRouter

from app.schemas import KickRequest, BanRequest, AnnounceRequest
from app.services.factorio_process import FactorioProcess

router = APIRouter(prefix="/api/commands", tags=["commands"])


@router.get("/players")
async def get_players():
    proc = FactorioProcess.get_instance()
    status = proc.get_status()
    if not status["running"]:
        return {"players": [], "error": "服务器未运行"}
    return {"players": status["online_players"]}


@router.post("/kick")
async def kick_player(req: KickRequest):
    proc = FactorioProcess.get_instance()
    result = await proc.kick(req.player, req.reason)
    return result


@router.post("/ban")
async def ban_player(req: BanRequest):
    proc = FactorioProcess.get_instance()
    result = await proc.ban(req.player, req.reason)
    return result


@router.post("/announce")
async def announce(req: AnnounceRequest):
    proc = FactorioProcess.get_instance()
    result = await proc.announce(req.message)
    return result


@router.post("/command")
async def send_command(command: str):
    proc = FactorioProcess.get_instance()
    result = await proc.send_command(command)
    return result
