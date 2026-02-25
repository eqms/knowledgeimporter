"""YAML to chunking-safe Markdown converter."""

from __future__ import annotations

from pathlib import Path

import yaml

from .base import BaseConverter, RawDocument, Section
from .json_converter import _flatten


class YamlConverter(BaseConverter):
    """Converts YAML files into chunking-safe Markdown."""

    def extract(self, path: str) -> RawDocument:
        text = Path(path).read_text(encoding="utf-8")
        try:
            data = yaml.safe_load(text)
        except yaml.YAMLError as e:
            raise ValueError(f"YAML-Fehler: {e}") from e

        sections: list[Section] = []
        if isinstance(data, list):
            for idx, item in enumerate(data, start=1):
                kv = _flatten(item)
                first_val = kv[0][1] if kv else str(idx)
                sections.append(Section(level=2, title=f"Eintrag {idx}: {first_val}", kv_pairs=kv))
        elif isinstance(data, dict):
            # Top-level keys with dict values become separate sections
            top_kv: list[tuple[str, str]] = []
            for k, v in data.items():
                if isinstance(v, dict):
                    kv = _flatten(v, prefix=str(k))
                    sections.append(Section(level=2, title=str(k), kv_pairs=kv))
                else:
                    top_kv.extend(_flatten(v, prefix=str(k)))
            if top_kv:
                sections.insert(0, Section(level=2, title="Grunddaten", kv_pairs=top_kv))
        else:
            sections.append(Section(level=2, title="Inhalt", kv_pairs=[("Wert", str(data))]))

        return RawDocument(
            source_path=path,
            source_type="yaml",
            title=Path(path).stem,
            language="de",
            date=None,
            sections=sections,
            metadata={},
            raw_text=text,
        )
