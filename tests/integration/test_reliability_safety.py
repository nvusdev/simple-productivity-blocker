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
from blockers.dns_server import DNSProxyServer
from core.platform_handler import WindowsHandler

def snapshot_dns_state(adapters=None, state_path=None):
    wh = WindowsHandler()
    if adapters is not None:
        wh._run_powershell_json = lambda script: adapters
    return wh._snapshot_dns_state()

def apply_local_dns(state, local_ip="127.0.0.1", state_path=None):
    wh = WindowsHandler()
    return wh._apply_local_dns(state, local_ip, state_path)

def restore_dns_state(state_path=None):
    wh = WindowsHandler()
    return wh._restore_dns_state(state_path)
from dnslib import DNSRecord
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
        self.assertEqual(cfg["schema_version"], 3)

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
                    "schedule": {"enabled": True, "always": True},
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

    def test_hosts_fallback_preserves_dns_priority_order(self):
        manual_domains = {"manual.example", "cloud.example"}
        filter_keywords = {"ads.example", "allowed-filter.example", "cloud-filter.example"}
        cloud_allowlist = {"cloud.example", "cloud-filter.example"}
        filter_exceptions = {"allowed-filter.example", "manual.example"}

        # Apply Exception > Content Filter manually as daemon does
        filtered_filters = {d for d in filter_keywords if d not in filter_exceptions}

        resolved = daemon._resolve_hosts_fallback_domains(
            manual_domains=manual_domains,
            normalized_filter_domains=filtered_filters,
            cloud_allowlist=cloud_allowlist,
        )

        self.assertIn("manual.example", resolved)
        self.assertIn("ads.example", resolved)
        self.assertNotIn("cloud.example", resolved)
        self.assertNotIn("allowed-filter.example", resolved)
        self.assertNotIn("cloud-filter.example", resolved)


class TestDnsPriorityHierarchy(unittest.TestCase):
    class FakeSocket:
        def __init__(self):
            self.sent = []

        def sendto(self, data, addr):
            self.sent.append((data, addr))

    def _decision_payload(self, server, domain):
        sock = self.FakeSocket()
        query = DNSRecord.question(domain)
        server._forward_query = lambda data: b"FORWARDED"
        server._handle_packet(sock, query.pack(), ("127.0.0.1", 53000))
        return sock.sent[0][0]

    def test_cloud_allowlist_overrides_manual_and_filter_blocks(self):
        server = DNSProxyServer(
            manual_list=["critical.example"],
            filter_list=["critical.example"],
            cloud_list=["critical.example"],
            filter_exceptions=[],
            port=53535,
        )

        self.assertEqual(self._decision_payload(server, "critical.example"), b"FORWARDED")

    def test_manual_block_overrides_filter_exception(self):
        server = DNSProxyServer(
            manual_list=["manual.example"],
            filter_list=["manual.example"],
            cloud_list=[],
            filter_exceptions=["manual.example"],
            port=53535,
        )

        payload = self._decision_payload(server, "manual.example")
        response = DNSRecord.parse(payload)
        self.assertEqual(str(response.rr[0].rdata), "0.0.0.0")

    def test_filter_exception_overrides_content_filter(self):
        server = DNSProxyServer(
            manual_list=[],
            filter_list=["ads.example"],
            cloud_list=[],
            filter_exceptions=["ads.example"],
            port=53535,
        )

        self.assertEqual(self._decision_payload(server, "ads.example"), b"FORWARDED")

    def test_content_filter_blocks_when_no_higher_priority_rule_matches(self):
        server = DNSProxyServer(
            manual_list=[],
            filter_list=["ads.example"],
            cloud_list=[],
            filter_exceptions=[],
            port=53535,
        )

        payload = self._decision_payload(server, "ads.example")
        response = DNSRecord.parse(payload)
        self.assertEqual(str(response.rr[0].rdata), "0.0.0.0")


class TestDnsStateSafety(unittest.TestCase):
    def test_snapshot_skips_protected_and_existing_dns_adapters(self):
        adapters = [
            {"alias": "Ethernet", "description": "USB Network", "index": 2, "status": "Up", "ipv4": ["192.168.1.1"], "ipv6": []},
            {"alias": "Tailscale", "description": "Tailscale Tunnel", "index": 3, "status": "Up", "ipv4": [], "ipv6": []},
            {"alias": "Lab", "description": "Plain Adapter", "index": 4, "status": "Up", "ipv4": [], "ipv6": []},
        ]

        state = snapshot_dns_state(adapters=copy.deepcopy(adapters))
        self.assertEqual(sorted(state["eligible"]), [2, 4])
        self.assertTrue(any("protected adapter" in w for w in state["warnings"]))

    @patch("core.platform_handler.subprocess.run")
    def test_apply_and_restore_dns_state_exactly(self, mock_run):
        mock_run.return_value = unittest.mock.MagicMock(returncode=0)
        state = {
            "eligible": [4],
            "adapters": [
                {"index": 4, "ipv4": ["10.0.0.1"], "ipv6": ["2001:db8::1"]},
                {"index": 5, "ipv4": ["9.9.9.9"], "ipv6": []},
            ],
        }

        # Mock writing JSON state to file to prevent actual disk write
        with patch("builtins.open", unittest.mock.mock_open()), \
             patch("os.makedirs"):
            self.assertTrue(apply_local_dns(state, state_path="ignored.json"))
            
        mock_run.assert_called_once()
        args, kwargs = mock_run.call_args
        self.assertIn("-InterfaceIndex 4", args[0][-1])
        self.assertIn("@('127.0.0.1', '::1')", args[0][-1])

        mock_run.reset_mock()
        
        # For restore, we mock opening the file and reading the JSON state
        mock_json_data = json.dumps(state)
        with patch("builtins.open", unittest.mock.mock_open(read_data=mock_json_data)), \
             patch("os.path.exists", return_value=True), \
             patch("os.remove") as mock_remove:
            self.assertTrue(restore_dns_state(state_path="ignored.json"))
            mock_remove.assert_called_once_with("ignored.json")
            
        mock_run.assert_called_once()
        args, kwargs = mock_run.call_args
        self.assertIn("-InterfaceIndex 4", args[0][-1])
        self.assertIn("@('10.0.0.1', '2001:db8::1')", args[0][-1])


if __name__ == "__main__":
    unittest.main()
