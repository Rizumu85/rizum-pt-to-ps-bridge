from __future__ import annotations

import unittest

from sp_plugin.rizum_sp_to_ps.export_selection_memory import ExportSelectionMemory


class _Settings:
    values = {}

    def __init__(self, organization, application):
        self.namespace = (organization, application)

    def value(self, key, default=None, value_type=None):
        value = self.values.get((self.namespace, key), default)
        return str(value) if value_type is str and value is not None else value

    def setValue(self, key, value):
        self.values[(self.namespace, key)] = value

    def sync(self):
        pass


class _QtCore:
    QSettings = _Settings


class ExportScopeMemoryTests(unittest.TestCase):
    def setUp(self):
        _Settings.values.clear()

    def test_scope_is_restored_only_for_the_same_project(self):
        first = ExportSelectionMemory(
            _QtCore,
            "Rizum",
            "PT-to-PS Bridge",
            "uuid:project-a",
        )
        first.remember_scope("all")
        first.save()

        reopened = ExportSelectionMemory(
            _QtCore,
            "Rizum",
            "PT-to-PS Bridge",
            "uuid:project-a",
        )
        other_project = ExportSelectionMemory(
            _QtCore,
            "Rizum",
            "PT-to-PS Bridge",
            "uuid:project-b",
        )

        self.assertEqual(reopened.scope(), "all")
        self.assertEqual(other_project.scope(), "current")


if __name__ == "__main__":
    unittest.main()
