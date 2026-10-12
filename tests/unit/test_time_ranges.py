"""Offline calendar-boundary and CLI checks for the Time utility."""
from support import ROOT

from datetime import date, datetime, timedelta, timezone
import importlib.util
import json
import os
import subprocess
import sys
import unittest
from unittest.mock import patch


SPEC = importlib.util.spec_from_file_location(
    "time_ranges_test_module", ROOT / "tools/time/ranges.py"
)
assert SPEC and SPEC.loader
ranges = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = ranges
SPEC.loader.exec_module(ranges)

CLI = ROOT / "tools/time/cli.py"
LABELS = (
    ("today", "今天"),
    ("yesterday", "昨天"),
    ("this_week", "本周"),
    ("this_month", "本月"),
    ("last_month", "上月"),
)
# Independent, fixed reference values include a year boundary and leap February.
EXPECTED = {
    "2026-10-09": (
        ("2026-10-09", "2026-10-09", 1791475200000, 1791561599999),
        ("2026-10-08", "2026-10-08", 1791388800000, 1791475199999),
        ("2026-10-05", "2026-10-11", 1791129600000, 1791734399999),
        ("2026-10-01", "2026-10-31", 1790784000000, 1793462399999),
        ("2026-09-01", "2026-09-30", 1788192000000, 1790783999999),
    ),
    "2026-01-01": (
        ("2026-01-01", "2026-01-01", 1767196800000, 1767283199999),
        ("2025-12-31", "2025-12-31", 1767110400000, 1767196799999),
        ("2025-12-29", "2026-01-04", 1766937600000, 1767542399999),
        ("2026-01-01", "2026-01-31", 1767196800000, 1769875199999),
        ("2025-12-01", "2025-12-31", 1764518400000, 1767196799999),
    ),
    "2024-03-01": (
        ("2024-03-01", "2024-03-01", 1709222400000, 1709308799999),
        ("2024-02-29", "2024-02-29", 1709136000000, 1709222399999),
        ("2024-02-26", "2024-03-03", 1708876800000, 1709481599999),
        ("2024-03-01", "2024-03-31", 1709222400000, 1711900799999),
        ("2024-02-01", "2024-02-29", 1706716800000, 1709222399999),
    ),
}


def expected_ranges(reference):
    return [
        {
            "key": key,
            "label": label,
            "start_ms": start_ms,
            "end_ms": end_ms,
            "start_time": start_day + " 00:00:00.000",
            "end_time": end_day + " 23:59:59.999",
        }
        for (key, label), (start_day, end_day, start_ms, end_ms)
        in zip(LABELS, EXPECTED[reference])
    ]


class TimeRangesTest(unittest.TestCase):
    def run_cli(self, *arguments, host_timezone="UTC"):
        environment = {**os.environ, "TZ": host_timezone}
        return subprocess.run(
            [sys.executable, str(CLI), *arguments],
            cwd=ROOT,
            env=environment,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=10,
            check=False,
        )

    def test_calendar_ranges_include_year_and_leap_month_boundaries(self):
        for reference in EXPECTED:
            with self.subTest(reference=reference):
                actual = ranges.calculate_ranges(date.fromisoformat(reference))
                self.assertEqual(actual, expected_ranges(reference))

    def test_default_date_changes_at_gmt8_midnight(self):
        class FrozenDateTime(datetime):
            instant = datetime(2026, 10, 8, 15, 59, 59, 999000, timezone.utc)
            requested_timezone = None

            @classmethod
            def now(cls, tz=None):
                cls.requested_timezone = tz
                return cls.instant.astimezone(tz) if tz is not None else cls.instant

        with patch.object(ranges, "datetime", FrozenDateTime):
            before = ranges.calculate_ranges()
            self.assertEqual(before[0]["start_ms"], 1791388800000)
            self.assertEqual(before[0]["start_time"], "2026-10-08 00:00:00.000")
            self.assertIsNotNone(FrozenDateTime.requested_timezone)
            self.assertEqual(
                FrozenDateTime.requested_timezone.utcoffset(FrozenDateTime.instant),
                timedelta(hours=8),
            )
            FrozenDateTime.instant += timedelta(milliseconds=1)
            self.assertEqual(ranges.calculate_ranges(), expected_ranges("2026-10-09"))

    def test_json_contract_is_independent_of_host_timezone(self):
        expected = {
            "date": "2026-10-09",
            "timezone": "GMT+8",
            "week_start": "Monday",
            "end_inclusive": True,
            "ranges": expected_ranges("2026-10-09"),
        }
        for host_timezone in ("UTC", "America/Los_Angeles", "Pacific/Honolulu"):
            with self.subTest(host_timezone=host_timezone):
                result = self.run_cli(
                    "--date", "2026-10-09", "--json", host_timezone=host_timezone
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(json.loads(result.stdout), expected)

    def test_cli_rejects_invalid_dates_and_unknown_arguments(self):
        for arguments in (
            ("--date", "2026-02-30"),
            ("--date", "2026-2-03"),
            ("--date", "today"),
            ("--unexpected",),
        ):
            with self.subTest(arguments=arguments):
                result = self.run_cli(*arguments)
                self.assertNotEqual(result.returncode, 0)
                self.assertTrue(result.stderr.strip())
                self.assertEqual(result.stdout, "")


if __name__ == "__main__":
    unittest.main()
