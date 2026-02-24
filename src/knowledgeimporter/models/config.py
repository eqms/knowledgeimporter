"""Application configuration model."""

from pathlib import Path

from pydantic import BaseModel, Field

# Default config directory
CONFIG_DIR = Path.home() / ".knowledgeimporter"
CONFIG_FILE = CONFIG_DIR / "config.json"


class AppConfig(BaseModel):
    """Configuration for the KnowledgeImporter application."""

    langdock_api_key: str = ""
    region: str = Field(default="eu", pattern="^(eu|us)$")
    default_folder_id: str = ""
    folder_name: str = ""
    last_source_dir: str = ""
    file_patterns: list[str] = Field(default_factory=lambda: ["*.md"])
    replace_existing: bool = True
