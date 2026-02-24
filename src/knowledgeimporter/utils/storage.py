"""Config storage with encrypted API key management."""

import json
import logging

import keyring
from eq_chatbot_core.security.encryption import FernetEncryption

from knowledgeimporter.models.config import CONFIG_DIR, CONFIG_FILE, AppConfig

logger = logging.getLogger(__name__)

KEYRING_SERVICE = "knowledgeimporter"
KEYRING_KEY = "master_key"


def get_or_create_master_key() -> str:
    """Retrieve master encryption key from OS keyring, or create one if missing."""
    key = keyring.get_password(KEYRING_SERVICE, KEYRING_KEY)
    if key is None:
        key = FernetEncryption.generate_key()
        keyring.set_password(KEYRING_SERVICE, KEYRING_KEY, key)
        logger.info("Generated new master encryption key")
    return key


def load_config() -> AppConfig:
    """Load config from disk. Decrypts the API key using the master key."""
    if not CONFIG_FILE.exists():
        return AppConfig()

    try:
        raw = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        logger.warning("Failed to read config file: %s", e)
        return AppConfig()

    encrypted_key = raw.get("langdock_api_key", "")
    if encrypted_key:
        try:
            master_key = get_or_create_master_key()
            enc = FernetEncryption(master_key)
            raw["langdock_api_key"] = enc.decrypt_from_string(encrypted_key)
        except Exception as e:
            logger.warning("Failed to decrypt API key: %s", e)
            raw["langdock_api_key"] = ""

    return AppConfig(**raw)


def save_config(config: AppConfig) -> None:
    """Save config to disk. Encrypts the API key before writing."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    data = config.model_dump()

    if data["langdock_api_key"]:
        master_key = get_or_create_master_key()
        enc = FernetEncryption(master_key)
        data["langdock_api_key"] = enc.encrypt_to_string(data["langdock_api_key"])

    CONFIG_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.info("Config saved to %s", CONFIG_FILE)


def validate_folder(api_key: str, folder_id: str, region: str = "eu") -> tuple[bool, int]:
    """Validate a folder by listing its files. Returns (is_valid, file_count)."""
    if not api_key or not folder_id:
        return False, 0

    try:
        from eq_chatbot_core.providers.langdock_provider import LangDockKnowledgeManager

        km = LangDockKnowledgeManager(api_key=api_key)
        files = km.list_files(folder_id)
        return True, len(files)
    except Exception as e:
        logger.warning("Folder validation failed: %s", e)
        return False, 0


def test_api_connection(api_key: str) -> bool:
    """Test if the API key is valid by attempting a basic API call."""
    if not api_key:
        return False

    try:
        import httpx
        from eq_chatbot_core.providers.langdock_provider import LangDockKnowledgeManager

        km = LangDockKnowledgeManager(api_key=api_key)
        km.list_files("00000000-0000-0000-0000-000000000000")
        return True
    except httpx.HTTPStatusError as e:
        # 404 = key works, folder doesn't exist — that's fine
        if e.response.status_code == 404:
            return True
        # 401/403 = invalid API key
        return False
    except Exception:
        return False
