# filepath: tests/test_core_logic.py
import unittest
import os
import sys

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.persistence import is_startup_enabled
from core.platform_handler import get_platform_handler

class TestCoreLogic(unittest.TestCase):
    def setUp(self):
        self.handler = get_platform_handler()

    def test_platform_handler_instantiation(self):
        """Ensure the correct handler is instantiated based on the OS."""
        self.assertIsNotNone(self.handler)
        if os.name == 'nt':
            self.assertEqual(self.handler.__class__.__name__, 'WindowsHandler')
        else:
            self.assertEqual(self.handler.__class__.__name__, 'LinuxHandler')

    def test_data_dir_resolution(self):
        """Verify that the data directory resolves to an absolute path."""
        data_dir = self.handler.get_data_dir()
        self.assertTrue(os.path.isabs(data_dir))

    def test_startup_check_does_not_crash(self):
        """Ensure the startup status query handles missing tasks gracefully."""
        try:
            status = is_startup_enabled("TestBlocker_NonExistent")
            self.assertIsInstance(status, bool)
        except Exception as e:
            self.fail(f"is_startup_enabled raised an exception: {e}")

if __name__ == '__main__':
    unittest.main()
