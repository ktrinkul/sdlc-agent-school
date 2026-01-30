from __future__ import annotations

from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    # GitHub
    github_token: str = Field(..., env="GITHUB_TOKEN")
    github_repo_owner: str = Field(..., env="GITHUB_REPO_OWNER")
    github_repo_name: str = Field(..., env="GITHUB_REPO_NAME")
    github_webhook_secret: str | None = Field(None, env="GITHUB_WEBHOOK_SECRET")
    github_auth_mode: Literal["pat", "app"] = Field("pat", env="GITHUB_AUTH_MODE")
    github_app_id: str | None = Field(None, env="GITHUB_APP_ID")
    github_app_private_key_path: str | None = Field(None, env="GITHUB_APP_PRIVATE_KEY_PATH")
    github_app_installation_id: int | None = Field(None, env="GITHUB_APP_INSTALLATION_ID")

    # LLM
    llm_provider: Literal["openai", "yandex"] = Field("openai", env="LLM_PROVIDER")
    llm_model: str = Field("gpt-4o-mini", env="LLM_MODEL")
    openai_api_key: str | None = Field(None, env="OPENAI_API_KEY")
    openai_base_url: str = Field("https://api.openai.com/v1", env="OPENAI_BASE_URL")
    openrouter_referer: str | None = Field(None, env="OPENROUTER_REFERER")
    openrouter_title: str | None = Field(None, env="OPENROUTER_TITLE")
    yandex_api_key: str | None = Field(None, env="YANDEX_API_KEY")
    yandex_folder_id: str | None = Field(None, env="YANDEX_FOLDER_ID")

    # Agent
    max_iterations: int = Field(5, env="MAX_ITERATIONS")
    base_branch: str = Field("main", env="BASE_BRANCH")
    log_level: str = Field("INFO", env="LOG_LEVEL")

    model_config = SettingsConfigDict(
        env_file=".env", case_sensitive=False, extra="ignore"
    )


settings = Settings()
