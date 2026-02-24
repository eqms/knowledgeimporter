"""Entry point for the KnowledgeImporter Flet application."""

import flet as ft

from knowledgeimporter.app import KnowledgeImporterApp


async def main(page: ft.Page) -> None:
    """Initialize and run the application."""
    app = KnowledgeImporterApp(page)
    await app.initialize()


def run() -> None:
    """CLI entry point for the knowledgeimporter command."""
    ft.run(main)


if __name__ == "__main__":
    run()
