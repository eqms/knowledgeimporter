"""Tests for XmlConverter — XML to chunking-safe Markdown."""

import tempfile

import pytest

from knowledgeimporter.converters.xml_converter import XmlConverter


def write_xml(content: str) -> str:
    f = tempfile.NamedTemporaryFile(mode="w", suffix=".xml", delete=False, encoding="utf-8")
    f.write(content)
    f.flush()
    return f.name


XML_SIMPLE = """<?xml version="1.0"?>
<produkt id="CMC70115">
  <bezeichnung>Kapton-Klebeband</bezeichnung>
  <temperatur unit="C">180</temperatur>
</produkt>"""

XML_LIST = """<?xml version="1.0"?>
<artikel>
  <item><name>A</name><preis>4.50</preis></item>
  <item><name>B</name><preis>9.90</preis></item>
</artikel>"""


def test_simple_xml_extracts_elements():
    path = write_xml(XML_SIMPLE)
    doc = XmlConverter().extract(path)
    assert len(doc.sections) >= 1
    all_kv = [(k, v) for s in doc.sections for k, v in s.kv_pairs]
    keys = [k for k, _ in all_kv]
    assert "bezeichnung" in keys or "temperatur" in keys


def test_xml_attributes_in_kv():
    path = write_xml(XML_SIMPLE)
    doc = XmlConverter().extract(path)
    all_kv = {k: v for s in doc.sections for k, v in s.kv_pairs}
    assert any("id" in k or "unit" in k for k in all_kv)


def test_xml_namespace_stripped():
    ns_xml = """<ns:root xmlns:ns="http://example.com"><ns:item>Wert</ns:item></ns:root>"""
    path = write_xml(ns_xml)
    doc = XmlConverter().extract(path)
    all_kv = {k: v for s in doc.sections for k, v in s.kv_pairs}
    assert "item" in all_kv  # Namespace-Prefix entfernt


def test_xml_markdown_has_frontmatter():
    path = write_xml(XML_SIMPLE)
    result = XmlConverter().run(path)
    assert result.markdown_content.startswith("---")
    assert "quelle: xml" in result.markdown_content


def test_malformed_xml_raises():
    path = write_xml("<root><unclosed>")
    with pytest.raises(ValueError, match="XML"):
        XmlConverter().extract(path)
