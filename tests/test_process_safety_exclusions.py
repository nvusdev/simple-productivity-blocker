import os
import sys
import types
import unittest

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

if "psutil" not in sys.modules:
    sys.modules["psutil"] = types.SimpleNamespace(process_iter=lambda *args, **kwargs: [])

from blockers.app_blocker import ProcessMonitor


class _FakeProc:
    def __init__(self, name, exe="", cmdline=None, cwd_path=""):
        self.info = {"name": name, "exe": exe, "cmdline": cmdline or []}
        self._cwd = cwd_path

    def cwd(self):
        return self._cwd


class TestProcessSafetyExclusions(unittest.TestCase):
    def test_protected_system_process_never_terminated_by_name(self):
        pm = ProcessMonitor()
        pm.set_blocked_apps(["explorer.exe"])
        proc = _FakeProc("explorer.exe", r"C:\Windows\explorer.exe")
        self.assertFalse(pm._should_terminate_proc(proc, 0.0, 0.0))

    def test_protected_system_process_never_terminated_by_exe_basename(self):
        pm = ProcessMonitor()
        pm.set_blocked_apps(["svchost.exe"])
        proc = _FakeProc("renamed-host.exe", r"C:\Windows\System32\svchost.exe")
        self.assertFalse(pm._should_terminate_proc(proc, 0.0, 0.0))

    def test_non_protected_blocked_process_still_terminates(self):
        pm = ProcessMonitor()
        pm.set_blocked_apps(["notepad-plus-plus.exe"])
        proc = _FakeProc("notepad-plus-plus.exe", r"C:\Apps\notepad-plus-plus.exe")
        self.assertTrue(pm._should_terminate_proc(proc, 0.0, 0.0))


if __name__ == "__main__":
    unittest.main()
