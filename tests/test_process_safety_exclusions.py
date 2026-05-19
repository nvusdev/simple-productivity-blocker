import os
import sys
import types
import unittest

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

if "psutil" not in sys.modules:
    sys.modules["psutil"] = types.SimpleNamespace(
        process_iter=lambda *args, **kwargs: [],
        Process=lambda *args, **kwargs: None,
        NoSuchProcess=Exception,
        AccessDenied=Exception,
        ZombieProcess=Exception,
    )

from blockers.app_blocker import ProcessMonitor


class FakeProcess:
    def __init__(self, name, exe="", cmdline=None, cwd_path=""):
        self.info = {"name": name, "exe": exe, "cmdline": cmdline or []}
        self._cwd = cwd_path

    def cwd(self):
        return self._cwd


class TestProcessSafetyExclusions(unittest.TestCase):
    def test_protected_system_process_never_terminated_by_name(self):
        pm = ProcessMonitor()
        pm.set_blocked_apps(["explorer.exe"])
        proc = FakeProcess("explorer.exe", r"C:\Windows\explorer.exe")
        self.assertFalse(pm._should_terminate_proc(proc, 0.0, 0.0))

    def test_protected_system_process_never_terminated_by_exe_basename(self):
        pm = ProcessMonitor()
        pm.set_blocked_apps(["svchost.exe"])
        proc = FakeProcess("renamed-host.exe", r"C:\Windows\System32\svchost.exe")
        self.assertFalse(pm._should_terminate_proc(proc, 0.0, 0.0))

    def test_non_protected_blocked_process_still_terminates(self):
        pm = ProcessMonitor()
        pm.set_blocked_apps(["notepadplusplus.exe"])
        proc = FakeProcess("notepadplusplus.exe", r"C:\Apps\notepadplusplus.exe")
        self.assertTrue(pm._should_terminate_proc(proc, 0.0, 0.0))

    def test_literal_keyword_allowlist_matching(self):
        pm = ProcessMonitor()
        # Set up global allowlisted keywords containing ".git"
        pm._global_allowlisted_keywords = [".git"]
        
        # Test a path that would match ".git" under regex (e.g. dot matches 'r' in "gitrepo") but should NOT match literally
        proc_gitrepo = FakeProcess("someprocess.exe", r"A:\gitrepo\app.exe")
        pm.set_blocked_apps([r"A:\gitrepo\app.exe"])
        self.assertTrue(pm._should_terminate_proc(proc_gitrepo, 0.0, 0.0))
        
        # Test a path that actually contains the literal ".git" folder/file (should match literally and be allowed)
        proc_dot_git = FakeProcess("git.exe", r"A:\gitrepo\.git\hooks\pre-commit")
        self.assertFalse(pm._should_terminate_proc(proc_dot_git, 0.0, 0.0))


if __name__ == "__main__":
    unittest.main()
