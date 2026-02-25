"""Tests for YamlConverter — YAML to chunking-safe Markdown."""

import tempfile

import pytest

from knowledgeimporter.converters.yaml_converter import YamlConverter


def write_yaml(content: str) -> str:
    f = tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False, encoding="utf-8")
    f.write(content)
    f.flush()
    return f.name


YAML_SIMPLE = """
name: Artikel A
preis: 4.50
aktiv: true
"""

YAML_NESTED = """
produkt:
  name: CMC 70115
  temp: 180
tags:
  - hochtemperatur
  - silikon
"""


def test_flat_yaml_extracts_kv():
    path = write_yaml(YAML_SIMPLE)
    doc = YamlConverter().extract(path)
    assert len(doc.sections) > 0
    keys = [k for k, _ in doc.sections[0].kv_pairs]
    assert "name" in keys or "preis" in keys


def test_nested_yaml_creates_subsections():
    path = write_yaml(YAML_NESTED)
    doc = YamlConverter().extract(path)
    assert len(doc.sections) >= 1


def test_yaml_markdown_has_frontmatter():
    path = write_yaml(YAML_SIMPLE)
    result = YamlConverter().run(path)
    assert "---" in result.markdown_content
    assert "quelle: yaml" in result.markdown_content


def test_invalid_yaml_raises():
    path = write_yaml("key: [unclosed")
    with pytest.raises(ValueError, match="YAML"):
        YamlConverter().extract(path)
