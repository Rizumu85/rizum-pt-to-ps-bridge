"""Painter-owned lifecycle for the native PT Bridge mapper."""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from . import desktop_transfer, exporter
from .photoshop_job import PhotoshopJob
from .ui_dialogs import CompactProgressDialog


SETTINGS_ORG = "Rizum"
SETTINGS_APP = "PTBridge"
PHOTOSHOP_DIR_KEY = "photoshop_document_dir"
PHOTOSHOP_DOCUMENT_KEY = "photoshop_document_path"
PHOTOSHOP_SUFFIXES = {".psd", ".psb"}
DESKTOP_REQUEST_MARKER = "@ptbridge "
IDLE_TOOLTIP = "Map layers between Painter and Photoshop"


class DesktopBridgeController:
    """Launch the native mapper and apply its explicit response in Painter."""

    def __init__(self, panel, show_message):
        self.panel = panel
        self.QtCore = panel.QtCore
        self.QtWidgets = panel.QtWidgets
        self._show_message_callback = show_message
        self._process = None
        self._transfer_path = None
        self._closing = False
        self._process_error_reported = False
        self._applying_transfer = False
        self._photoshop_job = None
        self._pending_transfer_result = None
        self._photoshop_progress_dialog = None
        self._photoshop_phase = None
        self._picking = False
        self._trace_path = None
        self._stdout_buffer = ""

        self.button = panel.dock_bridge_button
        self.button.clicked.connect(self.open)
        self._sync_button()

    def close(self):
        """Detach the controller and stop an owned desktop session on unload."""
        if self._closing:
            return
        self._closing = True
        self._clear_photoshop_export()
        try:
            self.button.clicked.disconnect(self.open)
        except (RuntimeError, TypeError):
            pass
        process = self._process
        self._process = None
        if (
            process is not None
            and process.state()
            != self.QtCore.QProcess.ProcessState.NotRunning
        ):
            process.terminate()
            if not process.waitForFinished(800):
                process.kill()
        if process is not None:
            process.deleteLater()

    def open(self):
        """Launch one mapping session with the last connected Photoshop document."""
        if self._busy_reason() is not None:
            return
        if not self.panel._project_is_open():
            self._show("Bridge", "Open a Painter project before starting Bridge.")
            return
        if not self.panel._project_is_ready():
            self._show("Bridge", "Painter project is still loading or not editable.")
            return

        self._launch_desktop(self._recent_photoshop_document())

    def _launch_desktop(self, psd_path):
        try:
            executable = _desktop_executable()
            session_dir = exporter.default_output_dir(
                self.panel.user_settings
            ) / "_desktop_bridge"
            session_dir.mkdir(parents=True, exist_ok=True)
            self._trace_path = session_dir / "desktop_session.log"
            self._trace("preparing_snapshot", reset=True)
            snapshot_path = session_dir / "painter_snapshot.json"
            transfer_path = session_dir / "desktop_transfer.json"
            transfer_path.unlink(missing_ok=True)
            exporter.write_painter_snapshot(
                snapshot_path,
                self.panel.user_settings,
            )
        except Exception as exc:
            self._show("Bridge", str(exc))
            return

        self._transfer_path = transfer_path
        self._process_error_reported = False
        self._stdout_buffer = ""
        process = self.QtCore.QProcess(self.panel.widget)
        process.setProgram(str(executable))
        arguments = [
            "--painter",
            str(snapshot_path),
            "--output",
            str(transfer_path),
        ]
        if psd_path is not None:
            arguments[0:0] = ["--psd", str(psd_path)]
        process.setArguments(arguments)
        process.finished.connect(self._desktop_finished)
        process.errorOccurred.connect(self._desktop_error)
        process.readyReadStandardOutput.connect(self._desktop_output)
        process.started.connect(lambda: self._trace("desktop_started"))
        self._process = process
        self._sync_button()
        process.start()

    def _busy_reason(self):
        if self._photoshop_job is not None:
            return "Photoshop operation in progress"
        if self._applying_transfer:
            return "Applying mapped layers"
        if self._process is not None or self._picking:
            return "PT Bridge desktop is open"
        return None

    def _sync_button(self):
        # The dock button is derived from session state here and nowhere else.
        # Imperative enable/disable writes from several owners left it disabled
        # after every export; export itself runs behind an application-modal
        # progress dialog, so the panel has no reason to gate this button.
        if self._closing:
            return
        reason = self._busy_reason()
        self.button.setEnabled(reason is None)
        self.button.setToolTip(reason or IDLE_TOOLTIP)

    def _recent_photoshop_document(self):
        settings = self.QtCore.QSettings(SETTINGS_ORG, SETTINGS_APP)
        saved = settings.value(PHOTOSHOP_DOCUMENT_KEY, "", str) or ""
        path = Path(saved) if saved else None
        if path is not None and not path.is_file():
            # A moved or deleted PSD opens Bridge disconnected instead of failing.
            settings.remove(PHOTOSHOP_DOCUMENT_KEY)
            settings.sync()
            return None
        return path

    def _connect_photoshop(self):
        self._trace("opening_photoshop_picker")
        settings = self.QtCore.QSettings(SETTINGS_ORG, SETTINGS_APP)
        start_dir = settings.value(PHOTOSHOP_DIR_KEY, "", str) or ""
        # The system dialog keeps the user's shortcuts, recent folders and cloud
        # drives, which Qt's widget dialog lacked. Use the static call: an owned
        # native QFileDialog runs on a helper thread on Windows and crashed
        # Painter when deleted right after it closed. Blocking is harmless
        # here, since the mapper waits for this answer anyway; the mapper
        # grants Painter foreground rights first so the dialog is not hidden.
        self._picking = True
        self._sync_button()
        try:
            path, _selected_filter = self.QtWidgets.QFileDialog.getOpenFileName(
                self.panel.widget.window(),
                "Connect Photoshop Document",
                start_dir,
                "Photoshop Document (*.psd *.psb)",
            )
        finally:
            self._picking = False
        self._photoshop_source_chosen(path)

    def _photoshop_source_chosen(self, path):
        if self._closing:
            return
        self._sync_button()
        if self._process is None:
            # The mapper window closed while the picker was open; its connection
            # request ended with it.
            return
        if not path:
            self._trace("photoshop_picker_cancelled")
            self._reply_to_desktop({"type": "photoshop_connect_cancelled"})
            return
        source_path = Path(path)
        self._trace("photoshop_source_selected", source_path.suffix)
        if source_path.suffix.lower() not in PHOTOSHOP_SUFFIXES:
            self._reply_to_desktop({
                "type": "photoshop_connect_failed",
                "message": f"{source_path.name} is not a Photoshop document.",
            })
            return
        settings = self.QtCore.QSettings(SETTINGS_ORG, SETTINGS_APP)
        settings.setValue(PHOTOSHOP_DIR_KEY, str(source_path.parent))
        # The mapper reads the PSD itself, so connecting never starts Photoshop.
        settings.setValue(PHOTOSHOP_DOCUMENT_KEY, str(source_path))
        settings.sync()
        self._reply_to_desktop({"type": "photoshop_connected", "psd": str(source_path)})

    def _reply_to_desktop(self, payload):
        # The mapper stays open while Painter connects Photoshop, so replies go
        # to its stdin instead of relaunching it with a new session.
        process = self._process
        if process is None:
            return
        self._trace("desktop_reply", payload.get("type", ""))
        process.write((json.dumps(payload) + "\n").encode("utf-8"))

    def _start_photoshop_job(self, launch, label, transfer_result):
        self._clear_photoshop_export()
        self._pending_transfer_result = transfer_result
        # Only Painter reads the script's progress receipts, so Painter shows
        # the layer count in the same compact dialog style as export.
        self._photoshop_progress_dialog = CompactProgressDialog(
            self.panel, "Photoshop", f"Opening Photoshop... {label}", cancellable=False, modal=False,
        )
        self._photoshop_progress_dialog.show()
        try:
            launched, message = self.panel.launch_photoshop(launch.launcher_path)
        except Exception as exc:
            self._photoshop_job_failed(str(exc))
            return
        if not launched:
            self._photoshop_job_failed(message)
            return
        self._trace("photoshop_launch_requested", str(launch.launcher_path))
        self._photoshop_job = PhotoshopJob(
            self.QtCore,
            self.panel.widget,
            launch,
            on_progress=self._update_photoshop_progress,
            on_done=self._finish_photoshop_transfer,
            on_failed=self._photoshop_job_failed,
        )
        self._photoshop_job.start()
        self._sync_button()

    def _update_photoshop_progress(self, payload):
        phase = payload.get("phase")
        if phase != self._photoshop_phase:
            self._trace("photoshop_progress", str(phase))
            self._photoshop_phase = phase
        dialog = self._photoshop_progress_dialog
        total = payload.get("total", 0)
        completed = payload.get("completed", 0)
        if dialog is None or not isinstance(total, int) or not isinstance(completed, int):
            return
        if phase == "transferring_layers" and total > 0:
            dialog.setRange(0, total)
            dialog.setValue(max(0, min(completed, total)))
            message = f"Inserting Photoshop layers: {completed} / {total}"
        elif phase == "saving_document":
            message = "Saving Photoshop document..."
        else:
            message = "Opening Photoshop document..."
        dialog.setLabelText(message)

    def _photoshop_job_failed(self, message):
        self._trace("photoshop_job_failed", message)
        transfer = self._pending_transfer_result
        self._clear_photoshop_export()
        if self._closing:
            return
        # A cross-host operation is not atomic. Never retry Painter edits
        # because Photoshop failed, or claim both hosts rolled back together.
        if transfer.imported_count:
            message = f"Already imported {transfer.imported_count} layer(s) into Painter.\n\n{message}"
        self._show("Bridge transfer incomplete", message)

    def _finish_photoshop_transfer(self, payload):
        transfer = self._pending_transfer_result
        inserted = payload.get("inserted") if isinstance(payload, dict) else None
        if not isinstance(inserted, list):
            self._photoshop_job_failed("Photoshop returned an invalid transfer result.")
            return
        count = len(inserted)
        if payload.get("success") is not True or count != transfer.exported_count:
            message = f"Inserted {count} of {transfer.exported_count} layer(s) into Photoshop.\n"
            message += _photoshop_export_error_summary(payload)
            message += "\n\nCheck both documents before retrying; completed inserts were not undone."
            self._photoshop_job_failed(message)
            return
        self._trace("photoshop_transfer_ready", str(count))
        self._clear_photoshop_export()
        warnings = list(transfer.warnings) + [str(value) for value in payload.get("warnings", [])]
        if payload.get("saved") is not True and not payload.get("warnings"):
            warnings.append("Photoshop changes are open but have not been saved.")
        self._report_transfer_complete(transfer.imported_count, count, warnings)

    def _report_transfer_complete(self, imported_count, exported_count, warnings):
        parts = []
        if imported_count:
            parts.append(f"Imported {imported_count} Photoshop layer(s) into Painter")
        if exported_count:
            parts.append(f"inserted {exported_count} Painter layer(s) into Photoshop")
        message = "; ".join(parts) + "."
        if warnings:
            message += "\n\n" + "\n".join(warnings)
        self._show("Bridge complete", message)

    def _clear_photoshop_export(self):
        job = self._photoshop_job
        self._photoshop_job = None
        self._pending_transfer_result = None
        self._photoshop_phase = None
        dialog = self._photoshop_progress_dialog
        self._photoshop_progress_dialog = None
        if dialog is not None:
            dialog.close()
        if job is not None:
            job.stop()
        self._sync_button()

    def _desktop_error(self, process_error):
        if self._closing or self._process_error_reported:
            return
        failed_to_start = self.QtCore.QProcess.ProcessError.FailedToStart
        if process_error != failed_to_start:
            return
        self._process_error_reported = True
        process = self._take_process()
        detail = process.errorString() if process is not None else "Unknown process error"
        if process is not None:
            process.deleteLater()
        self._show("Bridge", f"Could not start PT Bridge desktop.\n\n{detail}")

    def _desktop_finished(self, exit_code, _exit_status):
        # Unload can deliver a final QProcess signal after the dock is disposed.
        # close() owns that cleanup; an exiting child must not touch the old UI.
        if self._closing:
            return
        self._desktop_output()
        self._trace("desktop_finished", str(exit_code))
        process = self._take_process()
        if process is None:
            return
        stderr = bytes(process.readAllStandardError()).decode(
            "utf-8",
            errors="replace",
        ).strip()
        if int(exit_code) != 0:
            detail = stderr or f"Desktop process exited with code {exit_code}."
            process.deleteLater()
            self._show("Bridge", detail)
            return

        transfer_path = self._transfer_path
        if transfer_path is None or not transfer_path.is_file():
            self._trace("desktop_closed_without_request")
            process.deleteLater()
            return

        try:
            request_type = _desktop_request_type(transfer_path)
        except Exception as exc:
            process.deleteLater()
            self._show("Bridge", str(exc))
            return
        if request_type != "desktop_transfer":
            process.deleteLater()
            self._show("Bridge", f"Unsupported desktop request: {request_type or '(missing)'}")
            return

        self._applying_transfer = True
        self._sync_button()
        try:
            result = desktop_transfer.apply_transfer_manifest(
                transfer_path,
                settings=self.panel.user_settings,
            )
        except Exception as exc:
            process.deleteLater()
            self._show("Bridge", str(exc))
            return
        finally:
            self._applying_transfer = False
            self._sync_button()

        process.deleteLater()
        if result.photoshop_launch is not None:
            self._start_photoshop_job(
                result.photoshop_launch, f"Insert {result.exported_count} layer(s)", result,
            )
        else:
            self._report_transfer_complete(result.imported_count, 0, result.warnings)

    def _take_process(self):
        process = self._process
        self._process = None
        self._sync_button()
        return process

    def _show(self, title, message):
        self._trace(title, message)
        self._show_message_callback(
            self.QtWidgets,
            self.panel.widget,
            title,
            message,
        )

    def _open_photoshop_picker(self):
        if self._closing:
            return
        try:
            self._connect_photoshop()
        except Exception as exc:
            self._sync_button()
            self._reply_to_desktop({"type": "photoshop_connect_failed", "message": str(exc)})

    def _desktop_output(self):
        if self._process is None:
            return
        self._stdout_buffer += bytes(self._process.readAllStandardOutput()).decode(
            "utf-8", errors="replace"
        )
        *lines, self._stdout_buffer = self._stdout_buffer.split("\n")
        for line in lines:
            line = line.strip()
            if line.startswith(DESKTOP_REQUEST_MARKER):
                self._desktop_request(line[len(DESKTOP_REQUEST_MARKER):])
            elif line:
                self._trace("desktop", line)

    def _desktop_request(self, text):
        try:
            request_type = json.loads(text).get("type")
        except (ValueError, AttributeError):
            request_type = None
        self._trace("desktop_request", str(request_type))
        if request_type != "connect_photoshop":
            self._reply_to_desktop({
                "type": "photoshop_connect_failed",
                "message": f"Unsupported desktop request: {request_type or '(missing)'}",
            })
            return
        if self._picking or self._photoshop_job is not None:
            return
        # Leave the stdout signal before opening a new modal owner.
        self.QtCore.QTimer.singleShot(0, self._open_photoshop_picker)

    def _trace(self, event, detail="", *, reset=False):
        # Keep only lifecycle diagnostics, not snapshot data, so real host-only
        # failures can be distinguished from a missed click without exporting art.
        if self._trace_path is None:
            return
        try:
            with self._trace_path.open("w" if reset else "a", encoding="utf-8") as stream:
                stream.write(f"{datetime.now(timezone.utc).isoformat()} {event} {detail}\n")
        except OSError:
            pass


