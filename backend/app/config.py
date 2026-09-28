from pathlib import Path

from pydantic_settings import BaseSettings

_ENV_FILE = Path(__file__).resolve().parent.parent / ".env"


class Config(BaseSettings):
    jwt_secret: str = "change-this-super-secret-key-please-32bytes-min"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24 * 7

    frontend_url: str = "http://localhost:5173"
    debug: bool = False
    sms_mock: bool = True
    upload_dir: str = "./data/uploads"
    max_upload_size: int = 20 * 1024 * 1024

    skill_sandbox: str = "auto"  # auto / docker / local
    skill_runner_image: str = "askai-skill-runner"
    skill_data_volume: str = "app_data"
    skill_data_mount: str = "/app/data"
    skill_timeout: int = 60
    skill_cpus: str = "1"
    skill_memory: str = "512m"
    skill_pids_limit: int = 64

    class Config:
        env_file = _ENV_FILE
        env_prefix = ""


config = Config()
