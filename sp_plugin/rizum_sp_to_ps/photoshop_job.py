"""Watch one Photoshop script launched by Painter through its receipts."""

from __future__ import annotations

import json
import time

START_TIMEOUT_SECONDS = 120
FINISH_TIMEOUT_SECONDS = 30 * 60
POLL_INTERVAL_MS = 400


class PhotoshopJob:
    """Poll a launched JSX script's progress and result files.

    Launching Photoshop only proves the OS accepted the process; the job counts
    as started once the script publishes its first progress receipt. The poll
    runs only while a job the user started is active, which keeps Painter free
    of background timers otherwise.
    """

    def __init__(self, QtCore, parent, launch, *, on_progress, on_done, on_failed):
        self.launch = launch
        self.started = False
        self._on_progress = on_progress
        self._on_done = on_done
        self._on_failed = on_failed
        self._started_at = 0.0
        self._timer = QtCore.QTimer(parent)
        self._timer.setInterval(POLL_INTERVAL_MS)
        self._timer.timeout.connect(self.poll)

    def start(self):
        self._started_at = time.monotonic()
        self._timer.start()

    def stop(self):
        timer = self._timer
        self._timer = None
        if timer is not None:
            timer.stop()
            timer.deleteLater()

    @property
    def active(self):
        return self._timer is not None

    def elapsed(self):
        return time.monotonic() - self._started_at

    def poll(self):
        if not self.active:
            return
        if not self.launch.result_path.is_file():
            progress = _read_json(self.launch.progress_path)
            if isinstance(progress, dict) and progress.get("phase"):
                self.started = True
                self._on_progress(progress)
            elapsed = self.elapsed()
            if not self.started and elapsed > START_TIMEOUT_SECONDS:
                self._fail(
                    "Photoshop did not start the script within 2 minutes. "
                    "Check Photoshop for a startup or script confirmation dialog."
                )
            elif elapsed > FINISH_TIMEOUT_SECONDS:
                self._fail("Photoshop did not finish the operation within 30 minutes.")
            return
        try:
            payload = json.loads(self.launch.result_path.read_text(encoding="utf-8-sig"))
        except (OSError, ValueError) as exc:
            # Scripts publish receipts by rename; a malformed published receipt
            # is a terminal failure, not a partial file to wait on forever.
            self._fail(f"Photoshop result could not be read: {exc}")
            return
        self.stop()
        self._on_done(payload)

    def _fail(self, message):
        self.stop()
        self._on_failed(message)


def _read_json(path):
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return None
