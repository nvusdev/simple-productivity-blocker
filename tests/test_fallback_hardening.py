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

    def test_sync_website_protection_enforces_strict_line_cap(self):
        from blockers.website_blocker import apply_blocks
        from unittest.mock import patch, mock_open

        # Mock the open calls to read an empty hosts file and write captured lines
        mock_hosts_content = "127.0.0.1 localhost\n::1 localhost\n"
        m = mock_open(read_data=mock_hosts_content)

        # 50 domains to trigger the limit of 10 lines
        domains = [f"domain{i}.com" for i in range(50)]

        with patch("builtins.open", m), \
             patch("core.config_manager.load_config", return_value={"settings": {"max_domains_cap": 10}}):
            apply_blocks(domains, block_doh=False)

        # Retrieve the arguments passed to writelines
        handle = m()
        write_calls = handle.writelines.call_args_list
        self.assertTrue(len(write_calls) > 0)
        
        # Merge all writelines outputs
        written_lines = write_calls[0][0][0]
        
        # Check that the block exists and has the correct marker structure
        block_begin_idx = -1
        block_end_idx = -1
        for idx, line in enumerate(written_lines):
            if "# --- SPB Block Begin ---" in line:
                block_begin_idx = idx
            elif "# --- SPB Block End ---" in line:
                block_end_idx = idx

        self.assertNotEqual(block_begin_idx, -1)
        self.assertNotEqual(block_end_idx, -1)
        
        # The number of lines written inside the block (including markers) must be <= 10 (max_domains_cap)
        block_lines_count = block_end_idx - block_begin_idx + 1
        self.assertLessEqual(block_lines_count, 10)
        
        # Since MAX_LINES = 10, max_domains = (10 - 2) // 2 = 4 domains.
        # Each domain produces 2 entries (www and non-www), but since the input has no www,
        # it adds www and non-www (so each original domain has 2 domains, each taking 2 lines = 4 lines per original domain).
        # Thus, only 2 unique domains (each with base and www) can fit, generating 8 lines of host blocks + 2 marker lines = 10 lines total.
        self.assertEqual(block_lines_count, 10)

if __name__ == "__main__":
    unittest.main()
