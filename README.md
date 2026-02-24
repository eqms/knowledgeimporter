# KnowledgeImporter

Desktop app for batch-uploading Markdown files to LangDock Knowledge Folders.

## Quick Start

```bash
uv venv && source .venv/bin/activate
uv pip install -e ".[dev]"
flet run src/knowledgeimporter/main.py
```

## Development

```bash
pytest tests/ -v
ruff check src/ && ruff format src/ --check
```
