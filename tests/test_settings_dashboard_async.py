import os
import sys
import unittest
from unittest.mock import patch

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import main


class FakeWidget:
    def __init__(self):
        self.calls = []

    def winfo_exists(self):
        return True

    def configure(self, **kwargs):
        self.calls.append(kwargs)

    def pack(self, *args, **kwargs):
        self.calls.append({"pack": kwargs})

    def pack_forget(self):
        self.calls.append({"pack_forget": True})

    def destroy(self):
        self.calls.append({"destroy": True})


class FakeVar:
    def __init__(self, value=False):
        self.value = value

    def set(self, value):
        self.value = value

    def get(self):
        return self.value


class FakeThread:
    started_targets = []

    def __init__(self, target, daemon=False):
        self.target = target
        self.daemon = daemon

    def start(self):
        FakeThread.started_targets.append(self.target)


class TestSettingsDashboardAsync(unittest.TestCase):
    def setUp(self):
        self.app = main.ProductivityApp.__new__(main.ProductivityApp)
        self.app._screen_generation = 7
        self.app._countdown_timer = "timer-a"
        self.app._debounce_timer = "timer-b"
        self.app._settings_cache_ttl = 30.0
        self.app.winfo_exists = lambda: True
        self.app.after = lambda delay, fn=None: None
        self.app.after_cancel = lambda token: setattr(self.app, "_last_cancelled", token)

    def test_clear_screen_bumps_generation_and_cancels_timers(self):
        child = FakeWidget()
        self.app.winfo_children = lambda: [child]

        main.ProductivityApp.clear_screen(self.app)

        self.assertEqual(self.app._screen_generation, 8)
        self.assertIn(self.app._last_cancelled, {"timer-a", "timer-b"})
        self.assertTrue(any(call.get("destroy") for call in child.calls))

    def test_refresh_startup_status_uses_background_thread(self):
        self.app._startup_status_lbl = FakeWidget()
        self.app._startup_switch = FakeWidget()
        self.app.startup_var = FakeVar(False)
        self.app._startup_status_cache = {"value": None, "checked_at": 0.0}

        FakeThread.started_targets = []
        with patch("main.threading.Thread", FakeThread), patch.object(main.handler, "is_startup_enabled", side_effect=AssertionError("should not run inline")):
            main.ProductivityApp._refresh_startup_status_async(self.app, 7)

        self.assertEqual(len(FakeThread.started_targets), 1)
        self.assertTrue(any(call.get("state") == "disabled" for call in self.app._startup_switch.calls))

    def test_refresh_compatibility_status_uses_background_thread(self):
        self.app._compatibility_status_lbl = FakeWidget()
        self.app._compatibility_help_btn = FakeWidget()
        self.app._conflict_status_cache = {"value": None, "checked_at": 0.0}

        FakeThread.started_targets = []
        with patch("main.threading.Thread", FakeThread), patch("main.detect_conflicting_services", side_effect=AssertionError("should not run inline")):
            main.ProductivityApp._refresh_compatibility_status_async(self.app, 7)

        self.assertEqual(len(FakeThread.started_targets), 1)
        self.assertTrue(any(call.get("pack_forget") for call in self.app._compatibility_help_btn.calls))


if __name__ == "__main__":
    unittest.main()
