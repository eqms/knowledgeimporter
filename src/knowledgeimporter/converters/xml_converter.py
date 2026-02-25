"""XML to chunking-safe Markdown converter."""

from __future__ import annotations

from pathlib import Path

import lxml.etree as ET

from .base import BaseConverter, RawDocument, Section


def _elem_to_kv(elem: ET._Element, prefix: str = "") -> list[tuple[str, str]]:
    """Recursively convert XML element to key-value pairs with dot-notation."""
    tag = elem.tag.split("}")[-1]  # Strip namespace
    full_key = f"{prefix}.{tag}" if prefix else tag
    results: list[tuple[str, str]] = []

    # Attributes as additional fields
    for attr_name, attr_val in elem.attrib.items():
        results.append((f"{full_key}@{attr_name}", attr_val))

    if len(elem) == 0:
        # Leaf element → direct text value
        text = (elem.text or "").strip()
        if text:
            results.append((full_key, text))
    else:
        # Recurse into children
        for child in elem:
            results.extend(_elem_to_kv(child, prefix=full_key))

    return results


class XmlConverter(BaseConverter):
    """Converts XML files into chunking-safe Markdown."""

    def extract(self, path: str) -> RawDocument:
        text = Path(path).read_text(encoding="utf-8")
        try:
            root = ET.fromstring(text.encode("utf-8"))
        except ET.XMLSyntaxError as e:
            raise ValueError(f"XML-Fehler: {e}") from e

        root_tag = root.tag.split("}")[-1]
        sections: list[Section] = []

        # Check if root has multiple children of the same tag (list pattern)
        child_tags = [c.tag.split("}")[-1] for c in root]
        if len(set(child_tags)) == 1 and len(child_tags) > 1:
            for idx, child in enumerate(root, start=1):
                kv = _elem_to_kv(child)
                first_val = kv[0][1] if kv else str(idx)
                sections.append(Section(level=2, title=f"{child_tags[0]} {idx}: {first_val}", kv_pairs=kv))
        else:
            # Root attributes with root tag, children without root prefix
            kv: list[tuple[str, str]] = []
            for attr_name, attr_val in root.attrib.items():
                kv.append((f"{root_tag}@{attr_name}", attr_val))
            for child in root:
                kv.extend(_elem_to_kv(child))
            sections.append(Section(level=2, title=root_tag, kv_pairs=kv))

        return RawDocument(
            source_path=path,
            source_type="xml",
            title=Path(path).stem,
            language="de",
            date=None,
            sections=sections,
            metadata={"root_tag": root_tag},
            raw_text=text,
        )
