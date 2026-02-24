"""Tests for UploadService — batch upload, cancel, error handling."""

from unittest.mock import MagicMock, patch


class TestCollectFiles:
    """Test file collection with pattern matching."""

    def test_collect_markdown_files(self, tmp_path):
        (tmp_path / "doc1.md").write_text("# Doc 1")
        (tmp_path / "doc2.md").write_text("# Doc 2")
        (tmp_path / "readme.txt").write_text("readme")
        (tmp_path / "image.png").write_bytes(b"\x89PNG")

        with patch.dict(
            "sys.modules",
            {
                "eq_chatbot_core": MagicMock(),
                "eq_chatbot_core.providers": MagicMock(),
                "eq_chatbot_core.providers.langdock_provider": MagicMock(),
            },
        ):
            from knowledgeimporter.services.upload_service import UploadService

            svc = UploadService.__new__(UploadService)
            svc._cancelled = False
            files = svc.collect_files(str(tmp_path), ["*.md"])

        assert len(files) == 2
        names = [f.name for f in files]
        assert "doc1.md" in names
        assert "doc2.md" in names

    def test_collect_multiple_patterns(self, tmp_path):
        (tmp_path / "doc.md").write_text("# Doc")
        (tmp_path / "notes.txt").write_text("notes")
        (tmp_path / "image.png").write_bytes(b"\x89PNG")

        with patch.dict(
            "sys.modules",
            {
                "eq_chatbot_core": MagicMock(),
                "eq_chatbot_core.providers": MagicMock(),
                "eq_chatbot_core.providers.langdock_provider": MagicMock(),
            },
        ):
            from knowledgeimporter.services.upload_service import UploadService

            svc = UploadService.__new__(UploadService)
            svc._cancelled = False
            files = svc.collect_files(str(tmp_path), ["*.md", "*.txt"])

        assert len(files) == 2

    def test_collect_nonexistent_dir(self):
        with patch.dict(
            "sys.modules",
            {
                "eq_chatbot_core": MagicMock(),
                "eq_chatbot_core.providers": MagicMock(),
                "eq_chatbot_core.providers.langdock_provider": MagicMock(),
            },
        ):
            from knowledgeimporter.services.upload_service import UploadService

            svc = UploadService.__new__(UploadService)
            svc._cancelled = False
            files = svc.collect_files("/nonexistent/path", ["*.md"])

        assert files == []

    def test_collect_empty_dir(self, tmp_path):
        with patch.dict(
            "sys.modules",
            {
                "eq_chatbot_core": MagicMock(),
                "eq_chatbot_core.providers": MagicMock(),
                "eq_chatbot_core.providers.langdock_provider": MagicMock(),
            },
        ):
            from knowledgeimporter.services.upload_service import UploadService

            svc = UploadService.__new__(UploadService)
            svc._cancelled = False
            files = svc.collect_files(str(tmp_path), ["*.md"])

        assert files == []


