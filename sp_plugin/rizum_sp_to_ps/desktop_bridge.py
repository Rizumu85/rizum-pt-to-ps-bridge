"""Painter-owned lifecycle for the native PT Bridge mapper."""

from __future__ import annotations

import codecs
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from . import desktop_transfer, exporter
from .mapper_process import mapper_process_class
from .photoshop_documents import SETTINGS_KEY as PHOTOSHOP_DOCUMENTS_KEY, DocumentMemory
from .photoshop_job import PhotoshopJob
from .ui_dialogs import CompactProgressDialog


SETTINGS_ORG = "Rizum"
SETTINGS_APP = "PTBridge"
PHOTOSHOP_DIR_KEY = "photoshop_document_dir"
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
        self._snapshot_path = None
        self._documents_path = None
        self._project_key = None
        self._connect_context = {}
        self._closing = False
        self._applying_transfer = False
        self._photoshop_job = None
        self._pending_transfer_result = None
        self._photoshop_progress_dialog = None
        self._photoshop_phase = None
        self._picking = False
        self._trace_path = None
        self._stdout_buffer = ""
        self._stdout_decoder = None

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
        if process is not None:
            process.stop()

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

        self._launch_desktop()

    def _launch_desktop(self):
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
            self._snapshot_path = snapshot_path
            self._documents_path = session_dir / "photoshop_documents.json"
            self._write_document_map()
        except Exception as exc:
            self._show("Bridge", str(exc))
            return

        self._stdout_buffer = ""
        self._stdout_decoder = codecs.getincrementaldecoder("utf-8")(errors="replace")
        arguments = [
            "--painter",
            str(snapshot_path),
            "--documents",
            str(self._documents_path),
            "--output",
            str(transfer_path),
        ]
        process = mapper_process_class(self.QtCore)(executable, arguments)
        # Each signal names its process, so a late one from a closed session
        # cannot reach the mapper that replaced it.
        process.output.connect(lambda chunk, owner=process: self._desktop_output(owner, chunk))
        process.finished.connect(
            lambda code, stderr, owner=process: self._desktop_finished(owner, code, stderr)
        )
        try:
            process.start()
        except OSError as exc:
            self._show("Bridge", f"Could not start PT Bridge desktop.\n\n{exc}")
            return
        self._trace("desktop_started")
        self._process = process
        self._sync_button()

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

    def _document_memory(self):
        settings = self.QtCore.QSettings(SETTINGS_ORG, SETTINGS_APP)
        return DocumentMemory(settings.value(PHOTOSHOP_DOCUMENTS_KEY, "", str) or "")

    def _write_document_map(self):
        """Tell the mapper which PSD each Painter context in its snapshot uses."""
        snapshot = json.loads(self._snapshot_path.read_text(encoding="utf-8"))
        project = snapshot.get("project") or {}
        self._project_key = project.get("uuid") or project.get("path") or "unsaved"
        memory = self._document_memory()
        documents = []
        for context in snapshot.get("contexts") or []:
            psd = memory.resolve(
                self._project_key, context.get("texture_set"), context.get("stack") or "", context.get("channel"),
            )
            documents.append({
                "texture_set": context.get("texture_set"),
                "stack": context.get("stack") or "",
                "channel": context.get("channel"),
                "psd": psd,
            })
        exporter.write_json_atomic(self._documents_path, {"schema_version": 1, "documents": documents})

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
        context = self._connect_context
        memory = self._document_memory()
        memory.remember(
            self._project_key,
            context.get("texture_set"),
            context.get("stack") or "",
            context.get("channel"),
            str(source_path),
        )
        settings = self.QtCore.QSettings(SETTINGS_ORG, SETTINGS_APP)
        settings.setValue(PHOTOSHOP_DIR_KEY, str(source_path.parent))
        settings.setValue(PHOTOSHOP_DOCUMENTS_KEY, memory.dumps())
        settings.sync()
        # The mapper reads the PSD itself, so connecting never starts Photoshop.
        # The refreshed map tells it which of its other contexts share this PSD.
        self._write_document_map()
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
        self._apply_progress({"message": "Opening Photoshop document..."})
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
        if not isinstance(total, int) or not isinstance(completed, int):
            return
        if phase == "transferring_layers" and total > 0:
            if dialog is not None:
                dialog.setRange(0, total)
                dialog.setValue(max(0, min(completed, total)))
            message = f"Inserting Photoshop layers: {completed} / {total}"
        elif phase == "saving_document":
            message = "Saving Photoshop document..."
        else:
            message = "Opening Photoshop document..."
        if dialog is not None:
            if phase != "transferring_layers" or total <= 0:
                dialog.setRange(0, 0)
            dialog.setLabelText(message)
        self._apply_progress({"message": message, **(
            {"completed": completed, "total": total} if phase == "transferring_layers" and total > 0 else {}
        )})

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
        self._finish_apply("apply_failed", message)

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
        self._finish_apply("applied", message)

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

    def _desktop_finished(self, process, exit_code, stderr):
        # Unload can deliver a final signal after the dock is disposed. close()
        # owns that cleanup; an exiting child must not touch the old UI.
        if self._closing or process is not self._process:
            return
        self._trace("desktop_finished", str(exit_code))
        self._take_process()
        # Apply arrives as a request while the mapper is open, so an exit only
        # means the user closed the window; nothing is applied on the way out.
        if int(exit_code) != 0:
            self._show("Bridge", stderr or f"Desktop process exited with code {exit_code}.")

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

    def _desktop_output(self, process, chunk):
        if process is not self._process:
            return
        self._stdout_buffer += self._stdout_decoder.decode(bytes(chunk))
        *lines, self._stdout_buffer = self._stdout_buffer.split("\n")
        for line in lines:
            line = line.strip()
            if line.startswith(DESKTOP_REQUEST_MARKER):
                self._desktop_request(line[len(DESKTOP_REQUEST_MARKER):])
            elif line:
                self._trace("desktop", line)

    def _desktop_request(self, text):
        try:
            request = json.loads(text)
            request_type = request.get("type")
        except (ValueError, AttributeError):
            request, request_type = {}, None
        self._trace("desktop_request", str(request_type))
        if self._picking or self._photoshop_job is not None or self._applying_transfer:
            self._reply_to_desktop({"type": "failed", "message": "Painter is still busy with the last request."})
            return
        # Leave the stdout signal before opening a modal owner or editing Painter.
        if request_type == "connect_photoshop":
            # The PSD is remembered for the Painter target the mapper shows.
            self._connect_context = {
                key: request.get(key) for key in ("texture_set", "stack", "channel")
            }
            self.QtCore.QTimer.singleShot(0, self._open_photoshop_picker)
        elif request_type == "apply" and request.get("manifest"):
            manifest = Path(request["manifest"])
            self.QtCore.QTimer.singleShot(0, lambda: self._apply_desktop_transfer(manifest))
        else:
            self._reply_to_desktop({
                "type": "failed",
                "message": f"Unsupported desktop request: {request_type or '(missing)'}",
            })

    def _apply_desktop_transfer(self, manifest_path):
        if self._closing:
            return
        self._applying_transfer = True
        self._sync_button()
        try:
            self._apply_progress({"message": "Preparing Painter transfer..."})
            result = desktop_transfer.apply_transfer_manifest(
                manifest_path,
                settings=self.panel.user_settings,
                progress_callback=self._apply_progress,
            )
        except Exception as exc:
            self._finish_apply("apply_failed", str(exc))
            return
        finally:
            self._applying_transfer = False
            self._sync_button()
        if result.photoshop_launch is not None:
            self._start_photoshop_job(
                result.photoshop_launch, f"Insert {result.exported_count} layer(s)", result,
            )
        else:
            self._report_transfer_complete(result.imported_count, 0, result.warnings)

    def _apply_progress(self, payload):
        process = self._process
        if process is None:
            return
        # The pipe write is synchronous, so progress reaches the mapper while
        # Painter keeps working on its own thread and no Qt events are pumped
        # into a partially applied transfer.
        process.write((json.dumps({**payload, "type": "apply_progress"}) + "\n").encode("utf-8"))

    def _finish_apply(self, reply_type, message):
        """Report an Apply to the open mapper with a fresh Painter snapshot."""
        if self._process is None:
            # The mapper was closed while Photoshop worked; Painter is the only
            # place left to report the outcome.
            title = "Bridge complete" if reply_type == "applied" else "Bridge transfer incomplete"
            self._show(title, message)
            return
        reply = {"type": reply_type, "message": message}
        try:
            self._apply_progress({"message": "Refreshing Painter layers..."})
            # The mapper stays open after Apply, so it needs Painter's new
            # layer tree to keep mapping against what is really there now.
            exporter.write_painter_snapshot(self._snapshot_path, self.panel.user_settings)
            self._write_document_map()
            reply["snapshot"] = str(self._snapshot_path)
        except Exception as exc:
            reply["message"] = f"{message}\n\nPainter layers could not be refreshed: {exc}"
        self._reply_to_desktop(reply)

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
