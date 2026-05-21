import os
import sys
import unittest
from unittest.mock import MagicMock, patch

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from blockers.app_blocker import ProcessMonitor
from core.persistence import register_watchdog_task, set_process_watchdog

class TestWatchdogAndScanCap(unittest.TestCase):
    def setUp(self):
        self.pm = ProcessMonitor()

    def test_set_non_acl_max_files_unlimited(self):
        self.pm.set_non_acl_max_files(0)
        self.assertEqual(self.pm._non_acl_max_files, 0)
        
        # Verify walking all files when max_files is 0
        with patch('os.path.exists', return_value=True), \
             patch('os.walk', return_value=[('/root', [], ['file1.png', 'file2.png', 'file3.png'])]):
            files = self.pm._get_all_files_in_folder('/root', max_files=self.pm._non_acl_max_files)
            self.assertEqual(len(files), 3)

    def test_set_non_acl_max_files_capped(self):
        self.pm.set_non_acl_max_files(2)
        self.assertEqual(self.pm._non_acl_max_files, 2)
        
        # Verify walking is capped when max_files is positive
        with patch('os.path.exists', return_value=True), \
             patch('os.walk', return_value=[('/root', [], ['file1.png', 'file2.png', 'file3.png'])]):
            files = self.pm._get_all_files_in_folder('/root', max_files=self.pm._non_acl_max_files)
            self.assertEqual(len(files), 2)

    @patch('subprocess.run')
    def test_register_watchdog_task_powershell(self, mock_run):
        # Mock successful subprocess execution
        mock_run.return_value = MagicMock(returncode=0)
        
        with patch('os.name', 'nt'):
            res = register_watchdog_task("SPB_Daemon", "SPB_Watchdog")
            self.assertTrue(res)
            
            # Verify powershell command was run
            mock_run.assert_called_once()
            args, kwargs = mock_run.call_args
            cmd = args[0]
            self.assertEqual(cmd[0], 'powershell')
            self.assertIn('SPB_Watchdog', cmd[2])
            self.assertIn('SPB_Daemon', cmd[2])

    @patch('subprocess.run')
    def test_set_process_watchdog_enabled(self, mock_run):
        # Mock successful subprocess execution
        mock_run.return_value = MagicMock(returncode=0)
        
        with patch('os.name', 'nt'), \
             patch('core.persistence.is_startup_enabled', return_value=True):
            res = set_process_watchdog(True, "SPB_Daemon", "SPB_Watchdog")
            self.assertTrue(res)
            
            # Verify task registered
            mock_run.assert_called_once()
            args, _ = mock_run.call_args
            self.assertEqual(args[0][0], 'powershell')

    @patch('subprocess.run')
    def test_set_process_watchdog_disabled(self, mock_run):
        # Mock successful subprocess execution
        mock_run.return_value = MagicMock(returncode=0)
        
        with patch('os.name', 'nt'):
            res = set_process_watchdog(False, "SPB_Daemon", "SPB_Watchdog")
            self.assertTrue(res)
            
            # Verify task deleted
            mock_run.assert_called_once()
            args, _ = mock_run.call_args
            self.assertEqual(args[0], ['schtasks', '/delete', '/tn', 'SPB_Watchdog', '/f'])

if __name__ == '__main__':
    unittest.main()
