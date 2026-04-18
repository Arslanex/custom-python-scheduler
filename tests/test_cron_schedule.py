"""cron_schedule modülü testleri — kökten: PYTHONPATH=. python -m unittest tests.test_cron_schedule -v"""

import unittest
from datetime import datetime

from src.cron_schedule import CronSpec, matches, next_fire, parse_cron


class TestParseCron(unittest.TestCase):
    def test_five_fields_required(self):
        with self.assertRaises(ValueError):
            parse_cron("0 9 * *")
        with self.assertRaises(ValueError):
            parse_cron("0 9 * * * *")

    def test_wildcards_are_none(self):
        s = parse_cron("* * * * *")
        self.assertIsNone(s.minute)
        self.assertIsNone(s.hour)

    def test_fixed_minute_hour(self):
        s = parse_cron("30 14 * * *")
        self.assertEqual(s.minute, frozenset({30}))
        self.assertEqual(s.hour, frozenset({14}))

    def test_step_minutes(self):
        s = parse_cron("*/15 * * * *")
        self.assertEqual(s.minute, frozenset(range(0, 60, 15)))

    def test_comma_and_range(self):
        s = parse_cron("1,15,30 9-11 * * *")
        self.assertEqual(s.minute, frozenset({1, 15, 30}))
        self.assertEqual(s.hour, frozenset({9, 10, 11}))

    def test_dow_seven_maps_to_sunday(self):
        s = parse_cron("* * * * 7")
        self.assertIn(0, s.dow)
        self.assertNotIn(7, s.dow)

    def test_invalid_step(self):
        with self.assertRaises(ValueError):
            parse_cron("*/0 * * * *")


class TestMatches(unittest.TestCase):
    def test_every_minute_matches(self):
        spec = parse_cron("* * * * *")
        self.assertTrue(matches(datetime(2026, 6, 1, 12, 0), spec))

    def test_specific_weekday_monday(self):
        spec = parse_cron("0 9 * * 1")
        mon = datetime(2026, 4, 13, 9, 0)  # Pazartesi
        self.assertTrue(matches(mon, spec))
        tue = datetime(2026, 4, 14, 9, 0)
        self.assertFalse(matches(tue, spec))


class TestNextFire(unittest.TestCase):
    def test_monday_morning_after_sunday_anchor(self):
        # 12 Nis 2026 Pazar — sonraki Pzt 09:00
        sun = datetime(2026, 4, 12, 10, 0)
        nf = next_fire("0 9 * * 1", sun)
        self.assertEqual(nf, datetime(2026, 4, 13, 9, 0))

    def test_same_minute_advances(self):
        t0 = datetime(2026, 5, 1, 14, 30, 45)
        nf = next_fire("30 14 * * *", t0)
        self.assertEqual(nf, datetime(2026, 5, 2, 14, 30))

    def test_daily_eleven_after_ten(self):
        nf = next_fire("0 11 * * *", datetime(2026, 3, 10, 10, 30))
        self.assertEqual(nf, datetime(2026, 3, 10, 11, 0))

    def test_monthly_first(self):
        nf = next_fire("0 9 1 * *", datetime(2026, 4, 15, 12, 0))
        self.assertEqual(nf, datetime(2026, 5, 1, 9, 0))


class TestCronSpecFrozen(unittest.TestCase):
    def test_spec_immutable(self):
        s = parse_cron("0 0 * * *")
        self.assertIsInstance(s, CronSpec)
        with self.assertRaises(AttributeError):
            s.minute = frozenset({1})  # type: ignore[misc]


if __name__ == "__main__":
    unittest.main()
