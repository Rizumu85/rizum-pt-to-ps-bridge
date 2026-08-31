"""Painter-owned lifecycle for the native PT Bridge mapper."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from . import desktop_transfer, exporter


SETTINGS_ORG = "Rizum"
SETTINGS_APP = "PTBridge"
MANIFEST_DIR_KEY = "desktop_manifest_dir"


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

        self.button = panel.dock_bridge_button
        self.button.setEnabled(True)
        self.button.setToolTip("Map Photoshop layers into Painter")
        self.button.clicked.connect(self.open)

    def close(self):
        """Detach the controller and stop an owned desktop session on unload."""
        self._closing = True
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

    def open(self):
        """Choose a Photoshop selection and launch one native mapping session."""
        if self._process is not None:
            return
        if not self.panel._project_is_open():
            self._show("Bridge", "Open a Painter project before starting Bridge.")
            return
        if not self.panel._project_is_ready():
            self._show("Bridge", "Painter project is still loading or not editable.")
            return

        manifest_path = self._choose_photoshop_manifest()
        if manifest_path is None:
            return
        try:
            _validate_photoshop_manifest(manifest_path)
            executable = _desktop_executable()
            session_dir = exporter.default_output_dir(
                self.panel.user_settings
            ) / "_desktop_bridge"
            session_dir.mkdir(parents=True, exist_ok=True)
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
        process = self.QtCore.QProcess(self.panel.widget)
        process.setProgram(str(executable))
        process.setArguments(
            [
                "--session",
                str(manifest_path),
                "--painter",
                str(snapshot_path),
                "--output",
                str(transfer_path),
            ]
        )
        process.finished.connect(self._desktop_finished)
        process.errorOccurred.connect(self._desktop_error)
        self._process = process
        self.button.setEnabled(False)
        self.button.setToolTip("PT Bridge desktop is open")
        self.panel.status.setText("Mapping Photoshop layers in PT Bridge...")
        process.start()

    def _choose_photoshop_manifest(self):
        settings = self.QtCore.QSettings(SETTINGS_ORG, SETTINGS_APP)
        start_dir = settings.value(MANIFEST_DIR_KEY, "", str) or ""
        selected, _filter = self.QtWidgets.QFileDialog.getOpenFileName(
            self.panel.widget,
            "Select Photoshop Selection",
            start_dir,
            "Photoshop Selection (photoshop_selection.json);;JSON Files (*.json)",
        )
        if not selected:
            return None
        path = Path(selected)
        settings.setValue(MANIFEST_DIR_KEY, str(path.parent))
        settings.sync()
        return path

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
        self.panel.status.setText("PT Bridge desktop could not start.")
        self._show("Bridge", f"Could not start PT Bridge desktop.\n\n{detail}")

    def _desktop_finished(self, exit_code, _exit_status):
        process = self._take_process()
        if self._closing or process is None:
            return
        stderr = bytes(process.readAllStandardError()).decode(
            "utf-8",
            errors="replace",
        ).strip()
        if int(exit_code) != 0:
            detail = stderr or f"Desktop process exited with code {exit_code}."
            process.deleteLater()
            self.panel.status.setText("PT Bridge desktop failed.")
            self._show("Bridge", detail)
            return

        transfer_path = self._transfer_path
        if transfer_path is None or not transfer_path.is_file():
            process.deleteLater()
            self.panel.status.setText("Bridge mapping cancelled.")
            return

        try:
            result = desktop_transfer.apply_transfer_manifest(transfer_path)
        except Exception as exc:
            process.deleteLater()
            self.panel.status.setText("Bridge import failed.")
            self._show("Bridge", str(exc))
            return

        self.panel.status.setText(
            f"Imported {result.count} Photoshop layer(s) into Painter."
        )
        message = f"Imported {result.count} Photoshop layer(s) into Painter."
        if result.warnings:
            message += "\n\n" + "\n".join(result.warnings)
        process.deleteLater()
        self._show("Bridge complete", message)

    def _take_process(self):
        process = self._process
        self._process = None
        self.button.setEnabled(not self._closing)
        self.button.setToolTip("Map Photoshop layers into Painter")
        return process

    def _show(self, title, message):
        self._show_message_callback(
            self.QtWidgets,
            self.panel.widget,
            title,
            message,
        )


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
