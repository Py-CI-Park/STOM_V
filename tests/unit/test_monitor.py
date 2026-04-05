"""Tests for cli/monitor.py — ProgressMonitor, format_duration, create_progress_bar."""

import sys
import time
import unittest
from io import StringIO
from unittest.mock import patch

sys.path.insert(0, "/c/System_Trading/STOM/STOM_V")

from cli.monitor import ProgressMonitor, create_progress_bar, format_duration


# ---------------------------------------------------------------------------
# format_duration
# ---------------------------------------------------------------------------

class TestFormatDuration(unittest.TestCase):

    def test_seconds_only(self):
        self.assertEqual(format_duration(45), "45s")

    def test_exactly_one_minute(self):
        self.assertEqual(format_duration(60), "1m 0s")

    def test_minutes_and_seconds(self):
        self.assertEqual(format_duration(125), "2m 5s")

    def test_exactly_one_hour(self):
        self.assertEqual(format_duration(3600), "1h 0m 0s")

    def test_hours_minutes_seconds(self):
        self.assertEqual(format_duration(3700), "1h 1m 40s")

    def test_zero_seconds(self):
        self.assertEqual(format_duration(0), "0s")

    def test_fractional_seconds_truncated(self):
        # 59.9 should truncate to 59
        self.assertEqual(format_duration(59.9), "59s")


# ---------------------------------------------------------------------------
# create_progress_bar
# ---------------------------------------------------------------------------

class TestCreateProgressBar(unittest.TestCase):

    def test_empty_bar(self):
        bar = create_progress_bar(0, 100, width=10)
        self.assertIn("░" * 10, bar)
        self.assertIn("0.0%", bar)

    def test_full_bar(self):
        bar = create_progress_bar(100, 100, width=10)
        self.assertIn("█" * 10, bar)
        self.assertIn("100.0%", bar)

    def test_half_bar(self):
        bar = create_progress_bar(50, 100, width=10)
        self.assertIn("█████", bar)
        self.assertIn("50.0%", bar)

    def test_bar_format_brackets(self):
        bar = create_progress_bar(0, 10, width=5)
        self.assertTrue(bar.startswith("["))
        self.assertIn("]", bar)

    def test_zero_total(self):
        # Should not raise; percent defaults to 0
        bar = create_progress_bar(5, 0, width=10)
        self.assertIn("0.0%", bar)

    def test_over_total_clamped(self):
        # current > total should not exceed 100%
        bar = create_progress_bar(150, 100, width=10)
        self.assertIn("100.0%", bar)

    def test_custom_width(self):
        bar = create_progress_bar(0, 10, width=20)
        # bar section between [ and ] should be 20 chars
        inner = bar[bar.index("[") + 1: bar.index("]")]
        self.assertEqual(len(inner), 20)


# ---------------------------------------------------------------------------
# ProgressMonitor
# ---------------------------------------------------------------------------

class TestProgressMonitor(unittest.TestCase):

    def test_init_defaults(self):
        pm = ProgressMonitor()
        self.assertEqual(pm.total_codes, 0)
        self.assertTrue(pm.verbose)
        self.assertEqual(pm._processed, 0)
        self.assertIsNone(pm._start_time)

    def test_init_custom(self):
        pm = ProgressMonitor(total_codes=500, verbose=False)
        self.assertEqual(pm.total_codes, 500)
        self.assertFalse(pm.verbose)

    def test_update_tuple_increments(self):
        pm = ProgressMonitor(total_codes=10, verbose=False)
        pm.update(("ui_id", "종목 처리 완료"))
        self.assertEqual(pm._processed, 1)
        self.assertEqual(pm.last_message, "종목 처리 완료")

    def test_update_string_increments(self):
        pm = ProgressMonitor(total_codes=10, verbose=False)
        pm.update("단순 메시지")
        self.assertEqual(pm._processed, 1)
        self.assertEqual(pm.last_message, "단순 메시지")

    def test_update_sets_start_time(self):
        pm = ProgressMonitor(verbose=False)
        self.assertIsNone(pm._start_time)
        pm.update("msg")
        self.assertIsNotNone(pm._start_time)

    def test_update_verbose_prints_to_stderr(self):
        pm = ProgressMonitor(verbose=True)
        with patch("sys.stderr", new_callable=StringIO) as mock_err:
            pm.update("hello")
            output = mock_err.getvalue()
        self.assertIn("hello", output)

    def test_get_progress_fields(self):
        pm = ProgressMonitor(total_codes=100, verbose=False)
        p = pm.get_progress()
        self.assertIn("processed", p)
        self.assertIn("total", p)
        self.assertIn("percent", p)
        self.assertIn("elapsed_sec", p)
        self.assertIn("eta_sec", p)

    def test_get_progress_percent(self):
        pm = ProgressMonitor(total_codes=100, verbose=False)
        for _ in range(25):
            pm.update("x")
        p = pm.get_progress()
        self.assertAlmostEqual(p["percent"], 25.0, places=1)

    def test_get_progress_eta_none_when_not_started(self):
        pm = ProgressMonitor(total_codes=100, verbose=False)
        p = pm.get_progress()
        self.assertIsNone(p["eta_sec"])

    def test_format_progress_contains_counts(self):
        pm = ProgressMonitor(total_codes=500, verbose=False)
        for _ in range(127):
            pm.update("x")
        result = pm.format_progress()
        self.assertIn("127", result)
        self.assertIn("500", result)

    def test_reset_clears_state(self):
        pm = ProgressMonitor(total_codes=10, verbose=False)
        pm.update("msg")
        pm.reset()
        self.assertEqual(pm._processed, 0)
        self.assertIsNone(pm._start_time)
        self.assertIsNone(pm.last_message)

    def test_is_daemon_thread(self):
        pm = ProgressMonitor()
        self.assertTrue(pm.daemon)


if __name__ == "__main__":
    unittest.main()