def attach(panel, show_message):
    """Attach the desktop bridge lifecycle to an initialized Painter panel."""
    if panel is None:
        raise RuntimeError("Painter panel must exist before desktop Bridge attaches.")
    return DesktopBridgeController(panel, show_message)


def _desktop_executable():
    configured = os.environ.get("RIZUM_PT_BRIDGE_DESKTOP", "").strip()
    if configured:
        path = Path(configured)
    else:
        plugin_root = Path(__file__).resolve().parents[2]
        filename = "pt-bridge.exe" if sys.platform == "win32" else "pt-bridge"
        path = plugin_root / "desktop" / "dist" / filename
    if not path.is_file():
        raise FileNotFoundError(
            "PT Bridge desktop runtime was not found. Build desktop/dist/pt-bridge "
            "before using the Bridge action."
        )
    return path


def _desktop_request_type(path):
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except OSError as exc:
        raise RuntimeError(f"Could not read desktop response: {path}") from exc
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Desktop response is not valid JSON: {path}") from exc
    if not isinstance(payload, dict):
        raise RuntimeError("Desktop response must be a JSON object.")
    return payload.get("request_type")


def _photoshop_export_error_summary(payload):
    if not isinstance(payload, dict):
        return "Photoshop returned an invalid transfer result."
    errors = payload.get("errors")
    if not isinstance(errors, list) or not errors:
        return "Photoshop did not report what failed."
    lines = []
    for entry in errors[:8]:
        if isinstance(entry, dict):
            layer = entry.get("layer") or entry.get("name") or "Photoshop"
            detail = entry.get("error") or entry.get("message") or "Unknown error"
            lines.append(f"{layer}: {detail}")
        else:
            lines.append(str(entry))
    if len(errors) > 8:
        lines.append(f"...and {len(errors) - 8} more error(s).")
    return "\n".join(lines)
