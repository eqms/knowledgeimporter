"""JSON to chunking-safe Markdown converter."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .base import BaseConverter, RawDocument, Section


def _flatten(data: Any, prefix: str = "") -> list[tuple[str, str]]:
    """Recursively flatten JSON data with dot-notation keys."""
    items: list[tuple[str, str]] = []
    if isinstance(data, dict):
        for k, v in data.items():
            key = f"{prefix}.{k}" if prefix else k
            items.extend(_flatten(v, key))
    elif isinstance(data, list):
        for i, v in enumerate(data):
            items.extend(_flatten(v, f"{prefix}[{i}]" if prefix else f"[{i}]"))
    else:
        value = "" if data is None else str(data)
        items.append((prefix, value))
    return items


class JsonConverter(BaseConverter):
    """Converts JSON files into chunking-safe Markdown."""

    def extract(self, path: str) -> RawDocument:
        text = Path(path).read_text(encoding="utf-8")
        try:
            data = json.loads(text)
        except json.JSONDecodeError as e:
            raise ValueError(f"JSON-Fehler: {e}") from e

        sections: list[Section] = []
        if isinstance(data, list):
            for idx, item in enumerate(data, start=1):
                kv = _flatten(item)
                first_val = kv[0][1] if kv else str(idx)
                sections.append(Section(level=2, title=f"Eintrag {idx}: {first_val}", kv_pairs=kv))
        else:
            kv = _flatten(data)
            sections.append(Section(level=2, title="Inhalt", kv_pairs=kv))

        return RawDocument(
            source_path=path,
            source_type="json",
            title=Path(path).stem,
            language="de",
            date=None,
            sections=sections,
            metadata={},
            raw_text=text,
        )
