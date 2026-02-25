"""Tests for file-based upload logging."""

import time
from unittest.mock import patch

from knowledgeimporter.utils.upload_logger import (
    append_log,
    cleanup_old_logs,
    create_upload_log,
    finalize_log,
    get_latest_log,
)


class TestCreateUploadLog:
    def test_creates_log_file(self, tmp_path):
        with patch("knowledgeimporter.utils.upload_logger.LOG_DIR", tmp_path):
            log_file = create_upload_log()
            assert log_file.exists()
            assert log_file.name.startswith("upload_")
            assert log_file.suffix == ".log"

    def test_log_file_has_header(self, tmp_path):
        with patch("knowledgeimporter.utils.upload_logger.LOG_DIR", tmp_path):
            log_file = create_upload_log()
            content = log_file.read_text(encoding="utf-8")
            assert "KnowledgeImporter Upload Log" in content
            assert "Started:" in content


class TestAppendLog:
    def test_append_message(self, tmp_path):
        log_file = tmp_path / "test.log"
        log_file.write_text("", encoding="utf-8")
        append_log(log_file, "Test message")
        content = log_file.read_text(encoding="utf-8")
        assert "Test message" in content
        assert "] " in content  # timestamp bracket

    def test_append_multiple_messages(self, tmp_path):
        log_file = tmp_path / "test.log"
        log_file.write_text("", encoding="utf-8")
        append_log(log_file, "First")
        append_log(log_file, "Second")
        content = log_file.read_text(encoding="utf-8")
        assert "First" in content
        assert "Second" in content


class TestFinalizeLog:
    def test_writes_summary(self, tmp_path):
        log_file = tmp_path / "test.log"
        log_file.write_text("", encoding="utf-8")
        result = {"total": 10, "success": 8, "failed": 1, "skipped": 1}
        finalize_log(log_file, result)
        content = log_file.read_text(encoding="utf-8")
        assert "Completed:" in content
        assert "Total: 10" in content
        assert "Success: 8" in content
        assert "Failed: 1" in content

    def test_writes_errors(self, tmp_path):
        log_file = tmp_path / "test.log"
        log_file.write_text("", encoding="utf-8")
        result = {"total": 1, "success": 0, "failed": 1, "errors": ["file.md: API error"]}
        finalize_log(log_file, result)
        content = log_file.read_text(encoding="utf-8")
        assert "Errors:" in content
        assert "file.md: API error" in content


class TestCleanupOldLogs:
    def test_deletes_old_logs(self, tmp_path):
        with patch("knowledgeimporter.utils.upload_logger.LOG_DIR", tmp_path):
            # Create an "old" log file
            old_log = tmp_path / "upload_20240101_120000.log"
            old_log.write_text("old", encoding="utf-8")
            # Set mtime to 30 days ago
            old_time = time.time() - (30 * 86400)
            import os

            os.utime(old_log, (old_time, old_time))

            deleted = cleanup_old_logs(retention_days=7)
            assert deleted == 1
            assert not old_log.exists()

    def test_keeps_recent_logs(self, tmp_path):
        with patch("knowledgeimporter.utils.upload_logger.LOG_DIR", tmp_path):
            recent_log = tmp_path / "upload_20260225_120000.log"
            recent_log.write_text("recent", encoding="utf-8")

            deleted = cleanup_old_logs(retention_days=7)
            assert deleted == 0
            assert recent_log.exists()


class TestGetLatestLog:
    def test_returns_latest(self, tmp_path):
        with patch("knowledgeimporter.utils.upload_logger.LOG_DIR", tmp_path):
            log1 = tmp_path / "upload_20260101_100000.log"
            log2 = tmp_path / "upload_20260225_120000.log"
            log1.write_text("old", encoding="utf-8")
            time.sleep(0.01)  # Ensure different mtime
            log2.write_text("new", encoding="utf-8")

            latest = get_latest_log()
            assert latest == log2

    def test_returns_none_when_empty(self, tmp_path):
        with patch("knowledgeimporter.utils.upload_logger.LOG_DIR", tmp_path):
            assert get_latest_log() is None
