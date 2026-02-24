"""Tests for storage utilities — encryption roundtrip, config load/save."""

import json
from unittest.mock import MagicMock, patch

from knowledgeimporter.models.config import AppConfig


class TestGetOrCreateMasterKey:
    """Test master key generation and retrieval."""

    @patch("knowledgeimporter.utils.storage.keyring")
    @patch("knowledgeimporter.utils.storage.FernetEncryption")
    def test_creates_new_key_if_missing(self, mock_fernet, mock_keyring):
        mock_keyring.get_password.return_value = None
        mock_fernet.generate_key.return_value = "new-master-key"

        from knowledgeimporter.utils.storage import get_or_create_master_key

        key = get_or_create_master_key()

        assert key == "new-master-key"
        mock_keyring.set_password.assert_called_once_with("knowledgeimporter", "master_key", "new-master-key")

    @patch("knowledgeimporter.utils.storage.keyring")
    def test_returns_existing_key(self, mock_keyring):
        mock_keyring.get_password.return_value = "existing-key"

        from knowledgeimporter.utils.storage import get_or_create_master_key

        key = get_or_create_master_key()

        assert key == "existing-key"
        mock_keyring.set_password.assert_not_called()


class TestSaveAndLoadConfig:
    """Test config save/load with encryption."""

    @patch("knowledgeimporter.utils.storage.get_or_create_master_key")
    @patch("knowledgeimporter.utils.storage.CONFIG_FILE")
    @patch("knowledgeimporter.utils.storage.CONFIG_DIR")
    def test_save_config_encrypts_api_key(self, mock_dir, mock_file, mock_get_key):
        mock_get_key.return_value = "dGVzdC1rZXktMTIzNDU2Nzg5MDEyMzQ1Njc4OTAxMjM0NTY3ODkwMTI="  # noqa: E501

        mock_dir.mkdir = MagicMock()
        written_data = {}

        def capture_write(content, encoding=None):
            written_data["json"] = content

        mock_file.write_text = capture_write

        # Use real FernetEncryption for roundtrip
        from eq_chatbot_core.security.encryption import FernetEncryption

        real_key = FernetEncryption.generate_key()
        mock_get_key.return_value = real_key

        from knowledgeimporter.utils.storage import save_config

        config = AppConfig(langdock_api_key="my-secret-api-key", folder_name="Test")
        save_config(config)

        assert "json" in written_data
        saved = json.loads(written_data["json"])
        # API key should NOT be plaintext
        assert saved["langdock_api_key"] != "my-secret-api-key"
        assert saved["langdock_api_key"] != ""
        # Other fields should be preserved
        assert saved["folder_name"] == "Test"

    @patch("knowledgeimporter.utils.storage.get_or_create_master_key")
    @patch("knowledgeimporter.utils.storage.CONFIG_FILE")
    @patch("knowledgeimporter.utils.storage.CONFIG_DIR")
    def test_save_config_empty_key_not_encrypted(self, mock_dir, mock_file, mock_get_key):
        mock_dir.mkdir = MagicMock()
        written_data = {}

        def capture_write(content, encoding=None):
            written_data["json"] = content

        mock_file.write_text = capture_write

        from knowledgeimporter.utils.storage import save_config

        config = AppConfig(langdock_api_key="", folder_name="Test")
        save_config(config)

        saved = json.loads(written_data["json"])
        assert saved["langdock_api_key"] == ""
        mock_get_key.assert_not_called()

    @patch("knowledgeimporter.utils.storage.CONFIG_FILE")
    def test_load_config_file_not_found(self, mock_file):
        mock_file.exists.return_value = False

        from knowledgeimporter.utils.storage import load_config

        config = load_config()
        assert config == AppConfig()

    @patch("knowledgeimporter.utils.storage.get_or_create_master_key")
    @patch("knowledgeimporter.utils.storage.CONFIG_FILE")
    def test_load_config_decrypts_api_key(self, mock_file, mock_get_key):
        from eq_chatbot_core.security.encryption import FernetEncryption

        real_key = FernetEncryption.generate_key()
        mock_get_key.return_value = real_key

        enc = FernetEncryption(real_key)
        encrypted = enc.encrypt_to_string("my-secret-api-key")

        config_data = {
            "langdock_api_key": encrypted,
            "region": "eu",
            "default_folder_id": "folder-123",
            "folder_name": "Test",
            "last_source_dir": "",
            "file_patterns": ["*.md"],
            "replace_existing": True,
        }

        mock_file.exists.return_value = True
        mock_file.read_text.return_value = json.dumps(config_data)

        from knowledgeimporter.utils.storage import load_config

        config = load_config()
        assert config.langdock_api_key == "my-secret-api-key"
        assert config.default_folder_id == "folder-123"

    @patch("knowledgeimporter.utils.storage.CONFIG_FILE")
    def test_load_config_corrupt_json(self, mock_file):
        mock_file.exists.return_value = True
        mock_file.read_text.return_value = "not valid json {"

        from knowledgeimporter.utils.storage import load_config

        config = load_config()
        assert config == AppConfig()


class TestEncryptionRoundtrip:
    """Test full encryption roundtrip with real FernetEncryption."""

    def test_encrypt_decrypt_roundtrip(self):
        from eq_chatbot_core.security.encryption import FernetEncryption

        key = FernetEncryption.generate_key()
        enc = FernetEncryption(key)

        original = "my-super-secret-api-key-12345"
        encrypted = enc.encrypt_to_string(original)
        decrypted = enc.decrypt_from_string(encrypted)

        assert decrypted == original
        assert encrypted != original

    def test_empty_string_roundtrip(self):
        from eq_chatbot_core.security.encryption import FernetEncryption

        key = FernetEncryption.generate_key()
        enc = FernetEncryption(key)

        encrypted = enc.encrypt_to_string("")
        decrypted = enc.decrypt_from_string(encrypted)

        assert decrypted == ""


class TestValidateFolder:
    """Test folder validation."""

    def test_validate_folder_success(self):
        mock_km = MagicMock()
        mock_km.list_files.return_value = [
            {"id": "f1", "name": "file1.md"},
            {"id": "f2", "name": "file2.md"},
        ]

        with patch(
            "eq_chatbot_core.providers.langdock_provider.LangDockKnowledgeManager",
            return_value=mock_km,
        ):
            from knowledgeimporter.utils.storage import validate_folder

            ok, count = validate_folder("api-key", "folder-id")

        assert ok is True
        assert count == 2

    def test_validate_folder_empty_inputs(self):
        from knowledgeimporter.utils.storage import validate_folder

        ok, count = validate_folder("", "folder-id")
        assert ok is False
        assert count == 0

        ok, count = validate_folder("api-key", "")
        assert ok is False
        assert count == 0

    def test_test_api_connection_empty_key(self):
        from knowledgeimporter.utils.storage import test_api_connection

        assert test_api_connection("") is False
