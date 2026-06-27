from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg2://spendsync:spendsync@db:5432/spendsync"
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24
    nbp_base_url: str = "https://api.nbp.pl/api"

    @property
    def connect_args(self) -> dict:
        if self.database_url.startswith("sqlite"):
            return {"check_same_thread": False}
        return {}


settings = Settings()
