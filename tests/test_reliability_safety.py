import copy
import json
import os
import shutil
import tempfile
import unittest
from datetime import datetime
from unittest.mock import patch

import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from blockers.app_blocker import ProcessMonitor
from blockers.dns_server import apply_local_dns, restore_dns_state, snapshot_dns_state
from core.config_manager import load_config, normalize_config
from core.scheduler import is_active
import daemon


class TestSchedulerReliability(unittest.TestCase):
    def test_persist_all_day_respects_selected_days(self):
        group = {
            "schedule": {
                "enabled": True,
                "persist_all_day": True,
                "days": ["Monday"],
                "start_time": "09:00",
                "end_time": "17:00",
            }
        }

        self.assertTrue(is_active(group, datetime(2026, 5, 4, 23, 30)))
        self.assertFalse(is_active(group, datetime(2026, 5, 5, 10, 0)))

    def test_overnight_window_uses_previous_active_day_after_midnight(self):
        group = {
            "schedule": {
                "enabled": True,
                "days": ["Monday"],
                "start_time": "22:00",
                "end_time": "04:00",
            }
        }

        self.assertTrue(is_active(group, datetime(2026, 5, 4, 23, 0)))
        self.assertTrue(is_active(group, datetime(2026, 5, 5, 2, 0)))
        self.assertFalse(is_active(group, datetime(2026, 5, 5, 5, 0)))


class TestConfigReliability(unittest.TestCase):
    def test_legacy_flat_config_is_normalized(self):
        cfg = normalize_config({
            "websites": ["example.com"],
            "exceptions": ["allowed.com"],
            "schedule": {"enabled": True, "start": "08:00", "end": "12:00"},
        })

        group = cfg["groups"]["Default Profile"]
        self.assertEqual(group["websites"], ["example.com"])
        self.assertEqual(group["schedule"]["start_time"], "08:00")
        self.assertIn("allowed.com", group["adblocker"]["exceptions"])
        self.assertEqual(cfg["schema_version"], 2)

    def test_invalid_config_is_quarantined(self):
        tmp = tempfile.mkdtemp()
        try:
            path = os.path.join(tmp, "config.json")
            with open(path, "w", encoding="utf-8") as f:
                f.write("{not-json")

            cfg = load_config(path)
            quarantines = [p for p in os.listdir(tmp) if p.startswith("config.json.bad-")]
            self.assertTrue(quarantines)
            self.assertIn("Default Profile", cfg["groups"])
            self.assertTrue(cfg["migration_warnings"])
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class TestProcessMonitorLifecycle(unittest.TestCase):
    def test_synchronize_all_starts_and_stops_enforcement(self):
        pm = ProcessMonitor()
        events = []

        def fake_start():
            events.append("start")
            pm.is_active = True

        def fake_stop():
            events.append("stop")
            pm.is_active = False

        pm.start = fake_start
        pm.stop = fake_stop

        pm.synchronize_all(["blocked.exe"], [], [])
        self.assertTrue(pm.is_active)
        self.assertEqual(events, ["start"])

        pm.synchronize_all([], [], [])
        self.assertFalse(pm.is_active)
        self.assertEqual(events, ["start", "stop"])


class TestGroupTargetsAndGlobalSettings(unittest.TestCase):
    def test_compute_targets_respects_each_group_schedule(self):
        config = {
            "settings": {"cloud_allowlist_enabled": True, "cloud_allowlist": ["OneDrive.exe"]},
            "groups": {
                "active": {
                    "enabled": True,
                    "websites": ["active.example"],
                    "apps": ["active.exe"],
                    "files": [],
                    "folders": [],
                    "schedule": {"enabled": False},
                    "adblocker": {"enabled": False},
                },
                "inactive": {
                    "enabled": True,
                    "websites": ["inactive.example"],
                    "apps": ["inactive.exe"],
                    "files": [],
                    "folders": [],
                    "schedule": {
                        "enabled": True,
                        "days": [],
                        "start_time": "00:00",
                        "end_time": "23:59",
                    },
                    "adblocker": {"enabled": False},
                },
            },
        }

        ctx = daemon._compute_targets(config, None, os.path.abspath("config.json"))
        self.assertIn("active.example", ctx.manual_domains)
        self.assertIn("active.exe", ctx.processes)
        self.assertNotIn("inactive.example", ctx.manual_domains)
        self.assertNotIn("inactive.exe", ctx.processes)

    def test_global_cloud_allowlist_toggle_controls_global_allowlist(self):
        config = {
            "settings": {
                "cloud_allowlist_enabled": False,
                "cloud_allowlist": ["OneDrive.exe", "allowed.example"],
            },
            "groups": {
                "active": {
                    "enabled": True,
                    "websites": ["blocked.example"],
                    "apps": ["blocked.exe"],
                    "files": [],
                    "folders": [],
                    "schedule": {"enabled": False},
                    "adblocker": {"enabled": False},
                },
            },
        }

        ctx = daemon._compute_targets(config, None, os.path.abspath("config.json"))
        self.assertEqual(ctx.cloud_allowlist, set())


class TestDnsStateSafety(unittest.TestCase):
    def test_snapshot_skips_protected_and_existing_dns_adapters(self):
        adapters = [
            {"alias": "Ethernet", "description": "USB Network", "index": 2, "status": "Up", "ipv4": ["192.168.1.1"], "ipv6": []},
            {"alias": "Tailscale", "description": "Tailscale Tunnel", "index": 3, "status": "Up", "ipv4": [], "ipv6": []},
            {"alias": "Lab", "description": "Plain Adapter", "index": 4, "status": "Up", "ipv4": [], "ipv6": []},
        ]

        state = snapshot_dns_state(adapters=copy.deepcopy(adapters))
        self.assertEqual(state["eligible"], [4])
        self.assertTrue(any("existing DNS" in w for w in state["warnings"]))
        self.assertTrue(any("protected adapter" in w for w in state["warnings"]))

    @patch("blockers.dns_server.os.name", "nt")
    @patch("blockers.dns_server._save_dns_state")
    @patch("blockers.dns_server._set_adapter_dns")
    def test_apply_and_restore_dns_state_exactly(self, mock_set_dns, mock_save):
        mock_set_dns.return_value = True
        state = {
            "eligible": [4],
            "adapters": [
                {"index": 4, "ipv4": ["10.0.0.1"], "ipv6": ["2001:db8::1"]},
                {"index": 5, "ipv4": ["9.9.9.9"], "ipv6": []},
            ],
        }

        self.assertTrue(apply_local_dns(state, state_path="ignored.json"))
        mock_set_dns.assert_called_once_with(4, ["127.0.0.1", "::1"])

        mock_set_dns.reset_mock()
        with patch("blockers.dns_server.os.remove"):
            self.assertTrue(restore_dns_state(state, state_path="ignored.json"))
        mock_set_dns.assert_called_once_with(4, ["10.0.0.1", "2001:db8::1"])


if __name__ == "__main__":
    unittest.main()
