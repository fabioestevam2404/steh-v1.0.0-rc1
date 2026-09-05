from functools import lru_cache

from pydantic import Field, SecretStr
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
    auth_reviewer_role: str = "steh_reviewer"
    human_review_ttl_minutes: int = Field(default=60, ge=1, le=10080)

    context_max_sources: int = Field(default=10, ge=1, le=50)
    context_max_tokens: int = Field(default=4000, ge=128, le=50000)
    context_max_source_tokens: int = Field(default=2000, ge=64, le=25000)

    github_api_url: str = "https://api.github.com"
    github_api_version: str = Field(
        default="2026-03-10",
        pattern=r"^\d{4}-\d{2}-\d{2}$",
    )
    github_token: SecretStr | None = None
    github_timeout_seconds: float = Field(default=10.0, ge=1.0, le=30.0)
    github_issue_max_body_chars: int = Field(default=20000, ge=1000, le=100000)
    github_allowed_repositories: str = ""

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
