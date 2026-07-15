from pydantic_settings import SettingsConfigDict
from functools import lru_cache
from pydantic_settings import BaseSettings
SettingsConfigDict


class Settings(BaseSettings):
    model_config= SettingsConfigDict(env_file=".env" ,extra="ignore")

    environment: str = "development"
    database_url: str
    supabase_url: str
    supabase_service_role_key: str
    supabase_jwt_secret: str
    redis_url: str
    cors_origins: str = "http://localhost:5173"
    stripe_secret_key: str = ""
    stripe_enabled: bool = False 


    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",")]

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()