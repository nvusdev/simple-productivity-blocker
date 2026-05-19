import os
import sys
import unittest
from unittest.mock import MagicMock, patch

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from blockers.dns_server import DNSProxyServer
from blockers.app_blocker import ProcessMonitor

class TestSubsystemStability(unittest.TestCase):
    def test_dns_proxy_semaphore_initialization(self):
        """Verify that DNSProxyServer initializes a semaphore bounded to 100."""
        server = DNSProxyServer([], [])
        self.assertEqual(server._semaphore._value, 100)

    def test_dns_proxy_semaphore_handling(self):
        """Verify that DNSProxyServer semaphore acquisition drops requests when saturated."""
        server = DNSProxyServer([], [])
        # Consume all 100 slots
        for _ in range(100):
            self.assertTrue(server._semaphore.acquire(blocking=False))

        # 101st request should fail to acquire
        self.assertFalse(server._semaphore.acquire(blocking=False))

        # Release one
        server._semaphore.release()
        self.assertTrue(server._semaphore.acquire(blocking=False))

    def test_app_blocker_lru_cache_eviction(self):
        """Verify that ProcessMonitor path cache operates as a bounded LRU cache at 2000 entries."""
        pm = ProcessMonitor()
        # Initially empty
        self.assertEqual(len(pm._path_cache), 0)

        # Fill the cache with 2000 items
        for i in range(2000):
            pm._normalize_path(f"C:\\test_path_{i}.txt")
        self.assertEqual(len(pm._path_cache), 2000)

        # Access the oldest element (C:\test_path_0.txt)
        pm._normalize_path("C:\\test_path_0.txt")

        # Add one more item
        pm._normalize_path("C:\\test_path_2000.txt")

        # Cache size remains 2000
        self.assertEqual(len(pm._path_cache), 2000)

        # C:\test_path_0.txt should still be in cache because it was moved to end
        self.assertIn("C:\\test_path_0.txt", pm._path_cache)

        # C:\test_path_1.txt (which became the oldest because 0 was moved to end) should be evicted
        self.assertNotIn("C:\\test_path_1.txt", pm._path_cache)

    @patch('psutil.process_iter')
    def test_detect_conflicting_services_found(self, mock_process_iter):
        """Verify that detect_conflicting_services identifies a running conflicting process."""
        mock_proc = MagicMock()
        mock_proc.info = {'pid': 1234, 'name': 'Portmaster.exe'}
        mock_process_iter.return_value = [mock_proc]

        from blockers.dns_server import detect_conflicting_services
        res = detect_conflicting_services()
        self.assertEqual(res, "Portmaster.exe (PID: 1234)")

    @patch('psutil.process_iter')
    def test_detect_conflicting_services_not_found(self, mock_process_iter):
        """Verify that detect_conflicting_services returns None if no conflicting processes are running."""
        mock_proc = MagicMock()
        mock_proc.info = {'pid': 5678, 'name': 'notepad.exe'}
        mock_process_iter.return_value = [mock_proc]

        from blockers.dns_server import detect_conflicting_services
        res = detect_conflicting_services()
        self.assertIsNone(res)

if __name__ == "__main__":
    unittest.main()
