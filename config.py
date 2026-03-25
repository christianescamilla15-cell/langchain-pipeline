"""Centralized configuration using Pydantic Settings."""
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    app_name: str = "LangChain Pipeline"
    mode: str = "demo"
    anthropic_api_key: str = ""
    aws_default_region: str = ""
    pipeline_api_key: str = "demo"
    cors_origins: str = "http://localhost:3000,http://localhost:5173,https://langchain-pipeline.vercel.app"
    host: str = "0.0.0.0"
    port: int = 8000
    log_level: str = "INFO"
    max_content_length: int = 100000

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",")]


@lru_cache
def get_settings() -> Settings:
    return Settings()
