from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "STEH"
    app_env: str = "local"
    log_level: str = "INFO"

    database_url: str
    langgraph_database_url: str

    llm_mode: str = Field(default="stub", pattern="^(stub|openai)$")
    llm_model: str = "gpt-5-mini"
    openai_api_key: str | None = None

    auth_enabled: bool = False
    auth_jwt_secret: str = "change-me-local-only"
    auth_jwt_algorithm: str = "HS256"
    auth_required_role: str = "steh_user"

    policy_file: str = "policies/quality-gates.yaml"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    # BaseSettings resolves required values such as database_url and
    # langgraph_database_url from environment variables / .env at runtime.
    # Static type checking cannot infer that configuration injection.
    return Settings()  # type: ignore[call-arg]


settings = get_settings()