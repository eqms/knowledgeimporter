"""Tests for UniversalConverter — format registry and orchestration."""

import tempfile

import pytest

from knowledgeimporter.converters.universal_converter import UniversalConverter, UnsupportedFormatError


def write_file(content: str, suffix: str) -> str:
    f = tempfile.NamedTemporaryFile(mode="w", suffix=suffix, delete=False, encoding="utf-8")
    f.write(content)
    f.flush()
    return f.name


def test_json_file_dispatched_correctly():
    path = write_file('{"name": "Test"}', ".json")
    result = UniversalConverter().convert(path)
    assert "Test" in result.markdown_content


def test_yaml_file_dispatched():
    path = write_file("name: Test\nwert: 42\n", ".yaml")
    result = UniversalConverter().convert(path)
    assert result.markdown_content.startswith("---")


def test_csv_file_dispatched():
    path = write_file("A,B\n1,2\n", ".csv")
    result = UniversalConverter().convert(path)
    assert "A" in result.markdown_content or "1" in result.markdown_content


def test_unsupported_format_raises():
    path = write_file("dummy", ".xyz")
    with pytest.raises(UnsupportedFormatError, match=".xyz"):
        UniversalConverter().convert(path)


def test_yml_alias_works():
    path = write_file("key: value\n", ".yml")
    result = UniversalConverter().convert(path)
    assert result.markdown_content.startswith("---")


def test_supported_extensions():
    ext = UniversalConverter().supported_extensions()
    assert ".csv" in ext
    assert ".json" in ext
    assert ".yaml" in ext
    assert ".xml" in ext
    assert ".xlsx" in ext
