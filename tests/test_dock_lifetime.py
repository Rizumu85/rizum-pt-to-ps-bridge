from __future__ import annotations

import os
import unittest
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6 import QtCore, QtWidgets  # noqa: E402

from sp_plugin.rizum_sp_to_ps.ui import BridgePanel  # noqa: E402


class DockLifetimeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def test_close_lets_go_of_painters_dock(self):
        # The dock is Painter's. A connection or a queued call that still
        # holds it after the plugin closed crashes Painter when it exits.
        with mock.patch.object(BridgePanel, "_load_user_settings", return_value={}):
            panel = BridgePanel()
        dock = QtWidgets.QDockWidget()
        dock.setWidget(panel.widget)
        self.addCleanup(dock.deleteLater)
        floating_changed = QtCore.SIGNAL("topLevelChanged(bool)")

        panel.attach_dock(dock)

        self.assertTrue(dock.isFloating())
        self.assertGreaterEqual(dock.width(), panel.widget.minimumWidth())
        self.assertEqual(dock.receivers(floating_changed), 1)
        self.assertTrue(panel._floating_resize_timer.isActive())

        panel.close()

        self.assertIsNone(panel._dock)
        self.assertEqual(dock.receivers(floating_changed), 0)
        self.assertFalse(panel._floating_resize_timer.isActive())
        # Nothing of the panel runs against the dock any more.
        self.app.processEvents()


if __name__ == "__main__":
    unittest.main()
