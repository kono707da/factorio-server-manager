from pydantic import BaseModel


class ServerStatus(BaseModel):
    running: bool
    uptime_seconds: int = 0
    online_players: list[str] = []
    current_save: str = ""
    pid: int | None = None


class ServerStartRequest(BaseModel):
    save_filename: str | None = None


class CommandRequest(BaseModel):
    command: str


class KickRequest(BaseModel):
    player: str
    reason: str = ""


class BanRequest(BaseModel):
    player: str
    reason: str = ""


class AnnounceRequest(BaseModel):
    message: str


class SaveSwitchRequest(BaseModel):
    filename: str


class BackupConfigUpdate(BaseModel):
    enabled: bool | None = None
    interval_hours: int | None = None
    max_backups: int | None = None


class VersionInstallRequest(BaseModel):
    version: str
    channel: str = "stable"


class SettingsUpdate(BaseModel):
    factorio_dir: str | None = None
    saves_dir: str | None = None
    backups_dir: str | None = None
    logs_dir: str | None = None
    server_port: int | None = None
    game_password: str | None = None
    max_players: int | None = None
    require_user_verification: bool | None = None
    autosave_interval: int | None = None
    autosave_slots: int | None = None
    factorio_username: str | None = None
    factorio_token: str | None = None


class SaveInfo(BaseModel):
    filename: str
    size: int
    modified: str
    is_active: bool = False


class BackupInfo(BaseModel):
    id: int
    filename: str
    source_save: str
    file_size: int
    created_at: str


class ResourceInfo(BaseModel):
    cpu_percent: float
    memory_percent: float
    memory_used_mb: float
    memory_total_mb: float
    disk_percent: float
    disk_free_gb: float
    disk_total_gb: float


class VersionInfo(BaseModel):
    current_version: str
    install_path: str
    installed_at: str


class LatestVersionInfo(BaseModel):
    stable: str = ""
    experimental: str = ""


class ModToggleRequest(BaseModel):
    name: str
    enabled: bool
