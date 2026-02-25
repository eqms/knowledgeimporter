"""Tests for BaseConverter ABC and data models."""

import pytest

from knowledgeimporter.converters.base import BaseConverter, RawDocument, Section, ValidationResult


def test_raw_document_creation():
    doc = RawDocument(
        source_path="/tmp/test.csv",
        source_type="csv",
        title="Test",
        language="de",
        date=None,
        sections=[],
        metadata={},
        raw_text="a,b\n1,2",
    )
    assert doc.source_type == "csv"
    assert doc.raw_text == "a,b\n1,2"


def test_section_creation():
    s = Section(level=2, title="Zeile 1", kv_pairs=[("Feld A", "Wert 1")], free_text=None)
    assert s.level == 2
    assert s.kv_pairs[0] == ("Feld A", "Wert 1")


def test_base_converter_is_abstract():
    with pytest.raises(TypeError):
        BaseConverter()  # ABC, kann nicht direkt instanziiert werden


def test_conversion_result_structure():
    vr = ValidationResult(status="ok", coverage_score=1.0, issues=[], ai_used=False, corrected_markdown=None)
    assert vr.status == "ok"
    assert vr.coverage_score == 1.0
