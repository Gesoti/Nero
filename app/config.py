from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    upstream_base_url: str = "https://cyprus-water.appspot.com/api"
    upstream_timeout_seconds: float = 30.0
    db_path: str = "data/water.db"
    sync_interval_hours: int = 6
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False
    base_url: str = "https://nero.cy"

    model_config = {"env_prefix": "WL_", "env_file": ".env"}


settings = Settings()
