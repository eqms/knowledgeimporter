# Implementierungs-Checkliste: Universeller Dokument-Konverter

> Fortschritts-Tracking für Integration des technischen Konzepts v1.0

---

## Phase A: Vorbereitung

- [x] **Task 1** – Abhängigkeiten in `pyproject.toml` eintragen (`pandas`, `openpyxl`, `pyyaml`, `lxml`, `chardet`)
- [x] **Task 2** – `converters/base.py`: Datenmodelle (`RawDocument`, `Section`, `ValidationResult`, `ConversionResult`) + `BaseConverter` ABC + `build_frontmatter()` + `sections_to_markdown()`

---

## Phase B: Konverter implementieren (TDD)

- [ ] **Task 3** – `CsvConverter`: CSV mit Encoding-Erkennung (chardet) → Key-Value-Sektionen pro Zeile
- [ ] **Task 4** – `JsonConverter`: JSON-Flattening mit Dot-Notation, Arrays → mehrere Sektionen
- [ ] **Task 5** – `YamlConverter`: YAML-Mapping → Sektionen, Anchors/Aliases aufgelöst
- [ ] **Task 6** – `XmlConverter`: XML mit Namespace-Strip, Attribute als Zusatzfelder
- [ ] **Task 7** – `XlsxConverter`: Pro-Zeile-Sektionen, Multi-Sheet-Unterstützung

---

## Phase C: Orchestrierung & Integration

- [ ] **Task 8** – `UniversalConverter`: Format-Registry (`.csv`, `.json`, `.yaml`, `.yml`, `.xml`, `.xlsx`) + `UnsupportedFormatError`
- [ ] **Task 9** – `ConversionService` erweitern: `CONVERTIBLE_EXTENSIONS` + `UniversalConverter`-Delegation in `convert_file()`
- [ ] **Task 10** – `AppConfig`: `file_patterns` Default um neue Formate erweitern

---

## Phase D: Qualitätssicherung

- [ ] **Task 11** – Alle Tests grün (`pytest tests/ -v`)
- [ ] **Task 11** – Ruff-Lint und Format sauber (`ruff check src/ tests/`)
- [ ] **Task 11** – Finaler Commit `v0.4.0`

---

## Phase E: Manuelle Verifikation

- [ ] App starten, neue Formate in Settings sichtbar
- [ ] CSV-Datei hochladen → YAML-Frontmatter im Ergebnis
- [ ] JSON-Datei hochladen → Dot-Notation Flattening korrekt
- [ ] XLSX-Datei hochladen → Pro-Zeile-Sektionen in Markdown

---

## Ausgelassener Scope (YAGNI – späteres Release)

- [ ] ~~KI-Validierungsstufe (Coverage < 95% → LangDock-API)~~ → v0.5.0
- [ ] ~~PDF-OCR (Tesseract-Integration)~~ → v0.5.0
- [ ] ~~python-docx für bessere DOCX-Heading-Erkennung~~ → Bewertung ausstehend
