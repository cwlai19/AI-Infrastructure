import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path
from unittest import mock

from tracker import monitor


def ev(eid, kind="8-K", days_ago=0):
    return dict(event_id=eid, feed="edgar", group="g", subject="s", kind=kind,
                event_date=(date.today() - timedelta(days=days_ago)).isoformat(), title="t", url="u")


class AppendNew(unittest.TestCase):
    def setUp(self):
        self.path = Path(tempfile.mkdtemp()) / "events.csv"
        self.patch = mock.patch.object(monitor, "EVENTS", self.path)
        self.patch.start()

    def tearDown(self):
        self.patch.stop()

    def test_first_run_marks_old_events_baseline_and_ignores_noise(self):
        new = monitor.append_new([ev("a", days_ago=1), ev("b", days_ago=100), ev("c", kind="485BXT")], ignore_kinds=("485BXT",))
        self.assertEqual([e["event_id"] for e in new], ["a"])
        statuses = {e["event_id"]: e["status"] for e in monitor.load_events()}
        self.assertEqual(statuses, {"a": "new", "b": "baseline", "c": "ignored"})

    def test_already_logged_events_are_not_repeated(self):
        monitor.append_new([ev("a")])
        self.assertEqual(monitor.append_new([ev("a"), ev("b")]), [ev("b") | {"status": "new"}])

    def test_later_runs_do_not_baseline_old_filings(self):
        monitor.append_new([ev("a")])
        new = monitor.append_new([ev("late", days_ago=100)])
        self.assertEqual([e["event_id"] for e in new], ["late"])
