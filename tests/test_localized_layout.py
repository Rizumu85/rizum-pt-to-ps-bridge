from __future__ import annotations

import os
import unittest
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6 import QtCore, QtGui, QtWidgets

from sp_plugin.rizum_sp_to_ps import localization, ui
from sp_plugin.rizum_sp_to_ps.export_ui import ExportDialog
from sp_plugin.rizum_sp_to_ps.settings_ui import SettingsDialog


SCALES = (1.0, 1.5)


class _Panel:
    QtCore = QtCore
    QtGui = QtGui
    QtWidgets = QtWidgets

    def __init__(self):
        self.widget = QtWidgets.QWidget()
        # Not the first item of each combo, so the widest caption is not the
        # one showing when the shared combo width is measured.
        self.user_settings = {"bit_depth": 8, "psd_size": 2048, "render_scale": 2}

    def active_target_key(self):
        return ("M_body", "")

    def photoshop_executable(self):
        return None

    def save_user_settings(self, values):
        self.user_settings = dict(values)


class LocalizedLayoutTests(unittest.TestCase):
    """Translated captions are longer than English; none of them may clip."""

    @classmethod
    def setUpClass(cls):
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def setUp(self):
        self.addCleanup(self.app.setProperty, "rizumUiFontScale", self.app.property("rizumUiFontScale"))

    def in_every_language(self, check):
        for scale in SCALES:
            self.app.setProperty("rizumUiFontScale", scale)
            for language in localization.supported_languages():
                with (
                    self.subTest(language=language, scale=scale),
                    mock.patch.object(localization, "CURRENT_LANGUAGE", language),
                ):
                    check(scale)

    def settle(self):
        # A changed caption reaches its row's layout over several event passes.
        for _ in range(6):
            self.app.processEvents()

    def show(self, widget):
        widget.show()
        self.addCleanup(widget.deleteLater)
        self.addCleanup(widget.close)
        self.settle()

    def assertLabelFits(self, label):
        needed = label.fontMetrics().horizontalAdvance(label.text())
        self.assertLessEqual(needed, label.contentsRect().width() + 1, label.text())

    def assertInsideParent(self, widget):
        self.assertGreaterEqual(widget.geometry().left(), 0)
        self.assertLessEqual(widget.geometry().right(), widget.parentWidget().width())

    def test_settings_rows_fit_every_subtitle_and_combo_caption(self):
        def check(_scale):
            settings = SettingsDialog(_Panel())
            self.show(settings.dialog)
            width = settings.dialog.width()

            for infinite in (True, False):
                settings.infinite_padding.setChecked(infinite)
                settings._sync_padding_mode(animate=False)
                self.settle()
                self.assertLabelFits(settings.padding_meta)
            for strength in (0, 100):
                settings.smoothing_slider.setValue(strength)
                self.settle()
                self.assertLabelFits(settings.smoothing_meta)
            self.assertLabelFits(settings.render_texts._rizum_meta_label)
            for index in range(len(settings.blend_modes._items)):
                settings.blend_modes.setCurrentIndex(index)
                self.settle()
                self.assertLabelFits(settings.blend_modes_texts._rizum_meta_label)

            for combo in (settings.bit_depth, settings.psd_size, settings.render_scale, settings.blend_modes):
                self.assertInsideParent(combo)
                metrics = combo._label.fontMetrics()
                for caption, _value in combo._items:
                    self.assertLessEqual(
                        metrics.horizontalAdvance(caption),
                        combo._label.contentsRect().width() + 1,
                        caption,
                    )
            # Sized for every subtitle up front: the dialog must not change
            # width while a setting changes.
            self.assertEqual(settings.dialog.width(), width)

        self.in_every_language(check)

    def test_export_size_row_fits_its_captions(self):
        def check(_scale):
            export = ExportDialog(_Panel())
            export.targets = [
                {"texture_set": "M_body", "stack": "", "channels": ["BaseColor"], "channel_labels": {}},
            ]
            export.refresh_tree()
            self.show(export.dialog)

            for label in (export.psd_size_label, export.render_scale_label):
                self.assertLabelFits(label)
            for control in (export.psd_size_combo, export.render_scale_combo):
                self.assertInsideParent(control)

        self.in_every_language(check)

    def test_dock_buttons_are_never_narrower_than_their_captions(self):
        def check(scale):
            toolbar = ui._make_bridge_dock_toolbar(QtCore, QtWidgets)
            toolbar.setUiScale(scale)
            toolbar.resize(toolbar.minimumWidth(), toolbar.height())
            self.show(toolbar)

            export_button, bridge_button, _settings_button = toolbar.actionButtons()
            for button in (export_button, bridge_button):
                self.assertGreaterEqual(button.width(), button.sizeHint().width(), button.text())

        self.in_every_language(check)


if __name__ == "__main__":
    unittest.main()
