"""Upload orchestration service for batch uploading files to LangDock Knowledge Folders."""

import fnmatch
import logging
from collections.abc import Callable
from pathlib import Path
from typing import Any

from eq_chatbot_core.providers.langdock_provider import LangDockKnowledgeManager

logger = logging.getLogger(__name__)

# Type alias for progress callback: (current, total, filename, status)
ProgressCallback = Callable[[int, int, str, str], None]


class UploadService:
    """Orchestrates batch file uploads to LangDock Knowledge Folders."""

    def __init__(self, api_key: str) -> None:
        self._km = LangDockKnowledgeManager(api_key=api_key)
        self._cancelled = False

    def cancel(self) -> None:
        """Signal cancellation of the current batch operation."""
        self._cancelled = True

    @property
    def is_cancelled(self) -> bool:
        return self._cancelled

    def list_folder_files(self, folder_id: str) -> list[dict[str, Any]]:
        """List all files in a knowledge folder."""
        return self._km.list_files(folder_id)

    def clear_folder(self, folder_id: str) -> int:
        """Delete all files in a folder. Returns count of deleted files."""
        files = self._km.list_files(folder_id)
        deleted = 0
        for f in files:
            file_id = f.get("id", "")
            if file_id:
                try:
                    self._km.delete_file(folder_id, file_id)
                    deleted += 1
                except Exception as e:
                    logger.warning("Failed to delete file %s: %s", file_id, e)
        return deleted

    def collect_files(self, source_dir: str, patterns: list[str]) -> list[Path]:
        """Collect files matching the given glob patterns from source directory."""
        source = Path(source_dir)
        if not source.is_dir():
            return []

        matched: list[Path] = []
        for item in sorted(source.iterdir()):
            if not item.is_file():
                continue
            for pattern in patterns:
                if fnmatch.fnmatch(item.name, pattern):
                    matched.append(item)
                    break
        return matched

    def upload_batch(
        self,
        source_dir: str,
        folder_id: str,
        patterns: list[str],
        replace: bool = True,
        on_progress: ProgressCallback | None = None,
    ) -> dict[str, Any]:
        """
        Upload all matching files from source_dir to the LangDock folder.

        Returns a summary dict with keys: total, success, failed, skipped, errors.
        """
        self._cancelled = False
        files = self.collect_files(source_dir, patterns)
        total = len(files)
        success = 0
        failed = 0
        skipped = 0
        errors: list[dict[str, str]] = []

        if total == 0:
            return {"total": 0, "success": 0, "failed": 0, "skipped": 0, "errors": []}

        # If replace mode, get existing files for comparison
        existing_files: dict[str, str] = {}
        if replace:
            try:
                for f in self._km.list_files(folder_id):
                    name = f.get("name", "")
                    file_id = f.get("id", "")
                    if name and file_id:
                        existing_files[name] = file_id
            except Exception as e:
                logger.warning("Could not list existing files: %s", e)

        for i, file_path in enumerate(files):
            if self._cancelled:
                skipped = total - i
                if on_progress:
                    on_progress(i, total, "", "cancelled")
                break

            filename = file_path.name
            if on_progress:
                on_progress(i, total, filename, "uploading")

            try:
                # Delete existing file if replace mode is on
                if replace and filename in existing_files:
                    try:
                        self._km.delete_file(folder_id, existing_files[filename])
                        logger.debug("Deleted existing file: %s", filename)
                    except Exception as e:
                        logger.warning("Could not delete existing %s: %s", filename, e)

                self._km.upload_file(folder_id, str(file_path), filename=filename)
                success += 1

                if on_progress:
                    on_progress(i + 1, total, filename, "success")

            except Exception as e:
                failed += 1
                error_msg = str(e)
                errors.append({"file": filename, "error": error_msg})
                logger.error("Upload failed for %s: %s", filename, error_msg)

                if on_progress:
                    on_progress(i + 1, total, filename, "error")

        return {
            "total": total,
            "success": success,
            "failed": failed,
            "skipped": skipped,
            "errors": errors,
        }
