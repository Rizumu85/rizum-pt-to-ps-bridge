"""Painter-owned lifecycle for the native PT Bridge mapper."""

from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from . import desktop_transfer, exporter, photoshop_automation


SETTINGS_ORG = "Rizum"
SETTINGS_APP = "PTBridge"
PHOTOSHOP_DIR_KEY = "photoshop_document_dir"
MANIFEST_PATH_KEY = "desktop_manifest_path"
PHOTOSHOP_EXPORT_TIMEOUT_SECONDS = 30 * 60
PHOTOSHOP_START_TIMEOUT_SECONDS = 120
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
        self._photoshop_export_timer = None
        self._photoshop_launch = None
        self._pending_transfer_result = None
        self._photoshop_export_started_at = 0.0
        self._photoshop_progress_dialog = None
        self._photoshop_script_started = False
        self._photoshop_export_phase = None
        self._source_dialog = None
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
        if self._source_dialog is not None:
            self._source_dialog.close()
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

        self._launch_desktop(self._recent_photoshop_manifest())

    def _launch_desktop(self, manifest_path):
        try:
            if manifest_path is not None:
                _validate_photoshop_manifest(manifest_path)
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
        if manifest_path is not None:
            arguments[0:0] = ["--session", str(manifest_path)]
        process.setArguments(arguments)
        process.finished.connect(self._desktop_finished)
        process.errorOccurred.connect(self._desktop_error)
        process.readyReadStandardOutput.connect(self._desktop_output)
        process.started.connect(lambda: self._trace("desktop_started"))
        self._process = process
        self._sync_button()
        process.start()

    def _busy_reason(self):
        if self._photoshop_launch is not None:
            return "Photoshop operation in progress"
        if self._applying_transfer:
            return "Applying mapped layers"
        if self._process is not None or self._source_dialog is not None:
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

    def _recent_photoshop_manifest(self):
        settings = self.QtCore.QSettings(SETTINGS_ORG, SETTINGS_APP)
        saved = settings.value(MANIFEST_PATH_KEY, "", str) or ""
        if not saved:
            return None
        path = Path(saved)
        try:
            _validate_photoshop_manifest(path)
        except RuntimeError:
            # A stale document must become an explicit disconnected state instead
            # of blocking every future Bridge launch before the mapper is visible.
            settings.remove(MANIFEST_PATH_KEY)
            settings.sync()
            return None
        return path

    def _connect_photoshop(self):
        self._trace("opening_photoshop_picker")
        settings = self.QtCore.QSettings(SETTINGS_ORG, SETTINGS_APP)
        start_dir = settings.value(PHOTOSHOP_DIR_KEY, "", str) or ""
        dialog = self.QtWidgets.QFileDialog(
            self.panel.widget.window(), "Connect Photoshop Document", start_dir,
        )
        # Desktop has just relinquished focus. An owned, non-blocking Qt dialog
        # can be raised explicitly and disposed on unload; a static OS dialog cannot.
        dialog.setOption(self.QtWidgets.QFileDialog.Option.DontUseNativeDialog, True)
        dialog.setFileMode(self.QtWidgets.QFileDialog.FileMode.ExistingFile)
        dialog.setNameFilters(["Photoshop Document (*.psd *.psb)"])
        self._source_dialog = dialog
        self._sync_button()
        dialog.finished.connect(self._photoshop_source_chosen)
        dialog.open()
        dialog.raise_()
        dialog.activateWindow()
        self._trace("photoshop_picker_visible", str(dialog.isVisible()))

    def _photoshop_source_chosen(self, result):
        dialog = self._source_dialog
        if dialog is None:
            return
        self._source_dialog = None
        paths = dialog.selectedFiles()
        dialog.deleteLater()
        if self._closing:
            return
        self._sync_button()
        if self._process is None:
            # The mapper window closed while the picker was open; its connection
            # request ended with it.
            return
        if result != self.QtWidgets.QDialog.DialogCode.Accepted or not paths:
            self._trace("photoshop_picker_cancelled")
            self._reply_to_desktop({"type": "photoshop_connect_cancelled"})
            return
        source_path = Path(paths[0])
        self._trace("photoshop_source_selected", source_path.suffix)
        settings = self.QtCore.QSettings(SETTINGS_ORG, SETTINGS_APP)
        settings.setValue(PHOTOSHOP_DIR_KEY, str(source_path.parent))
        settings.sync()
        self._start_photoshop_document_export(source_path)

    def _remember_photoshop_manifest(self, path):
        settings = self.QtCore.QSettings(SETTINGS_ORG, SETTINGS_APP)
        # The picker's start folder stays where the user's PSD lives; the
        # manifest itself sits in an internal session folder.
        settings.setValue(MANIFEST_PATH_KEY, str(path))
        settings.sync()

    def _photoshop_connected(self, manifest_path):
        self._remember_photoshop_manifest(manifest_path)
        self._reply_to_desktop(
            {"type": "photoshop_connected", "manifest": str(manifest_path)}
        )

    def _reply_to_desktop(self, payload):
        # The mapper stays open while Painter connects Photoshop, so replies go
        # to its stdin instead of relaunching it with a new session.
        process = self._process
        if process is None:
            return
        self._trace("desktop_reply", payload.get("type", ""))
        process.write((json.dumps(payload) + "\n").encode("utf-8"))

    def _start_photoshop_document_export(self, source_path):
        try:
            session_root = (
                exporter.default_output_dir(self.panel.user_settings)
                / "_desktop_bridge"
                / "photoshop_documents"
            )
            output_dir = _photoshop_document_session_dir(session_root, source_path)
            launch = photoshop_automation.write_photoshop_document_launcher(
                source_path,
                output_dir,
            )
        except Exception as exc:
            self._photoshop_job_failed(str(exc))
            return

        self._start_photoshop_job(launch, source_path.name)

    def _start_photoshop_job(self, launch, label, transfer_result=None):
        self._clear_photoshop_export()
        self._photoshop_launch = launch
        self._pending_transfer_result = transfer_result
        self._photoshop_export_started_at = time.monotonic()
        self._show_photoshop_progress(label)
        try:
            launched, message = self.panel.launch_photoshop(launch.launcher_path)
        except Exception as exc:
            self._photoshop_job_failed(str(exc))
            return
        if not launched:
            self._photoshop_job_failed(message)
            return

        # Process launch only acknowledges the OS handoff. Require a JSX receipt
        # before treating Photoshop as connected, even if its window is visible.
        self._trace("photoshop_launch_requested", str(launch.launcher_path))
        timer = self.QtCore.QTimer(self.panel.widget)
        timer.setInterval(400)
        timer.timeout.connect(self._poll_photoshop_job)
        self._photoshop_export_timer = timer
        self._sync_button()
        timer.start()

    def _show_photoshop_progress(self, name):
        # Only Painter reads the script's progress receipts, so Painter shows the
        # layer count; the dock label is hidden and not sufficient feedback.
        dialog = self.QtWidgets.QProgressDialog(self.panel.widget.window())
        dialog.setWindowTitle("PT Bridge - Photoshop")
        dialog.setWindowModality(self.QtCore.Qt.WindowModality.NonModal)
        dialog.setWindowFlag(self.QtCore.Qt.WindowType.WindowCloseButtonHint, False)
        dialog.setCancelButton(None)
        dialog.setAutoClose(False)
        dialog.setAutoReset(False)
        dialog.setMinimumDuration(0)
        dialog.setMinimumWidth(360)
        dialog.setRange(0, 0)
        dialog.setLabelText(f"Opening Photoshop...\n{name}")
        label = dialog.findChild(self.QtWidgets.QLabel)
        label.setTextFormat(self.QtCore.Qt.TextFormat.PlainText)
        label.setWordWrap(True)
        self._photoshop_progress_dialog = dialog
        dialog.show()
        dialog.raise_()

    def _update_photoshop_progress(self, path):
        try:
            payload = json.loads(path.read_text(encoding="utf-8-sig"))
        except (OSError, ValueError):
            return
        if not isinstance(payload, dict):
            return
        phase = payload.get("phase")
        if phase not in {"reading_request", "opening_document", "exporting_layers", "transferring_layers", "saving_document"}:
            return
        self._photoshop_script_started = True
        if phase != self._photoshop_export_phase:
            self._trace("photoshop_progress", phase)
            self._photoshop_export_phase = phase
        dialog = self._photoshop_progress_dialog
        if dialog is None:
            return
        total = payload.get("total", 0)
        completed = payload.get("completed", 0)
        if not isinstance(total, int) or not isinstance(completed, int):
            return
        if phase in {"exporting_layers", "transferring_layers"} and total > 0:
            dialog.setRange(0, total)
            dialog.setValue(max(0, min(completed, total)))
            action = "Reading" if phase == "exporting_layers" else "Inserting"
            message = f"{action} Photoshop layers: {completed} / {total}"
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
        if transfer is not None:
            # A cross-host operation is not atomic. Never retry Painter edits
            # because Photoshop failed, or claim both hosts rolled back together.
            if transfer.imported_count:
                message = f"Already imported {transfer.imported_count} layer(s) into Painter.\n\n{message}"
            self._show("Bridge transfer incomplete", message)
            return
        if self._process is not None:
            self._reply_to_desktop({"type": "photoshop_connect_failed", "message": message})
        else:
            self._show("Bridge", message)

    def _poll_photoshop_job(self):
        launch = self._photoshop_launch
        if launch is None:
            return
        elapsed = time.monotonic() - self._photoshop_export_started_at
        if not launch.result_path.is_file():
            self._update_photoshop_progress(launch.progress_path)
            if not self._photoshop_script_started and elapsed > PHOTOSHOP_START_TIMEOUT_SECONDS:
                self._photoshop_job_failed(
                    "Photoshop did not start the script within 2 minutes. "
                    "Check Photoshop for a startup or script confirmation dialog."
                )
            elif elapsed > PHOTOSHOP_EXPORT_TIMEOUT_SECONDS:
                self._photoshop_job_failed(
                    "Photoshop did not finish the operation within 30 minutes."
                )
            return
        try:
            payload = json.loads(launch.result_path.read_text(encoding="utf-8-sig"))
        except (OSError, ValueError) as exc:
            # JSX publishes with rename; a malformed published receipt is a
            # terminal failure, not a partially written file to wait on forever.
            self._photoshop_job_failed(f"Photoshop result could not be read: {exc}")
            return

        if self._pending_transfer_result is not None:
            self._finish_photoshop_transfer(payload)
            return
        if not isinstance(payload, dict) or payload.get("success") is not True:
            self._photoshop_job_failed(_photoshop_export_error_summary(payload))
            return
        manifest_path = Path(payload.get("manifest") or launch.manifest_path)
        try:
            _validate_photoshop_manifest(manifest_path)
        except Exception as exc:
            self._photoshop_job_failed(str(exc))
            return

        self._trace("photoshop_document_ready", str(payload.get("exported_count", 0)))
        self._clear_photoshop_export()
        self._photoshop_connected(manifest_path)

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
        timer = self._photoshop_export_timer
        self._photoshop_export_timer = None
        self._photoshop_launch = None
        self._pending_transfer_result = None
        self._photoshop_export_started_at = 0.0
        self._photoshop_script_started = False
        self._photoshop_export_phase = None
        dialog = self._photoshop_progress_dialog
        self._photoshop_progress_dialog = None
        if dialog is not None:
            dialog.close()
            dialog.deleteLater()
        if timer is not None:
            timer.stop()
            timer.deleteLater()
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
        if self._source_dialog is not None:
            # The picker answers this mapper's request; it cannot outlive it.
            self._source_dialog.close()
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
            self._source_dialog = None
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
        if self._source_dialog is not None or self._photoshop_launch is not None:
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


