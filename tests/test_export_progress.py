import unittest

from sp_plugin.rizum_sp_to_ps.exporter import _scope_request_progress


class ExportProgressTests(unittest.TestCase):
    def test_request_scopes_form_one_monotonic_batch_progress_range(self):
        events = []
        first = _scope_request_progress(events.append, 1, 2)
        second = _scope_request_progress(events.append, 2, 2)

        first({"stage": "assets", "value": 0, "total": 4})
        first({"stage": "smoothing", "value": 4, "total": 4})
        second({"stage": "assets", "value": 0, "total": 8})
        second({"stage": "smoothing", "value": 8, "total": 8})

        self.assertEqual([event["value"] for event in events], [0, 1000, 1000, 2000])
        self.assertEqual({event["total"] for event in events}, {2000})


if __name__ == "__main__":
    unittest.main()
