"""Main application class with navigation between views."""

import logging

import flet as ft

from knowledgeimporter.models.config import AppConfig
from knowledgeimporter.utils.storage import load_config, save_config
from knowledgeimporter.views.settings_view import SettingsView
from knowledgeimporter.views.upload_view import UploadView

logger = logging.getLogger(__name__)


class KnowledgeImporterApp:
    """Root application managing navigation and shared state."""

    def __init__(self, page: ft.Page) -> None:
        self.page = page
        self.config = AppConfig()
        self._upload_view: UploadView | None = None
        self._settings_view: SettingsView | None = None

    async def initialize(self) -> None:
        """Set up the page, load config, and build UI."""
        await self._configure_page()
        self._load_config()
        self._build_ui()

    async def _configure_page(self) -> None:
        self.page.title = "KnowledgeImporter"
        self.page.theme_mode = ft.ThemeMode.SYSTEM
        self.page.window.icon = "KnowledgeImporter.png"
        self.page.window.width = 1000
        self.page.window.height = 700
        self.page.window.min_width = 800
        self.page.window.min_height = 550
        await self.page.window.center()
        self.page.padding = 20

    def _load_config(self) -> None:
        try:
            self.config = load_config()
            logger.info("Config loaded successfully")
        except Exception as e:
            logger.warning("Failed to load config, using defaults: %s", e)
            self.config = AppConfig()

    def _build_ui(self) -> None:
        self._upload_view = UploadView(
            config=self.config,
            page=self.page,
            on_config_changed=self._on_config_changed,
        )
        self._settings_view = SettingsView(
            config=self.config,
            page=self.page,
            on_config_saved=self._on_config_saved,
        )

        self._content_area = ft.Container(
            content=self._upload_view.build(),
            expand=True,
        )

        self.page.navigation_bar = ft.NavigationBar(
            selected_index=0,
            on_change=self._on_nav_change,
            destinations=[
                ft.NavigationBarDestination(
                    icon=ft.Icons.UPLOAD_FILE_OUTLINED,
                    selected_icon=ft.Icons.UPLOAD_FILE,
                    label="Upload",
                ),
                ft.NavigationBarDestination(
                    icon=ft.Icons.SETTINGS_OUTLINED,
                    selected_icon=ft.Icons.SETTINGS,
                    label="Settings",
                ),
            ],
        )

        self.page.add(self._content_area)

    def _on_nav_change(self, e: ft.ControlEvent) -> None:
        idx = e.control.selected_index
        if idx == 0:
            self._content_area.content = self._upload_view.build()
        elif idx == 1:
            self._content_area.content = self._settings_view.build()
        self._content_area.update()

    def _on_config_saved(self, config: AppConfig) -> None:
        """Called when settings are saved."""
        self.config = config
        try:
            save_config(config)
            self.page.show_dialog(ft.SnackBar(content=ft.Text("Settings saved")))
        except Exception as e:
            logger.error("Failed to save config: %s", e)
            self.page.show_dialog(ft.SnackBar(content=ft.Text(f"Save failed: {e}")))

        # Update upload view with new config
        if self._upload_view:
            self._upload_view.config = config
            self._upload_view.refresh_target_display()

    def _on_config_changed(self, config: AppConfig) -> None:
        """Called when config changes from upload view (e.g. last_source_dir)."""
        self.config = config
        try:
            save_config(config)
        except Exception as e:
            logger.warning("Failed to auto-save config: %s", e)
