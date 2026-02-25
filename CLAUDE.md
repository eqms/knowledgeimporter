# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

KnowledgeImporter is a Flet-based desktop application for batch-uploading Markdown files to LangDock Knowledge Folders. Built with Python 3.10+, it uses eq-chatbot-core for LangDock API integration, Fernet encryption for API key storage, and OS keyring for master key management.

## Commands

```bash
# Setup
uv venv && source .venv/bin/activate.fish && uv pip install -e ".[dev]"

# Run (production entry point)
knowledgeimporter

# Run (development with hot-reload)
flet run src/knowledgeimporter/main.py

# Tests
pytest tests/ -v
pytest tests/test_config.py                    # single file
pytest tests/test_upload_service.py::test_name  # single test

# Lint & Format
ruff check src/ tests/                          # lint check
ruff format src/ tests/ --check                 # format check
ruff check src/ tests/ --fix && ruff format src/ tests/  # auto-fix

# Build
uv build
```

## Architecture

**Entry flow**: `main.py::run()` → `ft.app(main)` → `KnowledgeImporterApp(page).initialize()` → two-view navigation (Upload | Settings)

**Key patterns**:

- **Flet UI**: Desktop app using Flet >=0.80.5 (Flutter-based). `FilePicker` is a service, registered via `page.services.append()`. All UI event handlers support `async/await`.
- **Background threading**: `BackgroundWorker` runs uploads in daemon threads with `threading.Event`-based cancellation. Progress updates go from background thread to UI via direct `page.update()` calls.
- **Config persistence**: `AppConfig` (Pydantic model) serializes to `~/.knowledgeimporter/config.json`. The API key is encrypted with Fernet before saving; the Fernet master key lives in OS keyring (`keyring` library).
- **Upload orchestration**: `UploadService` wraps `eq_chatbot_core.providers.langdock_provider.LangDockKnowledgeManager`. It collects files via glob patterns, uploads them sequentially with progress callbacks `(current, total, filename, status)`, and returns a result dict `{total, success, failed, skipped, errors}`.
- **Replace mode**: When enabled, deletes existing files in the target folder before re-uploading.

**External dependencies to understand**:
- `eq_chatbot_core.providers.langdock_provider.LangDockKnowledgeManager` — LangDock API client for file CRUD
- `eq_chatbot_core.security.encryption.FernetEncryption` — Symmetric encryption wrapper

## Testing

Tests use `unittest.mock.patch` to mock `LangDockKnowledgeManager` and `sys.modules` for external dependencies. Real Fernet encryption roundtrip tests are included. Pytest config: line 120 max, `-v --tb=short`.

## Code Style

Ruff with rules: E, W, F, I, B, C4, UP. Line length 120. Target py310. isort with `known-first-party = ["knowledgeimporter"]`.
