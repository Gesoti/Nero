from pydantic import model_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    upstream_base_url: str = "https://cyprus-water.appspot.com/api"
    upstream_timeout_seconds: float = 30.0
    db_path: str = ""
    sync_interval_hours: int = 6
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False
    base_url: str = "https://nero.cy"
    country: str = "cy"
    locale: str = "en"
    enabled_countries: str = "cy,gr,es,pt,cz,at,it,fi,no,ch,bg,de,pl"
    adsense_pub_id: str = ""

    model_config = {"env_prefix": "WL_", "env_file": ".env"}

    @model_validator(mode="after")
    def _set_default_db_path(self) -> "Settings":
        if not self.db_path:
            self.db_path = f"data/{self.country}/water.db"
        return self

    def get_enabled_countries(self) -> list[str]:
        """Parse enabled_countries CSV string into a list."""
        return [c.strip() for c in self.enabled_countries.split(",") if c.strip()]


settings = Settings()
