"""Background worker for running tasks outside the Flet UI thread."""

import logging
import threading
from collections.abc import Callable
from typing import Any

logger = logging.getLogger(__name__)


class BackgroundWorker:
    """Runs a callable in a background thread, reporting completion or errors."""

    def __init__(self) -> None:
        self._thread: threading.Thread | None = None
        self._cancel_event = threading.Event()

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    @property
    def cancel_event(self) -> threading.Event:
        """Expose cancel event so tasks can check for cancellation."""
        return self._cancel_event

    def run(
        self,
        fn: Callable[[], Any],
        on_complete: Callable[[Any], None] | None = None,
        on_error: Callable[[Exception], None] | None = None,
    ) -> None:
        """Execute fn in a background thread."""
        if self.is_running:
            logger.warning("Worker is already running, ignoring new request")
            return

        self._cancel_event.clear()

        def _target() -> None:
            try:
                result = fn()
                if on_complete:
                    on_complete(result)
            except Exception as e:
                logger.error("Background task failed: %s", e)
                if on_error:
                    on_error(e)

        self._thread = threading.Thread(target=_target, daemon=True)
        self._thread.start()

    def cancel(self) -> None:
        """Signal the background task to stop."""
        self._cancel_event.set()

    def wait(self, timeout: float | None = None) -> None:
        """Wait for the background thread to complete."""
        if self._thread is not None:
            self._thread.join(timeout=timeout)