class TestUploadBatch:
    """Test batch upload orchestration."""

    def _make_service_with_mock_km(self):
        """Create an UploadService with a mocked KnowledgeManager."""
        mock_km = MagicMock()
        mock_km.list_files.return_value = []
        mock_km.upload_file.return_value = {"id": "new-file-id"}

        with patch.dict(
            "sys.modules",
            {
                "eq_chatbot_core": MagicMock(),
                "eq_chatbot_core.providers": MagicMock(),
                "eq_chatbot_core.providers.langdock_provider": MagicMock(),
            },
        ):
            from knowledgeimporter.services.upload_service import UploadService

            svc = UploadService.__new__(UploadService)
            svc._km = mock_km
            svc._cancelled = False

        return svc, mock_km

    def test_upload_batch_success(self, tmp_path):
        (tmp_path / "doc1.md").write_text("# Doc 1")
        (tmp_path / "doc2.md").write_text("# Doc 2")

        svc, mock_km = self._make_service_with_mock_km()
        progress_calls = []

        result = svc.upload_batch(
            source_dir=str(tmp_path),
            folder_id="folder-123",
            patterns=["*.md"],
            replace=False,
            on_progress=lambda *args: progress_calls.append(args),
        )

        assert result["total"] == 2
        assert result["success"] == 2
        assert result["failed"] == 0
        assert result["errors"] == []
        assert mock_km.upload_file.call_count == 2
        assert len(progress_calls) > 0

    def test_upload_batch_with_replace(self, tmp_path):
        (tmp_path / "doc1.md").write_text("# Doc 1")

        svc, mock_km = self._make_service_with_mock_km()
        mock_km.list_files.return_value = [{"id": "existing-id", "name": "doc1.md"}]

        result = svc.upload_batch(
            source_dir=str(tmp_path),
            folder_id="folder-123",
            patterns=["*.md"],
            replace=True,
        )

        assert result["success"] == 1
        # Should have deleted the existing file first
        mock_km.delete_file.assert_called_once_with("folder-123", "existing-id")

    def test_upload_batch_empty_dir(self, tmp_path):
        svc, mock_km = self._make_service_with_mock_km()

        result = svc.upload_batch(
            source_dir=str(tmp_path),
            folder_id="folder-123",
            patterns=["*.md"],
        )

        assert result["total"] == 0
        assert result["success"] == 0
        mock_km.upload_file.assert_not_called()

    def test_upload_batch_partial_failure(self, tmp_path):
        (tmp_path / "good.md").write_text("# Good")
        (tmp_path / "bad.md").write_text("# Bad")

        svc, mock_km = self._make_service_with_mock_km()

        def upload_side_effect(folder_id, file_path, filename=None):
            if "bad.md" in str(file_path):
                raise RuntimeError("Upload failed for bad.md")
            return {"id": "ok"}

        mock_km.upload_file.side_effect = upload_side_effect

        result = svc.upload_batch(
            source_dir=str(tmp_path),
            folder_id="folder-123",
            patterns=["*.md"],
            replace=False,
        )

        assert result["total"] == 2
        assert result["success"] == 1
        assert result["failed"] == 1
        assert len(result["errors"]) == 1
        assert result["errors"][0]["file"] == "bad.md"

    def test_upload_batch_cancel(self, tmp_path):
        # Create many files to allow cancellation
        for i in range(10):
            (tmp_path / f"doc{i:02d}.md").write_text(f"# Doc {i}")

        svc, mock_km = self._make_service_with_mock_km()

        call_count = 0

        def upload_and_cancel(folder_id, file_path, filename=None):
            nonlocal call_count
            call_count += 1
            if call_count >= 3:
                svc.cancel()
            return {"id": "ok"}

        mock_km.upload_file.side_effect = upload_and_cancel

        result = svc.upload_batch(
            source_dir=str(tmp_path),
            folder_id="folder-123",
            patterns=["*.md"],
            replace=False,
        )

        # Should have uploaded some and skipped the rest
        assert result["success"] >= 2
        assert result["skipped"] > 0
        assert result["total"] == 10


class TestClearFolder:
    """Test folder clearing."""

    def test_clear_folder(self):
        mock_km = MagicMock()
        mock_km.list_files.return_value = [
            {"id": "f1", "name": "file1.md"},
            {"id": "f2", "name": "file2.md"},
        ]
        mock_km.delete_file.return_value = True

        with patch.dict(
            "sys.modules",
            {
                "eq_chatbot_core": MagicMock(),
                "eq_chatbot_core.providers": MagicMock(),
                "eq_chatbot_core.providers.langdock_provider": MagicMock(),
            },
        ):
            from knowledgeimporter.services.upload_service import UploadService

            svc = UploadService.__new__(UploadService)
            svc._km = mock_km
            svc._cancelled = False

        deleted = svc.clear_folder("folder-123")
        assert deleted == 2
        assert mock_km.delete_file.call_count == 2

    def test_clear_folder_partial_failure(self):
        mock_km = MagicMock()
        mock_km.list_files.return_value = [
            {"id": "f1", "name": "file1.md"},
            {"id": "f2", "name": "file2.md"},
        ]
        mock_km.delete_file.side_effect = [True, RuntimeError("delete failed")]

        with patch.dict(
            "sys.modules",
            {
                "eq_chatbot_core": MagicMock(),
                "eq_chatbot_core.providers": MagicMock(),
                "eq_chatbot_core.providers.langdock_provider": MagicMock(),
            },
        ):
            from knowledgeimporter.services.upload_service import UploadService

            svc = UploadService.__new__(UploadService)
            svc._km = mock_km
            svc._cancelled = False

        deleted = svc.clear_folder("folder-123")
        assert deleted == 1  # Only first succeeded
