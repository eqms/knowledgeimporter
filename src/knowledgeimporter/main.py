"""Entry point for the KnowledgeImporter Flet application."""

import sys
import types
from pathlib import Path

# flet build compatibility: flet bundles files flat (no knowledgeimporter/ wrapper),
# so "from knowledgeimporter.X import Y" fails. Fix: register a virtual package
# that maps knowledgeimporter.* to the current directory.
_app_dir = Path(__file__).parent
if "knowledgeimporter" not in sys.modules:
    _pkg = types.ModuleType("knowledgeimporter")
    _pkg.__path__ = [str(_app_dir)]
    _pkg.__file__ = str(_app_dir / "__init__.py")
    sys.modules["knowledgeimporter"] = _pkg

import flet as ft  # noqa: E402

from knowledgeimporter.app import KnowledgeImporterApp  # noqa: E402


async def main(page: ft.Page) -> None:
    """Initialize and run the application."""
    app = KnowledgeImporterApp(page)
    await app.initialize()


def run() -> None:
    """CLI entry point for the knowledgeimporter command."""
    ft.app(target=main, assets_dir=str(Path(__file__).parent))


if __name__ == "__main__":
    run()
