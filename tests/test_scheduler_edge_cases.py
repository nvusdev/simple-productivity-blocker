import os
import sys
import unittest
from datetime import datetime

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.scheduler import is_day_active, is_active


class TestIsDayActive(unittest.TestCase):
    def test_disabled_or_always_schedule_returns_true(self):
        self.assertTrue(is_day_active({"enabled": False}, datetime(2026, 5, 4, 10, 0)))
        self.assertTrue(is_day_active({"enabled": True, "always": True}, datetime(2026, 5, 4, 10, 0)))

    def test_day_list_and_boolean_fallback_are_supported(self):
        monday = datetime(2026, 5, 4, 12, 0)  # Monday
        self.assertTrue(is_day_active({"enabled": True, "days": ["Monday"]}, monday))
        self.assertFalse(is_day_active({"enabled": True, "days": ["Tuesday"]}, monday))
        self.assertTrue(is_day_active({"enabled": True, "Monday": True}, monday))


class TestIsActive(unittest.TestCase):
    def test_group_disabled_returns_false(self):
        cfg = {"enabled": False, "schedule": {"enabled": False}}
        self.assertFalse(is_active(cfg, datetime(2026, 5, 4, 10, 0)))

    def test_schedule_disabled_returns_true(self):
        cfg = {"enabled": True, "schedule": {"enabled": False}}
        self.assertTrue(is_active(cfg, datetime(2026, 5, 4, 10, 0)))

    def test_regular_window_respects_inclusive_boundaries(self):
        cfg = {
            "enabled": True,
            "schedule": {
                "enabled": True,
                "days": ["Monday"],
                "start_time": "09:00",
                "end_time": "17:00",
            },
        }
        self.assertTrue(is_active(cfg, datetime(2026, 5, 4, 9, 0)))
        self.assertTrue(is_active(cfg, datetime(2026, 5, 4, 17, 0)))
        self.assertFalse(is_active(cfg, datetime(2026, 5, 4, 8, 59)))
        self.assertFalse(is_active(cfg, datetime(2026, 5, 5, 10, 0)))

    def test_overnight_window_uses_previous_day_after_midnight(self):
        cfg = {
            "enabled": True,
            "schedule": {
                "enabled": True,
                "days": ["Monday"],
                "start_time": "22:00",
                "end_time": "03:00",
            },
        }
        self.assertTrue(is_active(cfg, datetime(2026, 5, 4, 22, 30)))  # Monday late
        self.assertTrue(is_active(cfg, datetime(2026, 5, 5, 1, 0)))    # Tuesday early, still Monday window
        self.assertFalse(is_active(cfg, datetime(2026, 5, 5, 4, 0)))

    def test_invalid_time_format_returns_false(self):
        cfg = {
            "enabled": True,
            "schedule": {
                "enabled": True,
                "days": ["Monday"],
                "start_time": "invalid",
                "end_time": "17:00",
            },
        }
        self.assertFalse(is_active(cfg, datetime(2026, 5, 4, 10, 0)))


if __name__ == "__main__":
    unittest.main()
