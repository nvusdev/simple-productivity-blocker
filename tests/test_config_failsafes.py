import os
import sys
import json
import shutil
import tempfile
import unittest
from unittest.mock import patch

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core import config_manager as cm


class TestConfigNormalization(unittest.TestCase):
    def test_legacy_flat_config_migrates_and_preserves_schedule_aliases(self):
        normalized = cm.normalize_config({
            "websites": ["example.com"],
            "exceptions": ["allowed.com", "allowed.com"],
            "schedule": {"enabled": True, "start": "08:00", "end": "11:30"},
            "settings": {"startup_enabled": True},
        })

        group = normalized["groups"]["Default Profile"]
        self.assertEqual(group["websites"], ["example.com"])
        self.assertEqual(group["schedule"]["start_time"], "08:00")
        self.assertEqual(group["schedule"]["end_time"], "11:30")
        self.assertEqual(group["adblocker"]["exceptions"], ["allowed.com"])
        self.assertNotIn("exceptions", group)
        self.assertIn("Legacy flat config migrated", " ".join(normalized["migration_warnings"]))

    def test_invalid_group_payload_is_replaced_with_defaults(self):
        normalized = cm.normalize_config({
            "groups": {
                "Default Profile": "invalid-group-shape",
            }
        })
        group = normalized["groups"]["Default Profile"]
        self.assertIsInstance(group, dict)
        self.assertIn("websites", group)
        self.assertIn("schedule", group)


class TestConfigRecoveryAndPersistence(unittest.TestCase):
    def test_load_config_quarantines_invalid_json(self):
        tmp = tempfile.mkdtemp()
        try:
            cfg_path = os.path.join(tmp, "config.json")
            with open(cfg_path, "w", encoding="utf-8") as f:
                f.write("{broken-json")

            loaded = cm.load_config(cfg_path)
            quarantines = [name for name in os.listdir(tmp) if name.startswith("config.json.bad-")]
            self.assertTrue(quarantines)
            self.assertIn("Default Profile", loaded["groups"])
            self.assertTrue(any("Invalid config quarantined" in w for w in loaded["migration_warnings"]))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_load_config_triggers_repair_if_quarantine_fails(self):
        tmp = tempfile.mkdtemp()
        try:
            cfg_path = os.path.join(tmp, "config.json")
            with open(cfg_path, "w", encoding="utf-8") as f:
                f.write("{broken-json")

            with patch("core.config_manager._quarantine_bad_config", return_value=None), patch(
                "core.config_manager.repair_config", return_value=True
            ) as mock_repair:
                loaded = cm.load_config(cfg_path)

            mock_repair.assert_called_once_with(cfg_path)
            self.assertTrue(any("Elevated self-healing triggered" in w for w in loaded["migration_warnings"]))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_save_config_retries_on_permission_error(self):
        tmp = tempfile.mkdtemp()
        try:
            target_path = os.path.join(tmp, "config.json")
            real_open = open
            call_count = {"count": 0}

            def flaky_open(*args, **kwargs):
                call_count["count"] += 1
                if call_count["count"] == 1:
                    raise PermissionError("simulated lock")
                return real_open(*args, **kwargs)

            with patch("core.config_manager.CONFIG_FILE", target_path), patch(
                "builtins.open", side_effect=flaky_open
            ), patch("core.config_manager.time.sleep") as mock_sleep:
                cm.save_config({"groups": {}, "settings": {}})

            self.assertTrue(os.path.exists(target_path))
            with open(target_path, "r", encoding="utf-8") as f:
                payload = json.load(f)
            self.assertEqual(payload, {"groups": {}, "settings": {}})
            mock_sleep.assert_called_once()
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_export_import_merge_preserves_existing_groups(self):
        tmp = tempfile.mkdtemp()
        try:
            export_path = os.path.join(tmp, "export.spb")
            new_payload = {
                "groups": {
                    "Imported": {
                        "websites": ["imported.example"],
                        "apps": [],
                        "files": [],
                        "folders": [],
                        "adblocker": {"enabled": False, "exceptions": [], "custom_lists": []},
                        "schedule": {"enabled": False},
                        "security": {"enabled": False, "challenge_length": 32},
                    }
                },
                "settings": {"startup_enabled": True},
            }
            self.assertTrue(cm.export_config(new_payload, export_path))

            current = cm.normalize_config({
                "groups": {
                    "Existing": {
                        "websites": ["existing.example"],
                        "apps": [],
                        "files": [],
                        "folders": [],
                        "adblocker": {"enabled": False, "exceptions": [], "custom_lists": []},
                        "schedule": {"enabled": False},
                        "security": {"enabled": False, "challenge_length": 32},
                    }
                },
                "settings": {"startup_enabled": False},
            })

            merged = cm.import_config(export_path, current_config=current, merge=True)
            self.assertIn("Existing", merged["groups"])
            self.assertIn("Imported", merged["groups"])
            self.assertTrue(merged["settings"]["startup_enabled"])
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
