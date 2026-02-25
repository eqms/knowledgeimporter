"""Document conversion service — converts PDF, DOCX, HTML, ODT to Markdown."""

import logging
import shutil
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)

# Extensions that require conversion before upload
CONVERTIBLE_EXTENSIONS = {".pdf", ".docx", ".html", ".htm", ".odt"}

# Extensions supported without conversion
NATIVE_EXTENSIONS = {".md"}


class ConversionError(Exception):
    """Raised when a file conversion fails."""

    def __init__(self, filename: str, reason: str) -> None:
        self.filename = filename
        self.reason = reason
        super().__init__(f"Failed to convert {filename}: {reason}")


class ConversionService:
    """Converts non-Markdown documents to Markdown for upload."""

    def __init__(self) -> None:
        self._temp_dir: Path | None = None

    @staticmethod
    def needs_conversion(path: Path) -> bool:
        """Check if a file needs conversion (non-Markdown but convertible)."""
        return path.suffix.lower() in CONVERTIBLE_EXTENSIONS

    @staticmethod
    def is_supported(path: Path) -> bool:
        """Check if a file is natively supported or convertible."""
        return path.suffix.lower() in (NATIVE_EXTENSIONS | CONVERTIBLE_EXTENSIONS)

    def create_temp_dir(self) -> Path:
        """Create a temporary directory for converted files."""
        self._temp_dir = Path(tempfile.mkdtemp(prefix="knowledgeimporter_"))
        logger.debug("Created temp dir: %s", self._temp_dir)
        return self._temp_dir

    def cleanup(self) -> None:
        """Remove the temporary directory and all its contents."""
        if self._temp_dir and self._temp_dir.exists():
            try:
                shutil.rmtree(self._temp_dir)
                logger.debug("Cleaned up temp dir: %s", self._temp_dir)
            except OSError as e:
                logger.warning("Failed to cleanup temp dir %s: %s", self._temp_dir, e)
        self._temp_dir = None

    def convert_file(self, path: Path) -> Path:
        """
        Convert a file to Markdown if needed.

        Returns the original path for .md files, or a new path to the
        converted .md file in the temp directory for other formats.
        """
        if path.suffix.lower() in NATIVE_EXTENSIONS:
            return path

        if not self._temp_dir:
            self.create_temp_dir()

        ext = path.suffix.lower()
        if ext == ".odt":
            return self._convert_odt(path)
        if ext in {".pdf", ".docx", ".html", ".htm"}:
            return self._convert_with_markitdown(path)

        raise ConversionError(path.name, f"Unsupported format: {ext}")

    def _convert_with_markitdown(self, path: Path) -> Path:
        """Convert PDF, DOCX, or HTML to Markdown using markitdown."""
        try:
            from markitdown import MarkItDown
        except ImportError as e:
            raise ConversionError(path.name, "markitdown library not installed") from e

        try:
            md = MarkItDown()
            result = md.convert(str(path))
            content = result.text_content

            assert self._temp_dir is not None  # guaranteed by convert_file()
            out_path = self._temp_dir / (path.stem + ".md")
            out_path.write_text(content, encoding="utf-8")
            logger.debug("Converted %s -> %s via markitdown", path.name, out_path.name)
            return out_path
        except Exception as e:
            raise ConversionError(path.name, str(e)) from e

    def _convert_odt(self, path: Path) -> Path:
        """Convert ODT to Markdown via odfdo paragraph extraction."""
        try:
            from odfdo import Document
        except ImportError as e:
            raise ConversionError(path.name, "odfdo library not installed") from e

        try:
            doc = Document(str(path))
            body = doc.body
            paragraphs = []
            for para in body.get_paragraphs():
                text = para.get_formatted_text() if hasattr(para, "get_formatted_text") else str(para)
                if text:
                    paragraphs.append(text)

            content = "\n\n".join(paragraphs)
            assert self._temp_dir is not None  # guaranteed by convert_file()
            out_path = self._temp_dir / (path.stem + ".md")
            out_path.write_text(content, encoding="utf-8")
            logger.debug("Converted %s -> %s via odfdo", path.name, out_path.name)
            return out_path
        except ConversionError:
            raise
        except Exception as e:
            raise ConversionError(path.name, str(e)) from e
