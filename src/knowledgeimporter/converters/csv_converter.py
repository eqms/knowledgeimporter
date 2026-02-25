"""CSV to chunking-safe Markdown converter."""

from __future__ import annotations

import csv
from pathlib import Path

import chardet

from .base import BaseConverter, RawDocument, Section


class CsvConverter(BaseConverter):
    """Converts CSV files into chunking-safe Markdown."""

    def extract(self, path: str) -> RawDocument:
        raw_bytes = Path(path).read_bytes()
        # Try UTF-8 first (most common), fall back to chardet detection
        try:
            text = raw_bytes.decode("utf-8")
        except UnicodeDecodeError:
            encoding = chardet.detect(raw_bytes)["encoding"] or "latin-1"
            text = raw_bytes.decode(encoding, errors="replace")

        lines = list(csv.DictReader(text.splitlines()))
        if not lines:
            raise ValueError("Keine Datensätze im CSV gefunden")

        headers = list(lines[0].keys())
        sections: list[Section] = []
        for idx, row in enumerate(lines, start=2):
            first_val = row.get(headers[0], "") if headers else ""
            title = f"Zeile {idx}: {first_val}" if first_val else f"Zeile {idx}"
            kv = [(k, str(v)) for k, v in row.items() if v is not None and str(v).strip()]
            sections.append(Section(level=2, title=title, kv_pairs=kv))

        return RawDocument(
            source_path=path,
            source_type="csv",
            title=Path(path).stem,
            language="de",
            date=None,
            sections=sections,
            metadata={"headers": headers, "row_count": len(lines)},
            raw_text=text,
        )
