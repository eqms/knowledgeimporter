"""Tests for ConversionService — file conversion to Markdown."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from knowledgeimporter.services.converter import (
    ConversionError,
    ConversionService,
)


class TestNeedsConversion:
    """Test extension classification for conversion requirement."""

    def test_markdown_no_conversion(self):
        assert ConversionService.needs_conversion(Path("doc.md")) is False

    def test_pdf_needs_conversion(self):
        assert ConversionService.needs_conversion(Path("doc.pdf")) is True

    def test_docx_needs_conversion(self):
        assert ConversionService.needs_conversion(Path("doc.docx")) is True

    def test_html_needs_conversion(self):
        assert ConversionService.needs_conversion(Path("page.html")) is True

    def test_htm_needs_conversion(self):
        assert ConversionService.needs_conversion(Path("page.htm")) is True

    def test_odt_needs_conversion(self):
        assert ConversionService.needs_conversion(Path("doc.odt")) is True

    def test_unsupported_no_conversion(self):
        assert ConversionService.needs_conversion(Path("image.png")) is False

    def test_txt_no_conversion(self):
        assert ConversionService.needs_conversion(Path("notes.txt")) is False

    def test_case_insensitive(self):
        assert ConversionService.needs_conversion(Path("DOC.PDF")) is True
        assert ConversionService.needs_conversion(Path("Page.HTML")) is True


class TestIsSupported:
    """Test file support detection (native + convertible)."""

    def test_markdown_supported(self):
        assert ConversionService.is_supported(Path("doc.md")) is True

    def test_pdf_supported(self):
        assert ConversionService.is_supported(Path("doc.pdf")) is True

    def test_docx_supported(self):
        assert ConversionService.is_supported(Path("doc.docx")) is True

    def test_html_supported(self):
        assert ConversionService.is_supported(Path("page.html")) is True

    def test_odt_supported(self):
        assert ConversionService.is_supported(Path("doc.odt")) is True

    def test_png_not_supported(self):
        assert ConversionService.is_supported(Path("image.png")) is False

    def test_txt_not_supported(self):
        assert ConversionService.is_supported(Path("notes.txt")) is False


class TestTempDirLifecycle:
    """Test temporary directory creation and cleanup."""

    def test_create_temp_dir(self):
        svc = ConversionService()
        temp_dir = svc.create_temp_dir()
        assert temp_dir.exists()
        assert temp_dir.is_dir()
        svc.cleanup()

    def test_cleanup_removes_dir(self):
        svc = ConversionService()
        temp_dir = svc.create_temp_dir()
        # Create a file inside to verify full cleanup
        (temp_dir / "test.md").write_text("# Test")
        svc.cleanup()
        assert not temp_dir.exists()

    def test_cleanup_idempotent(self):
        svc = ConversionService()
        svc.create_temp_dir()
        svc.cleanup()
        # Should not raise on second cleanup
        svc.cleanup()

    def test_cleanup_without_create(self):
        svc = ConversionService()
        # Should not raise when no temp dir was created
        svc.cleanup()


class TestConvertFile:
    """Test convert_file routing and passthrough."""

    def test_markdown_passthrough(self, tmp_path):
        md_file = tmp_path / "doc.md"
        md_file.write_text("# Hello")
        svc = ConversionService()
        result = svc.convert_file(md_file)
        assert result == md_file
        svc.cleanup()

    @patch("markitdown.MarkItDown")
    def test_pdf_routes_to_markitdown(self, mock_cls, tmp_path):
        pdf_file = tmp_path / "doc.pdf"
        pdf_file.write_bytes(b"%PDF-1.4 test")

        mock_result = MagicMock()
        mock_result.text_content = "# Converted PDF"
        mock_cls.return_value.convert.return_value = mock_result

        svc = ConversionService()
        svc.create_temp_dir()
        result = svc.convert_file(pdf_file)

        assert result.suffix == ".md"
        assert result.stem == "doc"
        svc.cleanup()

    @patch("odfdo.Document")
    def test_odt_routes_to_odfdo(self, mock_doc_cls, tmp_path):
        odt_file = tmp_path / "doc.odt"
        odt_file.write_bytes(b"PK fake odt")

        mock_para = MagicMock()
        mock_para.get_formatted_text.return_value = "Hello World"
        mock_body = MagicMock()
        mock_body.get_paragraphs.return_value = [mock_para]
        mock_doc = MagicMock()
        mock_doc.body = mock_body
        mock_doc_cls.return_value = mock_doc

        svc = ConversionService()
        svc.create_temp_dir()
        result = svc.convert_file(odt_file)

        assert result.suffix == ".md"
        assert result.stem == "doc"
        svc.cleanup()

    def test_unsupported_format_raises(self, tmp_path):
        txt_file = tmp_path / "doc.xyz"
        txt_file.write_text("data")

        svc = ConversionService()
        svc.create_temp_dir()

        with pytest.raises(ConversionError, match="Unsupported format"):
            svc.convert_file(txt_file)
        svc.cleanup()


class TestConvertWithMarkitdown:
    """Test markitdown-based conversion."""

    @patch("markitdown.MarkItDown")
    def test_successful_conversion(self, mock_cls, tmp_path):
        pdf_file = tmp_path / "report.pdf"
        pdf_file.write_bytes(b"%PDF-1.4 test content")

        mock_result = MagicMock()
        mock_result.text_content = "# Report\n\nContent here."
        mock_cls.return_value.convert.return_value = mock_result

        svc = ConversionService()
        svc.create_temp_dir()
        result = svc._convert_with_markitdown(pdf_file)

        assert result.exists()
        content = result.read_text(encoding="utf-8")
        assert "# Report" in content
        assert "Content here." in content
        svc.cleanup()

    @patch("markitdown.MarkItDown")
    def test_conversion_error(self, mock_cls, tmp_path):
        pdf_file = tmp_path / "broken.pdf"
        pdf_file.write_bytes(b"not a pdf")

        mock_cls.return_value.convert.side_effect = RuntimeError("Parse error")

        svc = ConversionService()
        svc.create_temp_dir()

        with pytest.raises(ConversionError, match="broken.pdf"):
            svc._convert_with_markitdown(pdf_file)
        svc.cleanup()

    def test_missing_library(self, tmp_path):
        pdf_file = tmp_path / "doc.pdf"
        pdf_file.write_bytes(b"%PDF test")

        svc = ConversionService()
        svc.create_temp_dir()

        with patch.dict("sys.modules", {"markitdown": None}):
            with pytest.raises(ConversionError, match="not installed"):
                svc._convert_with_markitdown(pdf_file)

        svc.cleanup()


class TestConvertODT:
    """Test ODT conversion via odfdo."""

    @patch("odfdo.Document")
    def test_paragraph_extraction(self, mock_doc_cls, tmp_path):
        odt_file = tmp_path / "document.odt"
        odt_file.write_bytes(b"PK fake odt")

        mock_para1 = MagicMock()
        mock_para1.get_formatted_text.return_value = "First paragraph"
        mock_para2 = MagicMock()
        mock_para2.get_formatted_text.return_value = "Second paragraph"
        mock_body = MagicMock()
        mock_body.get_paragraphs.return_value = [mock_para1, mock_para2]
        mock_doc = MagicMock()
        mock_doc.body = mock_body
        mock_doc_cls.return_value = mock_doc

        svc = ConversionService()
        svc.create_temp_dir()
        result = svc._convert_odt(odt_file)

        content = result.read_text(encoding="utf-8")
        assert "First paragraph" in content
        assert "Second paragraph" in content
        assert "\n\n" in content  # paragraphs separated by double newline
        svc.cleanup()

    @patch("odfdo.Document")
    def test_empty_paragraphs_filtered(self, mock_doc_cls, tmp_path):
        odt_file = tmp_path / "sparse.odt"
        odt_file.write_bytes(b"PK fake odt")

        mock_para1 = MagicMock()
        mock_para1.get_formatted_text.return_value = "Content"
        mock_para_empty = MagicMock()
        mock_para_empty.get_formatted_text.return_value = ""
        mock_body = MagicMock()
        mock_body.get_paragraphs.return_value = [mock_para1, mock_para_empty]
        mock_doc = MagicMock()
        mock_doc.body = mock_body
        mock_doc_cls.return_value = mock_doc

        svc = ConversionService()
        svc.create_temp_dir()
        result = svc._convert_odt(odt_file)

        content = result.read_text(encoding="utf-8")
        assert content == "Content"
        svc.cleanup()


class TestUTF8Handling:
    """Test that German umlauts and special characters are preserved."""

    @patch("markitdown.MarkItDown")
    def test_umlauts_in_markitdown_conversion(self, mock_cls, tmp_path):
        html_file = tmp_path / "umlaute.html"
        html_file.write_text("<p>Ärger über Ölförderung in Übersee</p>", encoding="utf-8")

        mock_result = MagicMock()
        mock_result.text_content = "Ärger über Ölförderung in Übersee"
        mock_cls.return_value.convert.return_value = mock_result

        svc = ConversionService()
        svc.create_temp_dir()
        result = svc._convert_with_markitdown(html_file)

        content = result.read_text(encoding="utf-8")
        assert "Ärger" in content
        assert "Ölförderung" in content
        assert "Übersee" in content
        svc.cleanup()

    @patch("odfdo.Document")
    def test_umlauts_in_odt_conversion(self, mock_doc_cls, tmp_path):
        odt_file = tmp_path / "deutsch.odt"
        odt_file.write_bytes(b"PK fake odt")

        mock_para = MagicMock()
        mock_para.get_formatted_text.return_value = "Größe der Straße in München"
        mock_body = MagicMock()
        mock_body.get_paragraphs.return_value = [mock_para]
        mock_doc = MagicMock()
        mock_doc.body = mock_body
        mock_doc_cls.return_value = mock_doc

        svc = ConversionService()
        svc.create_temp_dir()
        result = svc._convert_odt(odt_file)

        content = result.read_text(encoding="utf-8")
        assert "Größe" in content
        assert "Straße" in content
        assert "München" in content
        svc.cleanup()


class TestConversionServiceUniversal:
    """Tests for new format support via UniversalConverter."""

    def test_csv_file_detected_as_needing_conversion(self):
        service = ConversionService()
        assert service.needs_conversion(Path("test.csv"))

    def test_json_file_detected_as_needing_conversion(self):
        service = ConversionService()
        assert service.needs_conversion(Path("test.json"))

    def test_xlsx_file_detected_as_needing_conversion(self):
        service = ConversionService()
        assert service.needs_conversion(Path("test.xlsx"))

    def test_csv_convert_returns_markdown_path(self, tmp_path):
        csv_file = tmp_path / "test.csv"
        csv_file.write_text("Name,Wert\nA,1\n", encoding="utf-8")
        service = ConversionService()
        result = service.convert_file(csv_file)
        assert result.suffix == ".md"
        assert result.exists()
        content = result.read_text(encoding="utf-8")
        assert "---" in content  # Frontmatter
        service.cleanup()

    def test_yaml_convert_roundtrip(self, tmp_path):
        yaml_file = tmp_path / "test.yaml"
        yaml_file.write_text("name: Testprodukt\npreis: 9.99\n", encoding="utf-8")
        service = ConversionService()
        result = service.convert_file(yaml_file)
        content = result.read_text(encoding="utf-8")
        assert "Testprodukt" in content
        service.cleanup()
