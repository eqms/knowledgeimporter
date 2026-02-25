"""Tests for AppConfig model."""

import pytest
from pydantic import ValidationError

from knowledgeimporter.models.config import AppConfig


class TestAppConfig:
    """Test AppConfig serialization and validation."""

    def test_default_values(self):
        config = AppConfig()
        assert config.langdock_api_key == ""
        assert config.region == "eu"
        assert config.default_folder_id == ""
        assert config.folder_name == ""
        assert config.last_source_dir == ""
        assert "*.md" in config.file_patterns
        assert "*.pdf" in config.file_patterns
        assert "*.docx" in config.file_patterns
        assert "*.odt" in config.file_patterns
        assert config.replace_existing is True

    def test_custom_values(self):
        config = AppConfig(
            langdock_api_key="test-key-123",
            region="us",
            default_folder_id="abc-def-123",
            folder_name="My Folder",
            last_source_dir="/tmp/docs",
            file_patterns=["*.md", "*.txt"],
            replace_existing=False,
        )
        assert config.langdock_api_key == "test-key-123"
        assert config.region == "us"
        assert config.default_folder_id == "abc-def-123"
        assert config.folder_name == "My Folder"
        assert config.last_source_dir == "/tmp/docs"
        assert config.file_patterns == ["*.md", "*.txt"]
        assert config.replace_existing is False

    def test_region_validation_eu(self):
        config = AppConfig(region="eu")
        assert config.region == "eu"

    def test_region_validation_us(self):
        config = AppConfig(region="us")
        assert config.region == "us"

    def test_region_validation_invalid(self):
        with pytest.raises(ValidationError):
            AppConfig(region="asia")

    def test_model_dump_roundtrip(self):
        original = AppConfig(
            langdock_api_key="secret",
            region="us",
            default_folder_id="folder-id",
            folder_name="Test Folder",
            file_patterns=["*.md", "*.txt"],
        )
        data = original.model_dump()
        restored = AppConfig(**data)
        assert restored == original

    def test_model_dump_json_roundtrip(self):
        original = AppConfig(langdock_api_key="key", folder_name="Test")
        json_str = original.model_dump_json()
        restored = AppConfig.model_validate_json(json_str)
        assert restored == original

    def test_empty_patterns_list(self):
        config = AppConfig(file_patterns=[])
        assert config.file_patterns == []

    def test_file_patterns_default_factory(self):
        """Ensure default factory creates independent lists."""
        config1 = AppConfig()
        config2 = AppConfig()
        config1.file_patterns.append("*.txt")
        assert "*.txt" not in config2.file_patterns


class TestAppConfigNewFormats:
    """Test that new Universal Converter formats are included in default file_patterns."""

    def test_default_patterns_include_csv(self):
        config = AppConfig()
        assert "*.csv" in config.file_patterns

    def test_default_patterns_include_json(self):
        config = AppConfig()
        assert "*.json" in config.file_patterns

    def test_default_patterns_include_xlsx(self):
        config = AppConfig()
        assert "*.xlsx" in config.file_patterns

    def test_default_patterns_include_yaml(self):
        config = AppConfig()
        assert "*.yaml" in config.file_patterns

    def test_default_patterns_include_xml(self):
        config = AppConfig()
        assert "*.xml" in config.file_patterns
