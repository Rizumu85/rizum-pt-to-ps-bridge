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
            ("M_hair", ["basecolor", "roughness"]),
            ("M_shoes", ["basecolor", "normal"]),
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
        partial_groups = [
            group
            for group in self.export.groups
            if group["widget"].y() < viewport_height
            and group["widget"].y() + group["widget"].height() > viewport_height
        ]
        self.assertEqual(partial_groups, [])

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

    def test_collapsing_groups_removes_the_blank_scroll_range(self):
        self.export.scope_combo.setCurrentIndex(1)
        QtTest.QTest.qWait(220)
        self.app.processEvents()
        self.assertGreater(self.export.tree_scrollbar.maximum(), 0)

        self.export.tree_collapse_all()
        QtTest.QTest.qWait(350)
        self.app.processEvents()

        self.assertEqual(self.export.tree_scrollbar.maximum(), 0)
        self.assertEqual(
            self.export.tree_scroll.verticalScrollBar().maximum(),
            0,
        )

    def test_many_stacks_open_with_a_taller_complete_group_viewport(self):
        self.export.scope_combo.setCurrentIndex(1)
        QtTest.QTest.qWait(220)
        self.app.processEvents()

        self.assertGreater(
            self.export.tree_scroll.viewport().height(),
            self.export._metric(300, 225),
        )
        viewport_height = self.export.tree_scroll.viewport().height()
        partial_groups = [
            group
            for group in self.export.groups
            if group["widget"].y() < viewport_height
            and group["widget"].y() + group["widget"].height() > viewport_height
        ]
        self.assertEqual(partial_groups, [])

    def test_dialog_height_can_be_resized_by_the_user(self):
        initial_height = self.export.dialog.height()
        requested_height = initial_height + 80

        self.assertGreater(self.export.dialog.maximumHeight(), initial_height)
        self.export.dialog.resize(self.export.dialog.width(), requested_height)
        self.app.processEvents()

        self.assertEqual(self.export.dialog.height(), requested_height)
        self.assertGreater(self.export.tree_scroll.viewport().height(), 0)

    def test_export_action_uses_save_style_disabled_feedback(self):
        self.export.scope_combo.setCurrentIndex(1)
        QtTest.QTest.qWait(220)
        self.app.processEvents()

        self.assertFalse(self.export.run_button.isEnabled())
        self.assertEqual(self.export.run_button.activationProgress(), 0.0)

        self.export.set_all_checked(True)
        QtTest.QTest.qWait(220)
        self.app.processEvents()

        self.assertTrue(self.export.run_button.isEnabled())
        self.assertEqual(self.export.run_button.activationProgress(), 1.0)

    def test_child_hover_does_not_accumulate_across_rows(self):
        self.export.scope_combo.setCurrentIndex(1)
        QtTest.QTest.qWait(220)
        self.app.processEvents()
        children = self.export.groups[2]["children"][:2]
        first_filter = children[0]["row"]._rizum_hover_filter
        second_filter = children[1]["row"]._rizum_hover_filter

        first_filter.set_hovered(True)
        second_filter.set_hovered(True)

        self.assertFalse(children[0]["row"]._rizum_row.property("hovered"))
        self.assertTrue(children[1]["row"]._rizum_row.property("hovered"))

        second_filter.refresh_hovered()
        self.assertFalse(children[1]["row"]._rizum_row.property("hovered"))


if __name__ == "__main__":
    unittest.main()
