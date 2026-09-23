from pydantic_settings import BaseSettings


class Config(BaseSettings):
    jwt_secret: str = "change-this-super-secret-key-please-32bytes-min"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24 * 7

    frontend_url: str = "http://localhost:5173"
    sms_mock: bool = True
    upload_dir: str = "./data/uploads"
    max_upload_size: int = 20 * 1024 * 1024

    class Config:
        env_file = ".env"
        env_prefix = ""


config = Config()
