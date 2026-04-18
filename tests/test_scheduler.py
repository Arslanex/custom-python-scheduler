"""Otomatik testler: proje kökünden `python -m unittest discover -s tests -v`"""

import time
import unittest
from src.dto import Job, JobStatus
from src.scheduler import Scheduler, get_scheduler, schedule


def _nop():
    return 42


class TestSchedulerIntegration(unittest.TestCase):
    def test_trigger_runs_job(self):
        s = Scheduler(tick=0.05, max_workers=2)
        j = Job(name="a", func=_nop, interval=10.0)
        self.assertTrue(s.add(j))
        s.trigger("a")
        time.sleep(0.2)
        self.assertEqual(j.runs, 1)
        self.assertIn(j.status, (JobStatus.PENDING, JobStatus.SUCCESS))

    def test_loop_picks_due_interval(self):
        s = Scheduler(tick=0.05, max_workers=2)
        j = Job(name="b", func=_nop, interval=0.15)
        self.assertTrue(s.add(j))
        s.start()
        time.sleep(0.4)
        s.stop()
        self.assertGreaterEqual(j.runs, 1)

    def test_history_and_status(self):
        s = Scheduler()
        j = Job(name="c", func=_nop, interval=1.0)
        s.add(j)
        s.trigger("c")
        time.sleep(0.2)
        h = s.history(name="c", limit=5)
        self.assertTrue(h)
        self.assertEqual(h[0].name, "c")
        rows = s.status()
        self.assertTrue(any(r["name"] == "c" for r in rows))


class TestDefaultSchedulerHelpers(unittest.TestCase):
    def tearDown(self) -> None:
        import src.scheduler as sched_module

        sched_module._default_scheduler = None

    def test_schedule_decorator_adds_job(self):
        sched = get_scheduler()

        @schedule(interval=99.0)
        def ping():
            return None

        self.assertIn("ping", sched._jobs)


class TestSchedulerLifecycle(unittest.TestCase):
    def test_context_manager_starts_and_stops(self):
        s = Scheduler(tick=0.1)
        with s:
            self.assertIsNotNone(s._thread)
            self.assertTrue(s._thread.is_alive())
        self.assertIsNone(s._thread)

    def test_on_success_hook(self):
        seen: list[str] = []
        s = Scheduler()
        s.on_success(lambda r: seen.append(r.name))
        j = Job(name="hooked", func=_nop, interval=60.0)
        s.add(j)
        s.trigger("hooked")
        time.sleep(0.25)
        self.assertEqual(seen, ["hooked"])

    def test_max_runs_disables_job(self):
        s = Scheduler(tick=0.05, max_workers=2)
        j = Job(name="limited", func=_nop, interval=0.12, max_runs=2)
        self.assertTrue(s.add(j))
        s.start()
        time.sleep(0.55)
        s.stop()
        self.assertEqual(j.runs, 2)
        self.assertFalse(j.enabled)


if __name__ == "__main__":
    unittest.main()
