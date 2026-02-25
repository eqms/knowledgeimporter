# KnowledgeImporter

> **Language / Sprache**: [DE](#deutsche-dokumentation) | [EN](#english-documentation)

[![Version](https://img.shields.io/badge/version-0.3.1-blue.svg)]()
[![Python](https://img.shields.io/badge/python-3.10+-green.svg)]()
[![License](https://img.shields.io/badge/license-MIT-green.svg)]()

---

## Deutsche Dokumentation

### Projektübersicht

KnowledgeImporter ist eine Desktop-Applikation zum Batch-Upload von Dokumenten in LangDock Knowledge Folders. Die App konvertiert PDF, DOCX, HTML und ODT automatisch zu Markdown und lädt sie anschließend hoch.

Gebaut mit [Flet](https://flet.dev/) (Flutter für Python), bietet sie eine native Desktop-Oberfläche mit Fortschrittsanzeige, dateibasiertem Logging und verschlüsselter API-Key-Speicherung.

**Hauptfunktionen:**
- **Batch-Upload** — Ordner auswählen und alle passenden Dateien in einen LangDock Knowledge Folder hochladen
- **Dokument-Konvertierung** — PDF, DOCX, HTML und ODT werden automatisch zu Markdown konvertiert
- **Replace-Modus** — optional bestehende Dateien im Zielordner vor dem erneuten Upload löschen
- **Fortschrittsanzeige** — Echtzeit-Fortschrittsbalken mit Status pro Datei (Converting, Uploading, Success, Error)
- **Dateibasiertes Logging** — jede Upload-Session erzeugt ein Logfile mit `[CONV]`, `[UPLOAD]`, `[OK]`, `[FAIL]` Einträgen
- **Verschlüsselte Konfiguration** — API-Keys werden mit Fernet verschlüsselt gespeichert, Master Key im OS-Keyring
- **Versionsanzeige** — aktuelle Version im Fenster-Titel der Applikation

### Unterstützte Dateiformate

| Format | Endung | Konvertierungs-Bibliothek |
|--------|--------|--------------------------|
| Markdown | `.md` | Nativ (keine Konvertierung) |
| PDF | `.pdf` | [markitdown](https://github.com/microsoft/markitdown) via pdfminer.six |
| Word | `.docx` | [markitdown](https://github.com/microsoft/markitdown) via mammoth |
| HTML | `.html`, `.htm` | [markitdown](https://github.com/microsoft/markitdown) via BeautifulSoup4 |
| OpenDocument | `.odt` | [odfdo](https://github.com/jdum/odfdo) via Paragraph-Extraktion |

### Konvertierungs-Architektur

Nicht-Markdown-Dateien werden transparent innerhalb der `upload_batch()`-Methode des `UploadService` konvertiert:

1. **Erkennung** — `ConversionService.needs_conversion(path)` prüft die Dateiendung gegen die Menge konvertierbarer Formate
2. **Konvertierung** — `ConversionService.convert_file(path)` leitet an den passenden Konverter weiter:
   - PDF/DOCX/HTML → `MarkItDown().convert()` (Microsofts markitdown-Bibliothek, optimiert für LLM Knowledge Bases)
   - ODT → `odfdo.Document` Paragraph-Extraktion mit `get_formatted_text()`
3. **Temp-Verzeichnis** — konvertierte `.md`-Dateien werden in ein `tempfile.mkdtemp()`-Verzeichnis geschrieben
4. **Upload** — die konvertierte Datei wird mit dem ursprünglichen Dateinamen + `.md`-Endung hochgeladen (z.B. `report.pdf` → `report.md`)
5. **Cleanup** — das Temp-Verzeichnis wird im `finally`-Block entfernt, was Aufräumen bei Erfolg und Fehler garantiert

Die Konvertierung läuft im bestehenden `BackgroundWorker` Daemon-Thread. Progress-Callbacks nutzen den `"converting"`-Status, um blauen Status-Text in der UI anzuzeigen, bevor die `"uploading"`-Phase beginnt.

#### Fehlerbehandlung

- Schlägt die Konvertierung einer Datei fehl, wird sie übersprungen und als `failed` gezählt — der Batch fährt mit der nächsten Datei fort
- `ConversionError(filename, reason)` liefert strukturiertes Error-Reporting
- Bibliotheken werden lazy innerhalb der Konvertierungsmethoden importiert — fehlt markitdown oder odfdo, wird eine klare Fehlermeldung statt eines Import-Crashs erzeugt

### Voraussetzungen

- Python >= 3.10
- [UV](https://docs.astral.sh/uv/) Package Manager

### Installation

```bash
# Repository klonen
git clone https://github.com/equitania/knowledgeimporter.git

# In Projektverzeichnis wechseln
cd knowledgeimporter

# Virtuelle Umgebung erstellen und aktivieren
uv venv && source .venv/bin/activate

# Abhängigkeiten installieren
uv pip install -e ".[dev]"
```

### Verwendung

```bash
# Applikation starten (Produktions-Einstiegspunkt)
knowledgeimporter

# Entwicklung mit Hot-Reload
flet run src/knowledgeimporter/main.py
```

#### Konfiguration

Die Konfiguration erfolgt über die Settings-Ansicht in der App und wird in `~/.knowledgeimporter/config.json` gespeichert:

| Parameter | Typ | Standard | Beschreibung |
|-----------|-----|----------|--------------|
| `langdock_api_key` | string | `""` | LangDock API-Key (verschlüsselt gespeichert) |
| `region` | string | `"eu"` | API-Region (`eu` oder `us`) |
| `default_folder_id` | string | `""` | UUID des Ziel-Knowledge-Folders |
| `folder_name` | string | `""` | Anzeigename des Ordners |
| `file_patterns` | list | `["*.md", "*.pdf", "*.docx", "*.html", "*.htm", "*.odt"]` | Datei-Muster für den Upload |
| `replace_existing` | bool | `true` | Bestehende Dateien vor dem Upload löschen |

### Architektur

```
src/knowledgeimporter/
├── __init__.py              # Version (__version__)
├── main.py                  # Einstiegspunkt: ft.app(target=main)
├── app.py                   # KnowledgeImporterApp — Navigation, Config-Lifecycle
├── models/
│   └── config.py            # AppConfig (Pydantic) — file_patterns, API Key, Folder ID
├── services/
│   ├── converter.py         # ConversionService — PDF/DOCX/HTML/ODT → Markdown
│   └── upload_service.py    # UploadService — Batch-Upload mit Konvertierungs-Integration
├── utils/
│   ├── storage.py           # Config-Persistenz, Fernet-Verschlüsselung, Keyring
│   ├── upload_logger.py     # Dateibasiertes Upload-Logging mit Auto-Cleanup
│   └── worker.py            # BackgroundWorker — Daemon-Thread mit Cancellation
└── views/
    ├── upload_view.py       # Upload-Ansicht — Ordner-Auswahl, Fortschritt, Log-Viewer
    └── settings_view.py     # Einstellungen — API Key, Ordner, Muster
```

### Entwicklung

```bash
# Tests ausführen
pytest tests/ -v

# Lint- und Format-Prüfung
ruff check src/ tests/ && ruff format src/ tests/ --check

# Auto-Fix für Lint und Format
ruff check src/ tests/ --fix && ruff format src/ tests/

# Distribution erstellen
uv build
```

#### Code-Stil

- **Formatter:** Ruff (Zeilenlänge 120)
- **Linting:** Ruff mit Regeln E, W, F, I, B, C4, UP
- **Target:** Python 3.10
- **Commits:** `[ADD]`, `[CHG]`, `[FIX]` Prefix-Konvention

### Abhängigkeiten

| Paket | Zweck |
|-------|-------|
| `flet>=0.80.5` | Desktop-UI-Framework (Flutter-basiert) |
| `eq-chatbot-core>=1.2.1` | LangDock API-Client (`LangDockKnowledgeManager`) |
| `keyring>=25.0.0` | OS-Keyring für Fernet Master Key |
| `pydantic>=2.10.0` | Config-Model-Validierung und Serialisierung |
| `markitdown[pdf,docx]>=0.1.5` | PDF/DOCX/HTML → Markdown Konvertierung |
| `odfdo>=3.20` | ODT → Markdown Konvertierung |

### Changelog

#### [0.3.1] - 25.02.2026
- Version im Fenster-Titel der Applikation sichtbar
- Zweisprachige README-Dokumentation (DE/EN)

#### [0.3.0] - 25.02.2026
- Dokument-Konvertierung: PDF, DOCX, HTML, ODT → Markdown
- `ConversionService` mit markitdown und odfdo Integration
- `"converting"` Status in UI und Logging (`[CONV]`)
- Erweiterte Standard-Dateimuster: `*.md, *.pdf, *.docx, *.html, *.htm, *.odt`
- `converted` Counter in Upload-Ergebnis und Log-Summary

#### [0.2.1] - 2025
- Log-UI durch dateibasiertes Logging ersetzt
- App-Icon Dead Code entfernt
- Threading-Fix, Spinner, Icon & Version Bump

### Lizenz

MIT — Equitania Software GmbH

### Kontakt

- **Unternehmen:** Equitania Software GmbH
- **Website:** https://www.ownerp.com
- **Repository:** https://github.com/equitania/knowledgeimporter

---

## English Documentation

### Project Overview

KnowledgeImporter is a desktop application for batch-uploading documents to LangDock Knowledge Folders. The app automatically converts PDF, DOCX, HTML, and ODT files to Markdown before uploading.

Built with [Flet](https://flet.dev/) (Flutter for Python), it provides a native desktop UI with progress tracking, file-based logging, and encrypted API key storage.

**Key Features:**
- **Batch upload** — select a folder and upload all matching files to a LangDock Knowledge Folder
- **Document conversion** — PDF, DOCX, HTML, and ODT files are automatically converted to Markdown
- **Replace mode** — optionally delete existing files in the target folder before re-uploading
- **Progress tracking** — real-time progress bar with per-file status (converting, uploading, success, error)
- **File-based logging** — each upload session writes a timestamped log with `[CONV]`, `[UPLOAD]`, `[OK]`, `[FAIL]` entries
- **Encrypted config** — API keys are Fernet-encrypted at rest, master key stored in OS keyring
- **Version display** — current version shown in the application window title

### Supported File Formats

| Format | Extension | Conversion Library |
|--------|-----------|-------------------|
| Markdown | `.md` | Native (no conversion) |
| PDF | `.pdf` | [markitdown](https://github.com/microsoft/markitdown) via pdfminer.six |
| Word | `.docx` | [markitdown](https://github.com/microsoft/markitdown) via mammoth |
| HTML | `.html`, `.htm` | [markitdown](https://github.com/microsoft/markitdown) via BeautifulSoup4 |
| OpenDocument | `.odt` | [odfdo](https://github.com/jdum/odfdo) via paragraph extraction |

### Conversion Architecture

Non-Markdown files are transparently converted inside the `upload_batch()` method of `UploadService`:

1. **Detection** — `ConversionService.needs_conversion(path)` checks the file extension against the set of convertible formats
2. **Conversion** — `ConversionService.convert_file(path)` routes to the appropriate converter:
   - PDF/DOCX/HTML → `MarkItDown().convert()` (Microsoft's markitdown library, optimized for LLM knowledge bases)
   - ODT → `odfdo.Document` paragraph extraction with `get_formatted_text()`
3. **Temp directory** — converted `.md` files are written to a `tempfile.mkdtemp()` directory
4. **Upload** — the converted file is uploaded with the original stem + `.md` extension (e.g., `report.pdf` → `report.md`)
5. **Cleanup** — the temp directory is removed in a `finally` block, guaranteeing cleanup on success and error

The conversion runs in the existing `BackgroundWorker` daemon thread. Progress callbacks use the `"converting"` status to show blue status text in the UI before the `"uploading"` phase begins.

#### Error Handling

- If a file fails conversion, it is skipped and counted as `failed` — the batch continues with the next file
- `ConversionError(filename, reason)` provides structured error reporting
- Libraries are lazily imported inside conversion methods — if markitdown or odfdo is missing, a clear error message is raised instead of an import crash

### Prerequisites

- Python >= 3.10
- [UV](https://docs.astral.sh/uv/) package manager

### Installation

```bash
# Clone repository
git clone https://github.com/equitania/knowledgeimporter.git

# Navigate to project directory
cd knowledgeimporter

# Create and activate virtual environment
uv venv && source .venv/bin/activate

# Install dependencies
uv pip install -e ".[dev]"
```

### Usage

```bash
# Start application (production entry point)
knowledgeimporter

# Development with hot-reload
flet run src/knowledgeimporter/main.py
```

#### Configuration

Configuration is managed through the Settings view in the app and persisted in `~/.knowledgeimporter/config.json`:

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `langdock_api_key` | string | `""` | LangDock API key (stored encrypted) |
| `region` | string | `"eu"` | API region (`eu` or `us`) |
| `default_folder_id` | string | `""` | UUID of target Knowledge Folder |
| `folder_name` | string | `""` | Display name of the folder |
| `file_patterns` | list | `["*.md", "*.pdf", "*.docx", "*.html", "*.htm", "*.odt"]` | File patterns for upload |
| `replace_existing` | bool | `true` | Delete existing files before upload |

### Architecture

```
src/knowledgeimporter/
├── __init__.py              # Version (__version__)
├── main.py                  # Entry point: ft.app(target=main)
├── app.py                   # KnowledgeImporterApp — navigation, config lifecycle
├── models/
│   └── config.py            # AppConfig (Pydantic) — file_patterns, API key, folder ID
├── services/
│   ├── converter.py         # ConversionService — PDF/DOCX/HTML/ODT → Markdown
│   └── upload_service.py    # UploadService — batch upload with conversion integration
├── utils/
│   ├── storage.py           # Config persistence, Fernet encryption, keyring
│   ├── upload_logger.py     # File-based upload logging with auto-cleanup
│   └── worker.py            # BackgroundWorker — daemon thread with cancellation
└── views/
    ├── upload_view.py       # Upload screen — folder picker, progress, log viewer
    └── settings_view.py     # Settings screen — API key, folder, patterns
```

### Development

```bash
# Run tests
pytest tests/ -v

# Lint and format check
ruff check src/ tests/ && ruff format src/ tests/ --check

# Auto-fix lint and format
ruff check src/ tests/ --fix && ruff format src/ tests/

# Build distribution
uv build
```

#### Code Style

- **Formatter:** Ruff (line length 120)
- **Linting:** Ruff with rules E, W, F, I, B, C4, UP
- **Target:** Python 3.10
- **Commits:** `[ADD]`, `[CHG]`, `[FIX]` prefix convention

### Dependencies

| Package | Purpose |
|---------|---------|
| `flet>=0.80.5` | Desktop UI framework (Flutter-based) |
| `eq-chatbot-core>=1.2.1` | LangDock API client (`LangDockKnowledgeManager`) |
| `keyring>=25.0.0` | OS keyring for Fernet master key |
| `pydantic>=2.10.0` | Config model validation and serialization |
| `markitdown[pdf,docx]>=0.1.5` | PDF/DOCX/HTML → Markdown conversion |
| `odfdo>=3.20` | ODT → Markdown conversion |

### Changelog

#### [0.3.1] - 2026-02-25
- Version displayed in application window title
- Bilingual README documentation (DE/EN)

#### [0.3.0] - 2026-02-25
- Document conversion: PDF, DOCX, HTML, ODT → Markdown
- `ConversionService` with markitdown and odfdo integration
- `"converting"` status in UI and logging (`[CONV]`)
- Extended default file patterns: `*.md, *.pdf, *.docx, *.html, *.htm, *.odt`
- `converted` counter in upload result and log summary

#### [0.2.1] - 2025
- Replaced log UI with file-based logging
- Removed app icon dead code
- Threading fix, spinner, icon & version bump

### License

MIT — Equitania Software GmbH

### Contact

- **Company:** Equitania Software GmbH
- **Website:** https://www.ownerp.com
- **Repository:** https://github.com/equitania/knowledgeimporter
