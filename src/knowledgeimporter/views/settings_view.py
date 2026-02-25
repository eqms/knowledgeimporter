"""Settings view for API key, folder configuration, and upload preferences."""

import logging
from collections.abc import Callable

import flet as ft

from knowledgeimporter.models.config import AppConfig

logger = logging.getLogger(__name__)


class SettingsView:
    """Settings screen for configuring API key, folder, and upload options."""

    def __init__(
        self,
        config: AppConfig,
        page: ft.Page,
        on_config_saved: Callable[[AppConfig], None],
    ) -> None:
        self.config = config
        self.page = page
        self._on_config_saved = on_config_saved
        self._api_key_visible = False

        # Controls
        self._api_key_field = ft.TextField(
            label="LangDock API Key",
            value=config.langdock_api_key,
            password=True,
            can_reveal_password=True,
            width=500,
        )
        self._region_dropdown = ft.Dropdown(
            label="Region",
            value=config.region,
            width=200,
            options=[
                ft.dropdown.Option("eu", "EU (GDPR)"),
                ft.dropdown.Option("us", "US"),
            ],
        )
        self._folder_id_field = ft.TextField(
            label="Folder ID",
            value=config.default_folder_id,
            width=500,
            hint_text="UUID from LangDock Knowledge Folder",
        )
        self._folder_name_field = ft.TextField(
            label="Folder Name (Display)",
            value=config.folder_name,
            width=300,
            hint_text="e.g. CMC Datasheets",
        )
        self._patterns_field = ft.TextField(
            label="File Patterns (comma-separated)",
            value=", ".join(config.file_patterns),
            width=300,
            hint_text="*.md, *.txt",
        )
        self._replace_checkbox = ft.Checkbox(
            label="Replace existing files on upload",
            value=config.replace_existing,
        )
        self._connection_status = ft.Text("", size=13)
        self._folder_status = ft.Text("", size=13)

    def build(self) -> ft.Control:
        """Build and return the settings view layout."""
        return ft.Column(
            controls=[
                ft.Text("Settings", size=24, weight=ft.FontWeight.BOLD),
                ft.Divider(),
                # API Key Section
                ft.Text("LangDock API", size=16, weight=ft.FontWeight.W_600),
                ft.Row(
                    controls=[
                        self._api_key_field,
                        ft.ElevatedButton(
                            "Test Connection",
                            icon=ft.Icons.WIFI_TETHERING,
                            on_click=self._test_connection,
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.START,
                ),
                self._connection_status,
                self._region_dropdown,
                ft.Divider(),
                # Folder Section
                ft.Text("Knowledge Folder", size=16, weight=ft.FontWeight.W_600),
                ft.Row(
                    controls=[
                        self._folder_id_field,
                        ft.ElevatedButton(
                            "Validate",
                            icon=ft.Icons.CHECK_CIRCLE_OUTLINE,
                            on_click=self._validate_folder,
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.START,
                ),
                self._folder_status,
                self._folder_name_field,
                ft.Divider(),
                # Upload Preferences Section
                ft.Text("Upload Preferences", size=16, weight=ft.FontWeight.W_600),
                self._patterns_field,
                self._replace_checkbox,
                ft.Divider(),
                # Action Buttons
                ft.Row(
                    controls=[
                        ft.ElevatedButton(
                            "Save",
                            icon=ft.Icons.SAVE,
                            on_click=self._save_settings,
                            style=ft.ButtonStyle(
                                bgcolor=ft.Colors.PRIMARY,
                                color=ft.Colors.ON_PRIMARY,
                            ),
                        ),
                        ft.OutlinedButton(
                            "Reset",
                            icon=ft.Icons.RESTORE,
                            on_click=self._reset_settings,
                        ),
                    ],
                    spacing=10,
                ),
            ],
            spacing=12,
            scroll=ft.ScrollMode.AUTO,
            expand=True,
        )

    def _build_config_from_fields(self) -> AppConfig:
        """Create an AppConfig from the current field values."""
        patterns_raw = self._patterns_field.value or "*.md"
        patterns = [p.strip() for p in patterns_raw.split(",") if p.strip()]
        if not patterns:
            patterns = ["*.md"]

        return AppConfig(
            langdock_api_key=self._api_key_field.value or "",
            region=self._region_dropdown.value or "eu",
            default_folder_id=self._folder_id_field.value or "",
            folder_name=self._folder_name_field.value or "",
            last_source_dir=self.config.last_source_dir,
            file_patterns=patterns,
            replace_existing=self._replace_checkbox.value or False,
        )

    def _save_settings(self, _e: ft.ControlEvent) -> None:
        config = self._build_config_from_fields()
        self._on_config_saved(config)
        self.config = config

    def _reset_settings(self, _e: ft.ControlEvent) -> None:
        self._api_key_field.value = self.config.langdock_api_key
        self._region_dropdown.value = self.config.region
        self._folder_id_field.value = self.config.default_folder_id
        self._folder_name_field.value = self.config.folder_name
        self._patterns_field.value = ", ".join(self.config.file_patterns)
        self._replace_checkbox.value = self.config.replace_existing
        self._connection_status.value = ""
        self._folder_status.value = ""
        self.page.update()

    def _test_connection(self, _e: ft.ControlEvent) -> None:
        api_key = self._api_key_field.value or ""
        if not api_key:
            self._connection_status.value = "Please enter an API key first"
            self._connection_status.color = ft.Colors.ERROR
            self.page.update()
            return

        self._connection_status.value = "Testing..."
        self._connection_status.color = None
        self.page.update()

        try:
            from knowledgeimporter.utils.storage import test_api_connection

            ok = test_api_connection(api_key)
            if ok:
                self._connection_status.value = "Connection successful"
                self._connection_status.color = ft.Colors.GREEN
            else:
                self._connection_status.value = "Connection failed — check API key"
                self._connection_status.color = ft.Colors.ERROR
        except Exception as e:
            self._connection_status.value = f"Error: {e}"
            self._connection_status.color = ft.Colors.ERROR

        self.page.update()

    def _validate_folder(self, _e: ft.ControlEvent) -> None:
        api_key = self._api_key_field.value or ""
        folder_id = self._folder_id_field.value or ""

        if not api_key:
            self._folder_status.value = "API key required"
            self._folder_status.color = ft.Colors.ERROR
            self.page.update()
            return

        if not folder_id:
            self._folder_status.value = "Folder ID required"
            self._folder_status.color = ft.Colors.ERROR
            self.page.update()
            return

        self._folder_status.value = "Validating..."
        self._folder_status.color = None
        self.page.update()

        try:
            from knowledgeimporter.utils.storage import validate_folder

            region = self._region_dropdown.value or "eu"
            ok, file_count = validate_folder(api_key, folder_id, region)
            if ok:
                self._folder_status.value = f"Folder valid — {file_count} file(s) found"
                self._folder_status.color = ft.Colors.GREEN
                # Auto-save config after successful validation
                config = self._build_config_from_fields()
                self._on_config_saved(config)
                self.config = config
            else:
                self._folder_status.value = "Folder not found or access denied"
                self._folder_status.color = ft.Colors.ERROR
        except Exception as e:
            self._folder_status.value = f"Validation error: {e}"
            self._folder_status.color = ft.Colors.ERROR

        self.page.update()
