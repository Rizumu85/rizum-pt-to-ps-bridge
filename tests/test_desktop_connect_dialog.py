import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from PySide6 import QtCore, QtWidgets

from sp_plugin.rizum_sp_to_ps.desktop_bridge import DesktopBridgeController
from sp_plugin.rizum_sp_to_ps.desktop_transfer import TransferResult
from sp_plugin.rizum_sp_to_ps.photoshop_automation import write_photoshop_transfer_launcher


class DesktopConnectDialogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.settings = QtCore.QSettings(
            str(Path(self.directory.name) / "settings.ini"), QtCore.QSettings.Format.IniFormat
        )
        self.widget = QtWidgets.QWidget()
        self.panel = SimpleNamespace(
            QtCore=SimpleNamespace(QSettings=lambda *_: self.settings, QTimer=QtCore.QTimer, Qt=QtCore.Qt),
            QtWidgets=QtWidgets, widget=self.widget,
            dock_bridge_button=QtWidgets.QPushButton(self.widget),
            status=QtWidgets.QLabel(self.widget),
            user_settings={}, launch_photoshop=Mock(return_value=(True, "")),
        )
        self.controller = DesktopBridgeController(self.panel, Mock())
        self.controller._launch_desktop = Mock()
        self.controller._start_photoshop_document_export = Mock()

    def begin_export(self):
        root = Path(self.directory.name)
        source = root / "artwork.psd"
        source.touch()
        with patch("sp_plugin.rizum_sp_to_ps.desktop_bridge.exporter.default_output_dir", return_value=root):
            DesktopBridgeController._start_photoshop_document_export(self.controller, source)
        return self.controller._photoshop_launch

    def test_pending_connection_has_visible_nonmodal_progress_and_blocks_duplicates(self):
        self.begin_export()
        progress = self.controller._photoshop_progress_dialog
        self.assertTrue(progress.isVisible())
        self.assertFalse(progress.isModal())
        self.assertEqual(progress.maximum(), 0)
        self.assertFalse(self.panel.dock_bridge_button.isEnabled())
        self.controller.open()
        self.controller._launch_desktop.assert_not_called()

    def test_script_progress_updates_layer_count_without_relaunching(self):
        launch = self.begin_export()
        launch.progress_path.write_text(json.dumps({
            "phase": "exporting_layers", "completed": 2, "total": 5,
        }), encoding="utf-8")
        self.controller._poll_photoshop_job()
        progress = self.controller._photoshop_progress_dialog
        self.assertEqual(progress.value(), 2)
        self.assertEqual(progress.maximum(), 5)
        self.assertIn("2 / 5", progress.labelText())
        self.assertTrue(self.controller._photoshop_script_started)
        self.controller._launch_desktop.assert_not_called()

    def test_missing_start_ack_times_out_and_restores_mapper(self):
        self.begin_export()
        progress = self.controller._photoshop_progress_dialog
        self.controller._photoshop_export_started_at -= 121
        self.controller._poll_photoshop_job()
        self.assertFalse(progress.isVisible())
        self.assertIsNone(self.controller._photoshop_launch)
        self.assertIsNone(self.controller._photoshop_export_timer)
        self.controller._launch_desktop.assert_called_once_with(None)
        self.assertIn("2 minutes", self.controller._show_message_callback.call_args.args[-1])

    def test_acknowledged_export_uses_long_timeout(self):
        launch = self.begin_export()
        launch.progress_path.write_text('{"phase":"opening_document"}', encoding="utf-8")
        self.controller._photoshop_export_started_at -= 121
        self.controller._poll_photoshop_job()
        self.controller._launch_desktop.assert_not_called()
        self.controller._photoshop_export_started_at -= 1800
        self.controller._poll_photoshop_job()
        self.controller._launch_desktop.assert_called_once_with(None)
        self.assertIn("30 minutes", self.controller._show_message_callback.call_args.args[-1])

    def test_failure_receipt_restores_mapper_with_actual_error(self):
        launch = self.begin_export()
        launch.result_path.write_text(json.dumps({
            "success": False, "errors": [{"layer": "PSD", "error": "Could not decode"}],
        }), encoding="utf-8")
        self.controller._poll_photoshop_job()
        self.controller._launch_desktop.assert_called_once_with(None)
        self.assertIn("Could not decode", self.controller._show_message_callback.call_args.args[-1])
        self.assertIsNone(self.controller._photoshop_progress_dialog)

    def test_corrupt_published_receipt_is_not_an_endless_wait(self):
        launch = self.begin_export()
        launch.result_path.write_text("not json", encoding="utf-8")
        self.controller._poll_photoshop_job()
        self.controller._launch_desktop.assert_called_once_with(None)
        self.assertIsNone(self.controller._photoshop_export_timer)

    def test_success_reopens_mapper_with_manifest_and_closes_progress(self):
        launch = self.begin_export()
        launch.manifest_path.write_text(json.dumps({
            "schema_version": 1, "request_type": "photoshop_selection", "layers": [{"png": "1.png"}],
        }), encoding="utf-8")
        launch.result_path.write_text('{"success":true,"exported_count":1}', encoding="utf-8")
        progress = self.controller._photoshop_progress_dialog
        self.controller._poll_photoshop_job()
        self.assertFalse(progress.isVisible())
        self.controller._launch_desktop.assert_called_once_with(launch.manifest_path)
        self.assertEqual(self.controller._recent_photoshop_manifest(), launch.manifest_path)
        self.controller._show_message_callback.assert_not_called()

    def test_launch_failure_cleans_progress_and_restores_mapper(self):
        self.panel.launch_photoshop.return_value = (False, "Photoshop unavailable")
        self.begin_export()
        self.assertIsNone(self.controller._photoshop_progress_dialog)
        self.assertIsNone(self.controller._photoshop_export_timer)
        self.controller._launch_desktop.assert_called_once_with(None)
        self.assertEqual(self.controller._show_message_callback.call_args.args[-1], "Photoshop unavailable")

    def test_unload_closes_pending_connection_without_relaunch(self):
        self.begin_export()
        progress = self.controller._photoshop_progress_dialog
        self.controller.close()
        self.assertFalse(progress.isVisible())
        self.assertIsNone(self.controller._photoshop_export_timer)
        self.controller._poll_photoshop_job()
        self.controller._launch_desktop.assert_not_called()

    def begin_transfer(self):
        request = Path(self.directory.name) / "photoshop_transfer.json"
        request.write_text("{}", encoding="utf-8")
        launch = write_photoshop_transfer_launcher(request)
        transfer = TransferResult(2, 3, (), (), launch)
        self.controller._start_photoshop_job(launch, "Insert 3 layers", transfer)
        return launch

    def test_apply_waits_for_photoshop_receipt_instead_of_reporting_launch_as_success(self):
        launch = self.begin_transfer()
        self.controller._poll_photoshop_job()
        self.controller._show_message_callback.assert_not_called()
        self.assertFalse(self.panel.dock_bridge_button.isEnabled())
        launch.result_path.write_text(json.dumps({
            "success": True, "inserted": ["A", "B", "C"], "saved": True,
        }), encoding="utf-8")
        self.controller._poll_photoshop_job()
        args = self.controller._show_message_callback.call_args.args
        self.assertEqual(args[-2], "Bridge complete")
        self.assertIn("Imported 2", args[-1])
        self.assertIn("inserted 3", args[-1])
        self.assertIsNone(self.controller._photoshop_progress_dialog)

    def test_desktop_apply_handoff_keeps_dock_busy_until_real_photoshop_result(self):
        root = Path(self.directory.name)
        transfer_path = root / "desktop_transfer.json"
        transfer_path.write_text('{"request_type":"desktop_transfer"}', encoding="utf-8")
        request_path = root / "photoshop_transfer.json"
        request_path.write_text("{}", encoding="utf-8")
        launch = write_photoshop_transfer_launcher(request_path)
        result = TransferResult(0, 1, (), (), launch)
        process = SimpleNamespace(readAllStandardOutput=lambda: b"", readAllStandardError=lambda: b"", deleteLater=Mock())
        self.controller._process = process
        self.controller._transfer_path = transfer_path
        def apply(*_args, **_kwargs):
            self.assertFalse(self.panel.dock_bridge_button.isEnabled())
            self.controller.open()
            self.controller._launch_desktop.assert_not_called()
            return result
        with patch("sp_plugin.rizum_sp_to_ps.desktop_bridge.desktop_transfer.apply_transfer_manifest", side_effect=apply):
            self.controller._desktop_finished(0, None)
        process.deleteLater.assert_called_once()
        self.controller._show_message_callback.assert_not_called()
        self.assertFalse(self.panel.dock_bridge_button.isEnabled())
        self.assertEqual(self.controller._photoshop_launch, launch)

    def test_partial_transfer_reports_both_hosts_without_reapplying_painter(self):
        launch = self.begin_transfer()
        launch.result_path.write_text(json.dumps({
            "success": False, "inserted": ["A"],
            "errors": [{"name": "B", "message": "Missing target"}],
        }), encoding="utf-8")
        self.controller._poll_photoshop_job()
        args = self.controller._show_message_callback.call_args.args
        self.assertEqual(args[-2], "Bridge transfer incomplete")
        self.assertIn("Already imported 2", args[-1])
        self.assertIn("Inserted 1 of 3", args[-1])
        self.assertIn("Missing target", args[-1])
        self.controller._launch_desktop.assert_not_called()

    def test_success_with_missing_inserts_is_not_reported_as_complete(self):
        launch = self.begin_transfer()
        launch.result_path.write_text('{"success":true,"inserted":[]}', encoding="utf-8")
        self.controller._poll_photoshop_job()
        self.assertEqual(self.controller._show_message_callback.call_args.args[-2], "Bridge transfer incomplete")

    def test_unsaved_photoshop_changes_are_reported_as_unsaved(self):
        launch = self.begin_transfer()
        launch.result_path.write_text(json.dumps({
            "success": True, "inserted": ["A", "B", "C"], "saved": False,
        }), encoding="utf-8")
        self.controller._poll_photoshop_job()
        self.assertIn("not been saved", self.controller._show_message_callback.call_args.args[-1])

    def tearDown(self):
        if not self.controller._closing:
            self.controller.close()
        self.widget.close()
        self.widget.deleteLater()
        self.app.processEvents()
        self.directory.cleanup()

    def test_cancel_reopens_bridge_and_releases_picker(self):
        self.controller._connect_photoshop()
        dialog = self.controller._source_dialog
        self.assertTrue(dialog.isVisible())
        self.assertFalse(self.panel.dock_bridge_button.isEnabled())
        dialog.reject()
        self.assertIsNone(self.controller._source_dialog)
        self.controller._launch_desktop.assert_called_once_with(None)
        self.assertTrue(self.panel.dock_bridge_button.isEnabled())

    def test_accept_psd_starts_export(self):
        source = Path(self.directory.name) / "external.psd"
        source.touch()
        self.controller._connect_photoshop()
        dialog = self.controller._source_dialog
        dialog.selectFile(str(source))
        dialog.accept()
        self.controller._start_photoshop_document_export.assert_called_once_with(source)
        self.assertIsNone(self.controller._source_dialog)

    def test_unload_closes_picker_without_relaunch(self):
        self.controller._connect_photoshop()
        self.controller.close()
        self.assertIsNone(self.controller._source_dialog)
        self.controller._launch_desktop.assert_not_called()
