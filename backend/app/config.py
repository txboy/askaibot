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
    db_config_file: str = "./data/db_config.json"

    skill_timeout: int = 60

    class Config:
        env_file = _ENV_FILE
        env_prefix = ""


config = Config()
