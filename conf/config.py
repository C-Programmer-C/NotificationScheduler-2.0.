from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    LOGIN: str
    SECURITY_KEY: str
    MANAGER_ID: int
    DATABASE_PATH: str
    MAX_WORKERS: int
    LOCK_EXPIRY_MINUTES: int
    ESCALATION_ATTEMPT: int
    REMOVE_AFTER_ATTEMPTS: int
    SCAN_INTERVAL: int
    LIMIT_PROCESS_TASKS: int
    BOT_ID: int
    ATTEMPT_INTERVAL_DAYS: int
    ATTEMPT_INTERVAL_HOURS: int
    ATTEMPT_INTERVAL_MINUTES: int
    ATTEMPT_INTERVAL_SECONDS: int

    class Config:
        env_file = str(Path(__file__).resolve().parent.parent / ".env")

settings = Settings()

PROJECT_ROOT = Path(__file__).resolve().parent.parent

db_path = Path(settings.DATABASE_PATH).expanduser()
if not db_path.is_absolute():
    db_path = (PROJECT_ROOT / db_path).resolve()