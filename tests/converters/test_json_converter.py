"""Tests for JsonConverter — JSON to chunking-safe Markdown."""

import json
import tempfile

import pytest

from knowledgeimporter.converters.json_converter import JsonConverter


def write_json(data, suffix=".json"):
    f = tempfile.NamedTemporaryFile(mode="w", suffix=suffix, delete=False)
    json.dump(data, f, ensure_ascii=False)
    f.flush()
    return f.name


def test_flat_object_extracts_kv():
    path = write_json({"name": "Artikel A", "preis": 4.50, "aktiv": True})
    doc = JsonConverter().extract(path)
    assert ("name", "Artikel A") in doc.sections[0].kv_pairs


def test_nested_object_uses_dot_notation():
    path = write_json({"produkt": {"name": "CMC 70115", "eigenschaften": {"temp": 180}}})
    doc = JsonConverter().extract(path)
    keys = [k for k, _ in doc.sections[0].kv_pairs]
    assert "produkt.name" in keys
    assert "produkt.eigenschaften.temp" in keys


def test_array_of_objects_creates_multiple_sections():
    path = write_json([{"id": 1, "name": "A"}, {"id": 2, "name": "B"}])
    doc = JsonConverter().extract(path)
    assert len(doc.sections) == 2


def test_json_markdown_has_frontmatter():
    path = write_json({"x": 1})
    result = JsonConverter().run(path)
    assert result.markdown_content.startswith("---")
    assert "quelle: json" in result.markdown_content


def test_invalid_json_raises():
    f = tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w")
    f.write("{ungültig")
    f.flush()
    with pytest.raises(ValueError, match="JSON"):
        JsonConverter().extract(f.name)
