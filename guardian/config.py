"""
DataHub Health Guardian — Configuration
"""
import os
from dataclasses import dataclass, field
from dotenv import load_dotenv

load_dotenv()


@dataclass
class Config:
    """Application configuration loaded from environment variables."""

    # DataHub connection
    datahub_gms_url: str = field(
        default_factory=lambda: os.getenv("DATAHUB_GMS_URL", "http://localhost:8080")
    )
    datahub_token: str = field(
        default_factory=lambda: os.getenv("DATAHUB_TOKEN", "")
    )

    # Google Gemini API
    google_api_key: str = field(
        default_factory=lambda: os.getenv("GOOGLE_API_KEY", "")
    )

    # Agent settings
    scan_interval: int = field(
        default_factory=lambda: int(os.getenv("AGENT_SCAN_INTERVAL", "300"))
    )
    log_level: str = field(
        default_factory=lambda: os.getenv("LOG_LEVEL", "INFO")
    )

    # Model configuration
    model_name: str = "gemini-2.0-flash"
    max_output_tokens: int = 8192
    temperature: float = 0.2

    def validate(self) -> list[str]:
        """Validate configuration, return list of issues."""
        issues = []
        if not self.datahub_token:
            issues.append("DATAHUB_TOKEN is not set")
        if not self.google_api_key:
            issues.append("GOOGLE_API_KEY is not set")
        return issues
