"""Universal document converter — dispatches to format-specific converters."""

from __future__ import annotations

from pathlib import Path

from .base import BaseConverter, ConversionResult
from .csv_converter import CsvConverter
from .json_converter import JsonConverter
from .xml_converter import XmlConverter
from .xlsx_converter import XlsxConverter
from .yaml_converter import YamlConverter


class UnsupportedFormatError(Exception):
    """Raised when no converter is registered for the file extension."""

    def __init__(self, ext: str) -> None:
        super().__init__(f"Format nicht unterstützt: {ext}")
        self.ext = ext


class UniversalConverter:
    """Orchestrator: selects the appropriate converter based on file extension."""

    _REGISTRY: dict[str, type[BaseConverter]] = {
        ".csv": CsvConverter,
        ".json": JsonConverter,
        ".yaml": YamlConverter,
        ".yml": YamlConverter,
        ".xml": XmlConverter,
        ".xlsx": XlsxConverter,
    }

    def supported_extensions(self) -> list[str]:
        """Return list of supported file extensions."""
        return list(self._REGISTRY.keys())

    def convert(self, path: str) -> ConversionResult:
        """Convert a file to Markdown, dispatching to the registered converter."""
        ext = Path(path).suffix.lower()
        converter_cls = self._REGISTRY.get(ext)
        if converter_cls is None:
            raise UnsupportedFormatError(ext)
        return converter_cls().run(path)
