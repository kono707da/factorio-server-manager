import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.database import init_db, close_db
from app.routers import server, logs, commands, saves, backups, versions, config
from app.services.backup_service import BackupService
from app.services.factorio_process import FactorioProcess
from app.services.log_service import LogService
from app.config import DEFAULT_FACTORIO_DIR, DEFAULT_SAVES_DIR, DEFAULT_BACKUPS_DIR, DEFAULT_LOGS_DIR

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("factorio_manager")

FRONTEND_DIST = os.environ.get(
    "FRONTEND_DIST",
    os.path.abspath(os.path.join(os.path.dirname(__file__), "../../frontend/dist"))
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    logger.info("数据库初始化完成")

    for d in [DEFAULT_FACTORIO_DIR, DEFAULT_SAVES_DIR, DEFAULT_BACKUPS_DIR, DEFAULT_LOGS_DIR]:
        os.makedirs(d, exist_ok=True)
    logger.info("目录初始化完成: %s, %s, %s, %s", DEFAULT_FACTORIO_DIR, DEFAULT_SAVES_DIR, DEFAULT_BACKUPS_DIR, DEFAULT_LOGS_DIR)

    log_svc = LogService.get_instance()
    proc = FactorioProcess.get_instance()
    proc.add_log_callback(log_svc.push_log)

    backup_svc = BackupService.get_instance()
    await backup_svc.start_scheduler()
    logger.info("备份调度器已启动")

    if os.path.isdir(FRONTEND_DIST):
        logger.info("前端静态文件托管已启用: %s", FRONTEND_DIST)
    else:
        logger.warning("前端 dist 目录不存在（%s），请先运行 npm run build", FRONTEND_DIST)

    yield

    proc_svc = FactorioProcess.get_instance()
    if proc_svc.process and proc_svc.process.returncode is None:
        logger.info("正在停止 Factorio 服务器...")
        await proc_svc.stop()

    await backup_svc.stop_scheduler()
    await close_db()
    logger.info("应用已关闭")


app = FastAPI(
    title="Factorio Server Manager",
    description="Factorio 服务器管理面板",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(server.router)
app.include_router(logs.router)
app.include_router(commands.router)
app.include_router(saves.router)
app.include_router(backups.router)
app.include_router(versions.router)
app.include_router(config.router)


@app.get("/health")
async def health():
    return {"status": "ok"}


if os.path.isdir(FRONTEND_DIST):
    assets_dir = os.path.join(FRONTEND_DIST, "assets")
    if os.path.isdir(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/", include_in_schema=False)
    async def index():
        return FileResponse(os.path.join(FRONTEND_DIST, "index.html"))

    @app.exception_handler(StarletteHTTPException)
    async def spa_fallback(request: Request, exc: StarletteHTTPException):
        path = request.url.path
        if path.startswith(("/api/", "/docs", "/openapi.json", "/health")):
            return JSONResponse({"detail": exc.detail}, status_code=exc.status_code)
        if exc.status_code == 404:
            file_path = os.path.join(FRONTEND_DIST, path.lstrip("/"))
            if os.path.isfile(file_path):
                return FileResponse(file_path)
            return FileResponse(os.path.join(FRONTEND_DIST, "index.html"))
        return JSONResponse({"detail": exc.detail}, status_code=exc.status_code)
else:
    @app.get("/", tags=["root"])
    async def root():
        return {
            "name": "Factorio Server Manager",
            "version": "1.0.0",
            "docs": "/docs",
            "warning": "前端未构建，请先运行 npm run build",
        }
