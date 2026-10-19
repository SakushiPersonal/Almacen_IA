from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str

@lru_cache
def get_settings() -> Settings:
    """Built on first call, then cached for the life of the process."""
    return Settings()