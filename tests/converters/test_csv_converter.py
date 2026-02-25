"""Tests for CsvConverter — CSV to chunking-safe Markdown."""

import tempfile

import pytest

from knowledgeimporter.converters.csv_converter import CsvConverter


CSV_SIMPLE = "Name,Preis,Bestand\nArtikel A,4.50,100\nArtikel B,9.90,50\n"


def write_csv(content: str, encoding: str = "utf-8") -> str:
    f = tempfile.NamedTemporaryFile(mode="w", suffix=".csv", encoding=encoding, delete=False)
    f.write(content)
    f.flush()
    return f.name


def test_csv_extracts_headers_as_kv_keys():
    path = write_csv(CSV_SIMPLE)
    conv = CsvConverter()
    doc = conv.extract(path)
    assert len(doc.sections) == 2  # 2 Datenzeilen
    assert ("Name", "Artikel A") in doc.sections[0].kv_pairs


def test_csv_section_titles_include_row_number():
    path = write_csv(CSV_SIMPLE)
    conv = CsvConverter()
    doc = conv.extract(path)
    assert "Zeile 2" in doc.sections[0].title or "1" in doc.sections[0].title


def test_csv_markdown_contains_frontmatter():
    path = write_csv(CSV_SIMPLE)
    result = CsvConverter().run(path)
    assert result.markdown_content.startswith("---")
    assert "quelldatei:" in result.markdown_content


def test_csv_utf8_with_umlauts():
    path = write_csv("Bezeichnung,Wert\nÄpfel-Preis,2.50\n")
    result = CsvConverter().run(path)
    assert "Äpfel" in result.markdown_content


def test_csv_empty_file_raises():
    path = write_csv("")
    with pytest.raises(ValueError, match="Keine Datensätze"):
        CsvConverter().extract(path)