def _validate_photoshop_manifest(path):
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except OSError as exc:
        raise RuntimeError(f"Could not read Photoshop selection: {path}") from exc
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Photoshop selection is not valid JSON: {path}") from exc
    if not isinstance(payload, dict):
        raise RuntimeError("Photoshop selection manifest must be a JSON object.")
    if payload.get("schema_version") != 1:
        raise RuntimeError("Photoshop selection uses an unsupported schema_version.")
    if payload.get("request_type") != "photoshop_selection":
        raise RuntimeError("Selected JSON file is not a Photoshop selection manifest.")
    if not isinstance(payload.get("layers"), list) or not payload["layers"]:
        raise RuntimeError("Photoshop selection manifest contains no exported layers.")


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


def _photoshop_document_session_dir(root, source_path):
    source = Path(source_path).resolve()
    safe_stem = re.sub(r"[^A-Za-z0-9._-]+", "_", source.stem).strip("._")
    if not safe_stem:
        safe_stem = "photoshop_document"
    identity = hashlib.sha256(str(source).casefold().encode("utf-8")).hexdigest()[:10]
    return Path(root) / f"{safe_stem}-{identity}"


def _photoshop_export_error_summary(payload):
    if not isinstance(payload, dict):
        return "Photoshop returned an invalid document export result."
    errors = payload.get("errors")
    if not isinstance(errors, list) or not errors:
        return "Photoshop did not create a usable layer manifest."
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
