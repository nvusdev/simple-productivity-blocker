import unittest
from unittest.mock import patch, MagicMock
import sys

# Add project root to sys.path
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import spb_uninstaller

class TestUninstallBlocker(unittest.TestCase):
    @patch("spb_uninstaller.is_admin", return_value=True)
    @patch("core.config_manager.load_config")
    @patch("ctypes.windll.user32.MessageBoxW")
    @patch("sys.exit")
    def test_uninstaller_blocks_when_setting_enabled(self, mock_exit, mock_msgbox, mock_load, mock_admin):
        # Config has block_uninstall = True
        mock_load.return_value = {
            "settings": {
                "block_uninstall": True
            }
        }
        
        # Call main in non-silent mode
        with patch.object(sys, 'argv', ['spb_uninstaller.py']):
            spb_uninstaller.main()
            
        mock_msgbox.assert_called_once()
        self.assertIn("Uninstallation is blocked", mock_msgbox.call_args[0][1])
        mock_exit.assert_called_once_with(1)

    @patch("spb_uninstaller.is_admin", return_value=True)
    @patch("core.config_manager.load_config")
    @patch("sys.exit")
    def test_uninstaller_blocks_silently(self, mock_exit, mock_load, mock_admin):
        # Config has block_uninstall = True
        mock_load.return_value = {
            "settings": {
                "block_uninstall": True
            }
        }
        
        # Call main in silent mode
        with patch.object(sys, 'argv', ['spb_uninstaller.py', '--silent']):
            spb_uninstaller.main()
            
        mock_exit.assert_called_once_with(1)

if __name__ == "__main__":
    unittest.main()
