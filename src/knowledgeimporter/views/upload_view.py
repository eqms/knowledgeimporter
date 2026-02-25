"""Upload view — main screen for batch uploading files to LangDock."""

import logging
from collections.abc import Callable
from pathlib import Path

import flet as ft

from knowledgeimporter.models.config import AppConfig
from knowledgeimporter.services.upload_service import UploadService
from knowledgeimporter.utils.upload_logger import (
    append_log,
    cleanup_old_logs,
    create_upload_log,
    finalize_log,
    get_latest_log,
    open_log_in_editor,
)
from knowledgeimporter.utils.worker import BackgroundWorker

logger = logging.getLogger(__name__)


class UploadView:
    """Main upload screen with folder selection, progress bar, and file-based log."""

    def __init__(
        self,
        config: AppConfig,
        page: ft.Page,
        on_config_changed: Callable[[AppConfig], None],
    ) -> None:
        self.config = config
        self.page = page
        self._on_config_changed = on_config_changed
        self._worker = BackgroundWorker()
        self._upload_service: UploadService | None = None
        self._file_count = 0
        self._current_log: Path | None = None

        # File picker is a service in Flet 0.80+, registered via page.services
        self._dir_picker = ft.FilePicker()
        page.services.append(self._dir_picker)

        # Clean up old log files on startup
        cleanup_old_logs()

        # Controls
        self._source_path_text = ft.Text(
            config.last_source_dir or "No folder selected",
            size=14,
            expand=True,
        )
        self._file_count_text = ft.Text("", size=13)
        self._folder_info_text = ft.Text(self._folder_display(), size=13)
        self._progress_bar = ft.ProgressBar(value=0, visible=False, width=600)
        self._progress_text = ft.Text("", size=13)
        self._spinner = ft.ProgressRing(width=20, height=20, stroke_width=2, visible=False)
        self._status_text = ft.Text("Ready", size=14, weight=ft.FontWeight.W_600)
        self._current_file_text = ft.Text("", size=12, italic=True)
        self._stats_text = ft.Text("", size=13)

        self._upload_btn = ft.ElevatedButton(
            "Start Upload",
            icon=ft.Icons.CLOUD_UPLOAD,
            on_click=self._start_upload,
            disabled=True,
            style=ft.ButtonStyle(
                bgcolor=ft.Colors.PRIMARY,
                color=ft.Colors.ON_PRIMARY,
            ),
        )
        self._cancel_btn = ft.OutlinedButton(
            "Cancel",
            icon=ft.Icons.CANCEL,
            on_click=self._cancel_upload,
            visible=False,
        )
        self._view_log_btn = ft.TextButton(
            "View Log",
            icon=ft.Icons.DESCRIPTION,
            on_click=self._view_log,
            visible=get_latest_log() is not None,
        )

        # Update file count if we have a last source dir
        if config.last_source_dir:
            self._update_file_count(config.last_source_dir)

    def build(self) -> ft.Control:
        """Build and return the upload view layout."""
        self._folder_info_text.value = self._folder_display()

        return ft.Column(
            controls=[
                ft.Text("Upload", size=24, weight=ft.FontWeight.BOLD),
                ft.Divider(),
                # Source folder section
                ft.Text("Source Folder", size=16, weight=ft.FontWeight.W_600),
                ft.Row(
                    controls=[
                        ft.Icon(ft.Icons.FOLDER_OPEN, size=20),
                        self._source_path_text,
                        ft.ElevatedButton(
                            "Choose Folder",
                            icon=ft.Icons.FOLDER,
                            on_click=self._pick_folder,
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.START,
                ),
                self._file_count_text,
                ft.Divider(),
                # Target folder section
                ft.Text("Target", size=16, weight=ft.FontWeight.W_600),
                ft.Row(
                    controls=[
                        ft.Icon(ft.Icons.CLOUD, size=20),
                        self._folder_info_text,
                    ],
                ),
                ft.Divider(),
                # Upload controls
                ft.Row(
                    controls=[
                        self._upload_btn,
                        self._cancel_btn,
                        self._spinner,
                        self._status_text,
                    ],
                    spacing=15,
                    alignment=ft.MainAxisAlignment.START,
                ),
                self._progress_bar,
                self._progress_text,
                self._current_file_text,
                self._stats_text,
                # Log link
                ft.Row(
                    controls=[self._view_log_btn],
                    alignment=ft.MainAxisAlignment.END,
                ),
            ],
            spacing=10,
            expand=True,
        )

    def refresh_target_display(self) -> None:
        """Refresh target folder display and upload button state after config change."""
        self._folder_info_text.value = self._folder_display()
        if self.config.last_source_dir:
            self._update_file_count(self.config.last_source_dir)

    def _folder_display(self) -> str:
        name = self.config.folder_name or "Not configured"
        fid = self.config.default_folder_id
        if fid:
            short_id = fid[:8] + "..." if len(fid) > 12 else fid
            return f"{name} ({short_id})"
        return f"{name} — configure in Settings"

    async def _pick_folder(self, _e: ft.ControlEvent) -> None:
        initial = self.config.last_source_dir or None
        result = await self._dir_picker.get_directory_path(
            dialog_title="Select source folder",
            initial_directory=initial,
        )
        if not result:
            return

        self._source_path_text.value = result
        self._update_file_count(result)

        # Persist last source dir
        self.config.last_source_dir = result
        self._on_config_changed(self.config)
        self.page.update()

    def _update_file_count(self, source_dir: str) -> None:
        import fnmatch

        source = Path(source_dir)
        count = 0
        if source.is_dir():
            for item in source.iterdir():
                if not item.is_file():
                    continue
                for pattern in self.config.file_patterns:
                    if fnmatch.fnmatch(item.name, pattern):
                        count += 1
                        break

        self._file_count = count
        self._file_count_text.value = f"{self._file_count} file(s) matching {', '.join(self.config.file_patterns)}"
        self._upload_btn.disabled = self._file_count == 0 or not self.config.default_folder_id

    def _start_upload(self, _e: ft.ControlEvent) -> None:
        if not self.config.langdock_api_key:
            self._status_text.value = "API key not configured — go to Settings"
            self._status_text.color = ft.Colors.ERROR
            self.page.update()
            return

        if not self.config.default_folder_id:
            self._status_text.value = "Folder ID not configured — go to Settings"
            self._status_text.color = ft.Colors.ERROR
            self.page.update()
            return

        source_dir = self._source_path_text.value or ""
        if not source_dir or source_dir == "No folder selected":
            self._status_text.value = "Select a source folder first"
            self._status_text.color = ft.Colors.ERROR
            self.page.update()
            return

        # Create log file for this upload session
        self._current_log = create_upload_log()
        append_log(self._current_log, f"Source: {source_dir}")
        append_log(self._current_log, f"Target folder: {self.config.folder_name} ({self.config.default_folder_id})")
        append_log(self._current_log, f"Patterns: {', '.join(self.config.file_patterns)}")
        append_log(self._current_log, f"Replace mode: {self.config.replace_existing}")

        # Prepare UI for upload
        self._progress_bar.visible = True
        self._progress_bar.value = 0
        self._upload_btn.disabled = True
        self._cancel_btn.visible = True
        self._spinner.visible = True
        self._status_text.value = "Uploading..."
        self._status_text.color = ft.Colors.PRIMARY
        self._stats_text.value = ""
        self._progress_text.value = ""
        self._current_file_text.value = ""
        self.page.update()

        self._upload_service = UploadService(api_key=self.config.langdock_api_key)

        def do_upload():
            return self._upload_service.upload_batch(
                source_dir=source_dir,
                folder_id=self.config.default_folder_id,
                patterns=self.config.file_patterns,
                replace=self.config.replace_existing,
                on_progress=self._on_progress,
            )

        self._worker.run(
            fn=do_upload,
            on_complete=self._on_upload_complete,
            on_error=self._on_upload_error,
        )

    def _on_progress(self, current: int, total: int, filename: str, status: str) -> None:
        """Called from background thread — delegates UI update to Flet event loop."""
        # Write to log file (thread-safe file I/O)
        if self._current_log:
            if status == "uploading":
                append_log(self._current_log, f"[UPLOAD] {filename}")
            elif status == "success":
                append_log(self._current_log, f"[OK]     {filename}")
            elif status == "error":
                append_log(self._current_log, f"[FAIL]   {filename}")
            elif status == "cancelled":
                append_log(self._current_log, "[CANCELLED]")
            else:
                append_log(self._current_log, f"[{status.upper()}] {filename}")

        async def _update():
            if total > 0:
                self._progress_bar.value = current / total
            self._progress_text.value = f"{current}/{total}"

            if status == "uploading":
                self._current_file_text.value = f"Uploading: {filename}"
                self._current_file_text.color = None
            elif status == "success":
                self._current_file_text.value = f"{filename}"
                self._current_file_text.color = ft.Colors.GREEN
            elif status == "error":
                self._current_file_text.value = f"{filename} — FAILED"
                self._current_file_text.color = ft.Colors.ERROR
            elif status == "cancelled":
                self._current_file_text.value = "Upload cancelled"
                self._current_file_text.color = ft.Colors.AMBER
            else:
                self._current_file_text.value = f"{filename} ({status})"
                self._current_file_text.color = None

            self.page.update()

        self.page.run_task(_update)

    def _on_upload_complete(self, result: dict) -> None:
        """Called from background thread — delegates UI update to Flet event loop."""
        # Finalize log file
        if self._current_log:
            finalize_log(self._current_log, result)

        async def _update():
            total = result.get("total", 0)
            success = result.get("success", 0)
            failed = result.get("failed", 0)
            skipped = result.get("skipped", 0)

            self._status_text.value = "Complete"
            self._status_text.color = ft.Colors.GREEN if failed == 0 else ft.Colors.AMBER
            self._stats_text.value = f"Total: {total} | Success: {success} | Failed: {failed} | Skipped: {skipped}"
            self._progress_bar.value = 1.0
            self._upload_btn.disabled = False
            self._cancel_btn.visible = False
            self._spinner.visible = False
            self._current_file_text.value = ""
            self._view_log_btn.visible = True
            self.page.update()

        self.page.run_task(_update)

    def _on_upload_error(self, error: Exception) -> None:
        """Called from background thread — delegates UI update to Flet event loop."""
        if self._current_log:
            append_log(self._current_log, f"[ERROR] {error}")

        async def _update():
            self._status_text.value = f"Error: {error}"
            self._status_text.color = ft.Colors.ERROR
            self._upload_btn.disabled = False
            self._cancel_btn.visible = False
            self._spinner.visible = False
            self._progress_bar.visible = False
            self._current_file_text.value = ""
            self._view_log_btn.visible = True
            self.page.update()

        self.page.run_task(_update)

    def _cancel_upload(self, _e: ft.ControlEvent) -> None:
        if self._upload_service:
            self._upload_service.cancel()
        self._worker.cancel()
        self._status_text.value = "Cancelling..."
        self._status_text.color = ft.Colors.AMBER
        self._spinner.visible = False

        if self._current_log:
            append_log(self._current_log, "[CANCELLED] Upload cancelled by user")

        self.page.update()

    def _view_log(self, _e: ft.ControlEvent) -> None:
        """Open the most recent log file in the system editor."""
        log_file = self._current_log or get_latest_log()
        if log_file and log_file.exists():
            open_log_in_editor(log_file)
        else:
            self._status_text.value = "No log file available"
            self._status_text.color = ft.Colors.AMBER
            self.page.update()
