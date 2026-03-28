"""Tests for cli/engine_tuner.py — recommend_engine_count, get_system_info, etc."""

import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, "/c/System_Trading/STOM/STOM_V")

from cli.engine_tuner import (
    check_resources,
    estimate_memory_per_engine,
    get_system_info,
    recommend_engine_count,
)


# ---------------------------------------------------------------------------
# recommend_engine_count
# ---------------------------------------------------------------------------

class TestRecommendEngineCount(unittest.TestCase):

    @patch("os.cpu_count", return_value=1)
    def test_cpu_1_recommends_1(self, _):
        r = recommend_engine_count()
        self.assertEqual(r["recommended"], 1)

    @patch("os.cpu_count", return_value=2)
    def test_cpu_2_recommends_1(self, _):
        r = recommend_engine_count()
        self.assertEqual(r["recommended"], 1)

    @patch("os.cpu_count", return_value=4)
    def test_cpu_4_recommends_2(self, _):
        r = recommend_engine_count()
        self.assertEqual(r["recommended"], 2)

    @patch("os.cpu_count", return_value=6)
    def test_cpu_6_recommends_4(self, _):
        # max(2, 6-2) = 4
        r = recommend_engine_count()
        self.assertEqual(r["recommended"], 4)

    @patch("os.cpu_count", return_value=8)
    def test_cpu_8_recommends_6(self, _):
        # max(2, 8-2) = 6
        r = recommend_engine_count()
        self.assertEqual(r["recommended"], 6)

    @patch("os.cpu_count", return_value=16)
    def test_cpu_16_capped_at_8(self, _):
        # min(16-2, 8) = 8
        r = recommend_engine_count()
        self.assertEqual(r["recommended"], 8)

    @patch("os.cpu_count", return_value=10)
    def test_cpu_10_capped_at_8(self, _):
        # min(10-2, 8) = 8
        r = recommend_engine_count()
        self.assertEqual(r["recommended"], 8)

    @patch("os.cpu_count", return_value=8)
    def test_total_codes_limits_recommendation(self, _):
        # recommended=6, but only 3 codes
        r = recommend_engine_count(total_codes=3)
        self.assertEqual(r["recommended"], 3)

    @patch("os.cpu_count", return_value=8)
    def test_total_codes_larger_than_recommended_no_effect(self, _):
        # recommended=6, codes=100 -> stay at 6
        r = recommend_engine_count(total_codes=100)
        self.assertEqual(r["recommended"], 6)

    @patch("os.cpu_count", return_value=4)
    def test_returns_required_fields(self, _):
        r = recommend_engine_count()
        self.assertIn("recommended", r)
        self.assertIn("cpu_count", r)
        self.assertIn("reason", r)


# ---------------------------------------------------------------------------
# get_system_info
# ---------------------------------------------------------------------------

class TestGetSystemInfo(unittest.TestCase):

    def test_returns_required_fields(self):
        info = get_system_info()
        self.assertIn("cpu_count", info)
        self.assertIn("memory_total_gb", info)
        self.assertIn("memory_available_gb", info)
        self.assertIn("platform", info)

    def test_cpu_count_positive(self):
        info = get_system_info()
        self.assertGreater(info["cpu_count"], 0)

    def test_platform_is_string(self):
        info = get_system_info()
        self.assertIsInstance(info["platform"], str)
        self.assertGreater(len(info["platform"]), 0)

    @patch.dict("sys.modules", {"psutil": None})
    def test_fallback_when_psutil_missing(self):
        # When psutil is unavailable, memory fields default to 0.0
        import importlib
        import cli.engine_tuner as et
        importlib.reload(et)
        with patch("os.cpu_count", return_value=4):
            info = et.get_system_info()
        self.assertEqual(info["cpu_count"], 4)
        # memory may be 0.0 if psutil absent — just check types
        self.assertIsInstance(info["memory_total_gb"], float)
        self.assertIsInstance(info["memory_available_gb"], float)


# ---------------------------------------------------------------------------
# estimate_memory_per_engine
# ---------------------------------------------------------------------------

class TestEstimateMemory(unittest.TestCase):

    def test_tick_returns_500(self):
        self.assertEqual(estimate_memory_per_engine(is_tick=True), 500.0)

    def test_min_returns_200(self):
        self.assertEqual(estimate_memory_per_engine(is_tick=False), 200.0)


# ---------------------------------------------------------------------------
# check_resources
# ---------------------------------------------------------------------------

class TestCheckResources(unittest.TestCase):

    def _make_system_info(self, available_gb):
        return {
            "cpu_count": 8,
            "memory_total_gb": 16.0,
            "memory_available_gb": available_gb,
            "platform": "Linux",
        }

    @patch("cli.engine_tuner.get_system_info")
    @patch("os.cpu_count", return_value=8)
    def test_ok_when_enough_memory(self, _cpu, mock_info):
        # 4 engines × 200 MB = 800 MB; available = 4 GB
        mock_info.return_value = self._make_system_info(available_gb=4.0)
        result = check_resources(engine_count=4, is_tick=False)
        self.assertEqual(result["status"], "ok")
        self.assertIn("recommended", result)

    @patch("cli.engine_tuner.get_system_info")
    @patch("os.cpu_count", return_value=8)
    def test_warning_when_insufficient_memory(self, _cpu, mock_info):
        # 6 engines × 500 MB = 3000 MB; available = 1 GB (1024 MB)
        mock_info.return_value = self._make_system_info(available_gb=1.0)
        result = check_resources(engine_count=6, is_tick=True)
        self.assertEqual(result["status"], "warning")
        self.assertIn("recommended", result)
        self.assertLess(result["recommended"], 6)

    @patch("cli.engine_tuner.get_system_info")
    @patch("os.cpu_count", return_value=8)
    def test_ok_when_no_psutil(self, _cpu, mock_info):
        # memory_available_gb == 0.0 means psutil unavailable
        mock_info.return_value = self._make_system_info(available_gb=0.0)
        result = check_resources(engine_count=4, is_tick=False)
        self.assertEqual(result["status"], "ok")

    def test_returns_required_fields(self):
        result = check_resources(engine_count=2, is_tick=False)
        self.assertIn("status", result)
        self.assertIn("message", result)
        self.assertIn("recommended", result)


if __name__ == "__main__":
    unittest.main()
