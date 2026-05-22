from pydantic import AnyUrl
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: AnyUrl = 'postgresql+asyncpg://bottrader:bottrader@postgres:5432/bottrading'
    redis_url: str = 'redis://redis:6379/0'
    ollama_url: str = 'http://127.0.0.1:11434'
    environment: str = 'development'
    api_prefix: str = '/api/v1'
    vnstock_enable: bool = True
    # Chu kỳ sync giá (VCI / vnstock) — mục tiêu trễ ≤ quote_max_delay_seconds
    quote_sync_interval_seconds: int = 8
    quote_max_delay_seconds: int = 10

    class Config:
        env_file = '.env'
        env_file_encoding = 'utf-8'
        extra = 'ignore'  # Ignore extra fields from .env


settings = Settings()
