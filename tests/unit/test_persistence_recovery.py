import unittest
import os
import sys
import json
import tempfile
import shutil

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from core.persistence import is_startup_enabled, harden_config_dir
from recovery_uplift import terminate_spb_processes

class TestPersistenceRecovery(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.recovery_file = os.path.join(self.test_dir, "recovery.json")

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_is_startup_enabled_runs(self):
        # We just want to ensure it doesn't crash
        status = is_startup_enabled()
        self.assertIsInstance(status, bool)

    @unittest.skipIf(os.name != 'nt', "Windows-only ACL hardening")
    def test_harden_config_dir(self):
        # Ensure it runs without crashing
        res = harden_config_dir(self.test_dir)
        self.assertTrue(res)

    def test_terminate_spb_processes_runs(self):
        # Ensure it runs without crashing (won't actually kill anything unless running)
        try:
            terminate_spb_processes()
        except Exception as e:
            self.fail(f"terminate_spb_processes crashed: {e}")

    def test_is_safe_mode(self):
        from core.win32_utils import is_safe_mode
        status = is_safe_mode()
        self.assertIsInstance(status, bool)

if __name__ == "__main__":
    unittest.main()
