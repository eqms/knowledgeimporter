"""File-based upload logging with automatic cleanup."""

import logging
import os
import time
from datetime import datetime
from pathlib import Path

from knowledgeimporter.models.config import CONFIG_DIR

logger = logging.getLogger(__name__)

LOG_DIR = CONFIG_DIR / "logs"
DEFAULT_RETENTION_DAYS = 7


def get_log_dir() -> Path:
    """Return the log directory, creating it if necessary."""
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    return LOG_DIR


def create_upload_log() -> Path:
    """Create a new log file for the current upload session."""
    log_dir = get_log_dir()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = log_dir / f"upload_{timestamp}.log"
    log_file.write_text(
        f"# KnowledgeImporter Upload Log\n# Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n# {'=' * 60}\n\n",
        encoding="utf-8",
    )
    return log_file


def append_log(log_file: Path, message: str) -> None:
    """Append a timestamped message to the log file."""
    timestamp = datetime.now().strftime("%H:%M:%S")
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] {message}\n")


def finalize_log(log_file: Path, result: dict) -> None:
    """Write summary to the log file."""
    total = result.get("total", 0)
    success = result.get("success", 0)
    failed = result.get("failed", 0)
    skipped = result.get("skipped", 0)
    converted = result.get("converted", 0)

    with open(log_file, "a", encoding="utf-8") as f:
        f.write(f"\n# {'=' * 60}\n")
        f.write(f"# Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        summary = f"# Total: {total} | Success: {success} | Failed: {failed} | Skipped: {skipped}"
        if converted > 0:
            summary += f" | Converted: {converted}"
        f.write(summary + "\n")

    errors = result.get("errors", [])
    if errors:
        with open(log_file, "a", encoding="utf-8") as f:
            f.write("\n# Errors:\n")
            for err in errors:
                f.write(f"#   - {err}\n")


def cleanup_old_logs(retention_days: int = DEFAULT_RETENTION_DAYS) -> int:
    """Delete log files older than retention_days. Returns count of deleted files."""
    log_dir = get_log_dir()
    cutoff = time.time() - (retention_days * 86400)
    deleted = 0

    for log_file in log_dir.glob("upload_*.log"):
        try:
            if log_file.stat().st_mtime < cutoff:
                log_file.unlink()
                deleted += 1
        except OSError as e:
            logger.warning("Failed to delete old log %s: %s", log_file, e)

    if deleted:
        logger.info("Cleaned up %d old log file(s)", deleted)
    return deleted


def get_latest_log() -> Path | None:
    """Return the most recent log file, or None if no logs exist."""
    log_dir = get_log_dir()
    logs = sorted(log_dir.glob("upload_*.log"), key=lambda p: p.stat().st_mtime, reverse=True)
    return logs[0] if logs else None


def open_log_in_editor(log_file: Path) -> None:
    """Open a log file in the system's default text editor."""
    import subprocess
    import sys

    try:
        if sys.platform == "darwin":
            subprocess.Popen(["open", str(log_file)])
        elif sys.platform == "win32":
            os.startfile(str(log_file))  # noqa: S606
        else:
            subprocess.Popen(["xdg-open", str(log_file)])
    except Exception as e:
        logger.error("Failed to open log file: %s", e)
