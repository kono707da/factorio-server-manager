import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.environ.get("DATA_DIR", os.path.join(BASE_DIR, "data"))
DATABASE_PATH = os.path.join(DATA_DIR, "factorio_manager.db")
DATABASE_URL = f"sqlite+aiosqlite:///{DATABASE_PATH}"

DEFAULT_FACTORIO_DIR = os.environ.get(
    "FACTORIO_DIR", "/opt/factorio"
)
DEFAULT_SAVES_DIR = os.environ.get("SAVES_DIR", "")
DEFAULT_BACKUPS_DIR = os.environ.get("BACKUPS_DIR", "")
DEFAULT_LOGS_DIR = os.environ.get("LOGS_DIR", "")
DEFAULT_SERVER_PORT = 34197
DEFAULT_WEB_PORT = 8199

for d in [DATA_DIR]:
    os.makedirs(d, exist_ok=True)
