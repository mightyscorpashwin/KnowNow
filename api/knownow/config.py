"""Settings read from app settings (environment variables)."""
from __future__ import annotations

import os
from dataclasses import dataclass, field


def _split(value: str) -> frozenset[str]:
    return frozenset(v.strip().lower() for v in value.split(",") if v.strip())


@dataclass(frozen=True)
class Settings:
    cosmos_endpoint: str = ""
    cosmos_database: str = "knownow"
    openai_endpoint: str = ""
    openai_deployment: str = "content"
    openai_api_version: str = "2025-04-01-preview"
    blob_endpoint: str = ""
    learn_mcp_url: str = "https://learn.microsoft.com/api/mcp"
    reviewer_emails: frozenset[str] = field(default_factory=frozenset)
    reviewer_group_id: str = ""
    environment: str = "dev"


def load_settings() -> Settings:
    env = os.environ.get
    return Settings(
        cosmos_endpoint=env("COSMOS_ENDPOINT", ""),
        cosmos_database=env("COSMOS_DATABASE", "knownow"),
        openai_endpoint=env("AZURE_OPENAI_ENDPOINT", ""),
        openai_deployment=env("AZURE_OPENAI_DEPLOYMENT", "content"),
        openai_api_version=env("AZURE_OPENAI_API_VERSION", "2025-04-01-preview"),
        blob_endpoint=env("STORAGE_BLOB_ENDPOINT", ""),
        learn_mcp_url=env("LEARN_MCP_URL", "https://learn.microsoft.com/api/mcp"),
        reviewer_emails=_split(env("REVIEWER_EMAILS", "")),
        reviewer_group_id=env("REVIEWER_GROUP_ID", "").strip().lower(),
        environment=env("KNOWNOW_ENVIRONMENT", "dev"),
    )
