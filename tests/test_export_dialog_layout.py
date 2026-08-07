from __future__ import annotations

import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6 import QtCore, QtGui, QtTest, QtWidgets

from sp_plugin.rizum_sp_to_ps.ui import ExportDialog


class _Panel:
    QtCore = QtCore
    QtGui = QtGui
    QtWidgets = QtWidgets

    def __init__(self):
        self.widget = QtWidgets.QWidget()

    def active_target_key(self):
        return ("M_body", "")


def _targets():
    return [
        {
            "texture_set": name,
            "stack": "",
            "channels": channels,
            "channel_labels": {channel: channel for channel in channels},
        }
        for name, channels in (
            ("M_body", ["basecolor"]),
            ("M_clothes", ["basecolor"]),
            ("M_coat", ["basecolor", "normal"]),
            ("M_face", ["basecolor", "normal"]),
        )
    ]


class ExportDialogLayoutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
        cls.app.setProperty("rizumUiFontScale", 1.1)

    def setUp(self):
        self.export = ExportDialog(_Panel())
        self.export.targets = _targets()
        self.export.refresh_tree()
        self.export.dialog.show()
        self.app.processEvents()

    def tearDown(self):
        self.export.dialog.close()
        self.export.dialog.deleteLater()
        self.app.processEvents()

    def test_scope_switch_keeps_the_scrollbar_gutter_stable(self):
        scrollbar = self.export.tree_scrollbar
        current_width = self.export.tree_scroll.viewport().width()
        current_height = self.export.dialog.height()

        self.assertEqual(
            self.export.tree_scroll.verticalScrollBar().width(),
            0,
        )
        self.assertTrue(scrollbar.isVisible())
        self.assertTrue(scrollbar.isEnabled())
        self.assertFalse(scrollbar.property("scrollable"))
        top_margins = self.export.top_controls.layout().contentsMargins()
        self.assertEqual(
            top_margins.right() - top_margins.left(),
            scrollbar.width(),
        )

        self.export.scope_combo.setCurrentIndex(1)
        self.app.processEvents()
        self.assertIsNotNone(self.export._height_animation)
        self.assertEqual(self.export.tree_scroll.viewport().width(), current_width)
        self.assertTrue(scrollbar.isEnabled())
        self.assertTrue(scrollbar.property("scrollable"))

        QtTest.QTest.qWait(220)
        self.app.processEvents()
        all_height = self.export.dialog.height()
        self.assertGreater(all_height, current_height)
        self.assertGreater(scrollbar.maximum(), 0)
        self.assertEqual(self.export.tree_scroll.viewport().width(), current_width)

        self.export.scope_combo.setCurrentIndex(0)
        QtTest.QTest.qWait(220)
        self.app.processEvents()
        self.assertEqual(self.export.dialog.height(), current_height)
        self.assertEqual(self.export.tree_scroll.viewport().width(), current_width)
        self.assertTrue(scrollbar.isEnabled())
        self.assertFalse(scrollbar.property("scrollable"))

    def test_all_stacks_height_stops_before_the_next_group(self):
        self.export.scope_combo.setCurrentIndex(1)
        QtTest.QTest.qWait(220)
        self.app.processEvents()

        viewport_height = self.export.tree_scroll.viewport().height()
        next_group_y = self.export.groups[3]["widget"].y()
        self.assertLessEqual(viewport_height, next_group_y)

    def test_rapid_scope_reversal_finishes_at_the_latest_height(self):
        current_height = self.export.dialog.height()
        current_width = self.export.tree_scroll.viewport().width()

        self.export.scope_combo.setCurrentIndex(1)
        QtTest.QTest.qWait(60)
        self.export.scope_combo.setCurrentIndex(0)
        QtTest.QTest.qWait(220)
        self.app.processEvents()

        self.assertIsNone(self.export._height_animation)
        self.assertEqual(self.export.dialog.height(), current_height)
        self.assertEqual(self.export.tree_scroll.viewport().width(), current_width)


if __name__ == "__main__":
    unittest.main()
