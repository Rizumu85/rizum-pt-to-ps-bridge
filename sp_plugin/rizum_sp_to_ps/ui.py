"""Painter UI registration for Rizum PT-to-PS Bridge."""

from __future__ import annotations

from pathlib import Path

from .exporter import write_build_bundles
from .sync_inbox import (
    apply_latest_push_manifest,
    format_apply_summary,
    format_scan_summary,
    scan_current_project_inbox,
)

PLUGIN_ROOT = Path(__file__).resolve().parents[2]
SMOKE_TEST_DIR = PLUGIN_ROOT / "_rizum_m1_test"
_ACTIVE_PANEL = None


class SmokeTestPanel:
    """Small M1 validation panel, intentionally separate from final export UI."""

    def __init__(self):
        from PySide6 import QtCore, QtWidgets

        self.QtCore = QtCore
        self.QtWidgets = QtWidgets
        self._running = False
        self.widget = QtWidgets.QWidget()
        self.widget.setObjectName("RizumPtToPsSmokeTestPanel")
        self.widget.setWindowTitle("Rizum PT-to-PS")

        layout = QtWidgets.QVBoxLayout(self.widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        self.export_pngs = QtWidgets.QCheckBox("Export PNGs")
        self.export_pngs.setChecked(True)
        self.export_pngs.setToolTip(
            "Unchecked writes JSON-only build bundles. Checked also exports PNGs."
        )

        self.run_button = QtWidgets.QPushButton("Run M1 Smoke Test")
        self.run_button.clicked.connect(self.run_smoke_test)

        self.scan_inbox_button = QtWidgets.QPushButton("Scan PS Inbox")
        self.scan_inbox_button.clicked.connect(self.scan_ps_inbox)

        self.apply_inbox_button = QtWidgets.QPushButton("Validate PS Inbox")
        self.apply_inbox_button.clicked.connect(self.apply_ps_inbox)

        self.status = QtWidgets.QLabel("Ready")
        self.status.setWordWrap(True)

        self.output = QtWidgets.QPlainTextEdit()
        self.output.setReadOnly(True)
        self.output.setMinimumHeight(120)
        self.output.setPlainText(f"Output folder:\n{SMOKE_TEST_DIR}")

        layout.addWidget(self.export_pngs)
        layout.addWidget(self.run_button)
        layout.addWidget(self.scan_inbox_button)
        layout.addWidget(self.apply_inbox_button)
        layout.addWidget(self.status)
        layout.addWidget(self.output)
        layout.addStretch(1)

        self.project_timer = QtCore.QTimer(self.widget)
        self.project_timer.setInterval(1000)
        self.project_timer.timeout.connect(self.refresh_project_state)
        self.project_timer.start()
        self.refresh_project_state()

    def close(self):
        """Stop owned Qt helpers before Painter removes the dock."""
        self.project_timer.stop()

    def refresh_project_state(self):
        """Keep the panel usable when Painter starts without a project."""
        if self._running:
            return

        if self._project_is_open():
            self.run_button.setEnabled(True)
            self.scan_inbox_button.setEnabled(True)
            self.apply_inbox_button.setEnabled(True)
            if self.status.text().startswith("Open a Painter project"):
                self.status.setText("Ready")
            return

        self.run_button.setEnabled(False)
        self.scan_inbox_button.setEnabled(False)
        self.apply_inbox_button.setEnabled(False)
        self.status.setText("Open a Painter project to run the M1 smoke test.")

    def _project_is_open(self):
        try:
            import substance_painter.project

            return substance_painter.project.is_open()
        except Exception:
            return False

    def run_smoke_test(self):
        if not self._project_is_open():
            self.status.setText("Open a Painter project to run the M1 smoke test.")
            return

        export_pngs = self.export_pngs.isChecked()
        self._running = True
        self.run_button.setEnabled(False)
        self.status.setText("Running M1 smoke test...")
        self.QtWidgets.QApplication.processEvents()

        try:
            paths = write_build_bundles(
                SMOKE_TEST_DIR,
                settings={
                    "normal_map_format": "OpenGL",
                    "infinite_padding": False,
                    "keep_alpha": True,
                },
                export_pngs=export_pngs,
            )
        except Exception as exc:  # noqa: BLE001 - show host errors to the user.
            self.status.setText("M1 smoke test failed.")
            self.output.setPlainText(f"{type(exc).__name__}: {exc}")
        else:
            mode = "JSON + PNG" if export_pngs else "JSON-only"
            self.status.setText(f"M1 smoke test passed ({mode}).")
            lines = [f"Wrote {len(paths)} build request(s):"]
            lines.extend(str(path) for path in paths)
            self.output.setPlainText("\n".join(lines))
        finally:
            self._running = False
            self.run_button.setEnabled(True)
            self.refresh_project_state()

    def scan_ps_inbox(self):
        if not self._project_is_open():
            self.status.setText("Open a Painter project to scan the PS inbox.")
            return

        self.status.setText("Scanning PS inbox...")
        self.QtWidgets.QApplication.processEvents()

        try:
            scan = scan_current_project_inbox()
        except Exception as exc:  # noqa: BLE001 - show host errors to the user.
            self.status.setText("PS inbox scan failed.")
            self.output.setPlainText(f"{type(exc).__name__}: {exc}")
            return

        self.status.setText(
            f"PS inbox scan found {scan['manifest_count']} manifest(s)."
        )
        self.output.setPlainText(format_scan_summary(scan))

    def apply_ps_inbox(self):
        if not self._project_is_open():
            self.status.setText("Open a Painter project to validate the PS inbox.")
            return

        self.status.setText("Validating latest PS inbox...")
        self.QtWidgets.QApplication.processEvents()

        try:
            result = apply_latest_push_manifest()
        except Exception as exc:  # noqa: BLE001 - show host errors to the user.
            self.status.setText("PS inbox apply failed.")
            self.output.setPlainText(f"{type(exc).__name__}: {exc}")
            return

        self.status.setText(result["reason"])
        self.output.setPlainText(format_apply_summary(result))


def register():
    """Register Painter UI elements and return handles for cleanup."""
    import substance_painter as sp

    global _ACTIVE_PANEL
    panel = SmokeTestPanel()
    _ACTIVE_PANEL = panel
    dock = sp.ui.add_dock_widget(panel.widget)
    dock.setWindowTitle("Rizum PT-to-PS")
    dock.show()
    dock.raise_()
    sp.logging.info("Rizum PT-to-PS Painter plugin loaded")
    return [dock]


def unregister(handles):
    """Remove Painter UI elements registered by this plugin."""
    import substance_painter as sp

    global _ACTIVE_PANEL
    if _ACTIVE_PANEL is not None:
        _ACTIVE_PANEL.close()
        _ACTIVE_PANEL = None

    for handle in handles:
        sp.ui.delete_ui_element(handle)
    handles.clear()
    sp.logging.info("Rizum PT-to-PS Painter plugin unloaded")
