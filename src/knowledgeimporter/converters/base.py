"""Base classes and data models for document converters."""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml


@dataclass
class Section:
    """A structural section of a document with key-value pairs."""

    level: int
    title: str
    kv_pairs: list[tuple[str, str]]
    free_text: str | None = None


@dataclass
class RawDocument:
    """Structured representation of a source document."""

    source_path: str
    source_type: str
    title: str
    language: str
    date: str | None
    sections: list[Section]
    metadata: dict[str, Any]
    raw_text: str


@dataclass
class ValidationResult:
    """Result of the coverage validation step."""

    status: str  # "ok", "warning", "error"
    coverage_score: float  # 0.0 – 1.0
    issues: list[str]
    ai_used: bool
    corrected_markdown: str | None


@dataclass
class ConversionResult:
    """Final result of a document conversion."""

    source_path: str
    markdown_content: str
    validation: ValidationResult
    duration_seconds: float = 0.0
    ai_calls: int = 0


CONVERTER_VERSION = "1.0.0"


def build_frontmatter(doc: RawDocument) -> str:
    """Build YAML frontmatter according to LangDock schema."""
    meta = {
        "quelle": doc.source_type,
        "titel": doc.title,
        "sprache": doc.language,
        "stand": doc.date or "",
        "konvertiert": datetime.now().isoformat(timespec="seconds"),
        "quelldatei": Path(doc.source_path).name,
    }
    return "---\n" + yaml.dump(meta, allow_unicode=True, sort_keys=False) + "---"


def sections_to_markdown(sections: list[Section]) -> str:
    """Convert sections into chunking-safe Markdown."""
    lines: list[str] = []
    for section in sections:
        heading = "#" * section.level + " " + section.title
        lines.append(heading)
        lines.append("")
        if section.kv_pairs:
            for key, value in section.kv_pairs:
                lines.append(f"- **{key}:** {value}")
            lines.append("")
        if section.free_text:
            lines.append(section.free_text)
            lines.append("")
    return "\n".join(lines)


class BaseConverter(ABC):
    """Abstract base class for all format converters."""

    @abstractmethod
    def extract(self, path: str) -> RawDocument:
        """Extract structured data from the source file."""
        ...

    def generate_markdown(self, doc: RawDocument) -> str:
        """Generate LangDock-optimized Markdown with YAML frontmatter."""
        parts = [build_frontmatter(doc), "", f"# {doc.title}", ""]
        parts.append(sections_to_markdown(doc.sections))
        return "\n".join(parts)

    def validate(self, doc: RawDocument, markdown: str) -> ValidationResult:
        """Python validation: coverage score based on numeric/ID values."""
        original_words = set(doc.raw_text.split())
        key_tokens = {w for w in original_words if len(w) >= 2 and (w.isdigit() or len(w) <= 20)}
        if not key_tokens:
            return ValidationResult(status="ok", coverage_score=1.0, issues=[], ai_used=False, corrected_markdown=None)
        found = sum(1 for t in key_tokens if t in markdown)
        score = found / len(key_tokens)
        status = "ok" if score >= 0.95 else "warning"
        issues = [] if score >= 0.95 else [f"Coverage nur {score:.0%} – manuell prüfen"]
        return ValidationResult(
            status=status, coverage_score=score, issues=issues, ai_used=False, corrected_markdown=None
        )

    def run(self, path: str) -> ConversionResult:
        """Orchestrate extract → generate_markdown → validate."""
        t0 = time.time()
        doc = self.extract(path)
        markdown = self.generate_markdown(doc)
        validation = self.validate(doc, markdown)
        duration = time.time() - t0
        return ConversionResult(
            source_path=path,
            markdown_content=markdown,
            validation=validation,
            duration_seconds=round(duration, 3),
        )
