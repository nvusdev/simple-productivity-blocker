import os
import sys
import unittest
from datetime import datetime

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.config_manager import normalize_config, DEFAULT_CONFIG
from daemon import _compute_targets, _resolve_hosts_fallback_domains

class TestFallbackHardening(unittest.TestCase):
    def test_default_config_has_max_domains_cap(self):
        normalized = normalize_config({})
        self.assertIn("max_domains_cap", normalized["settings"])
        self.assertEqual(normalized["settings"]["max_domains_cap"], 1000)

    def test_compute_targets_uses_full_time_window_logic_for_normalized(self):
        # Setup config where group schedule is enabled but currently inactive
        config = {
            "settings": {
                "max_domains_cap": 2000,
                "cloud_allowlist_enabled": True,
                "cloud_allowlist": ["safe.com"],
                "cloud_path_keywords": []
            },
            "groups": {
                "Test Group": {
                    "enabled": True,
                    "websites": ["blocked.com"],
                    "adblocker": {
                        "enabled": True,
                        "persist_all_day": False, # Follows schedule
                        "social_media": True,
                        "exceptions": []
                    },
                    "schedule": {
                        "enabled": True,
                        "days": ["Monday"],
                        "start_time": "09:00",
                        "end_time": "17:00"
                    }
                }
            }
        }
        
        # Test 1: During schedule window (active) -> normalized filter domains are computed
        dt_active = datetime(2026, 5, 4, 12, 0) # Monday 12:00 (active)
        res = _compute_targets(config, dt_active, __file__)
        self.assertGreater(len(res.normalized_filter_domains), 0)

        # Test 2: Outside schedule window (inactive) -> normalized filter domains are NOT computed
        dt_inactive = datetime(2026, 5, 4, 8, 0) # Monday 08:00 (inactive)
        res_inactive = _compute_targets(config, dt_inactive, __file__)
        self.assertEqual(len(res_inactive.normalized_filter_domains), 0)

    def test_resolve_hosts_fallback_domains_filters_cloud_allowlist(self):
        manual = {"blocked.com", "safe.com"}
        normalized = {"another.com", "allowed-cloud.com"}
        cloud = {"safe.com", "allowed-cloud.com"}
        
        resolved = _resolve_hosts_fallback_domains(manual, normalized, cloud)
        self.assertIn("blocked.com", resolved)
        self.assertIn("another.com", resolved)
        self.assertNotIn("safe.com", resolved)
        self.assertNotIn("allowed-cloud.com", resolved)

if __name__ == "__main__":
    unittest.main()
