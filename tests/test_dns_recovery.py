import os
import json
import unittest
from unittest.mock import patch, MagicMock
from blockers.dns_server import detect_system_dns, DNS_STATE_FILE, LOOPBACK_DNS

class TestDNSRecovery(unittest.TestCase):
    def setUp(self):
        self.test_state_file = DNS_STATE_FILE + ".test"
        if os.path.exists(self.test_state_file):
            os.remove(self.test_state_file)

    def tearDown(self):
        if os.path.exists(self.test_state_file):
            os.remove(self.test_state_file)

    @patch("blockers.dns_server.DNS_STATE_FILE", new_callable=lambda: DNS_STATE_FILE + ".test")
    def test_detect_system_dns_from_state(self, mock_state_path):
        # 1. Create a mock dns_state.json
        mock_state = {
            "version": 1,
            "adapters": [
                {
                    "index": 1,
                    "alias": "Ethernet",
                    "ipv4": ["8.8.8.8", "127.0.0.1"],
                    "ipv6": ["2001:4860:4860::8888", "::1"]
                }
            ]
        }
        
        os.makedirs(os.path.dirname(self.test_state_file), exist_ok=True)
        with open(self.test_state_file, "w") as f:
            json.dump(mock_state, f)

        # 2. Call detect_system_dns
        # We also need to patch the powershell call to avoid real system changes/delays
        with patch("subprocess.run") as mock_run:
            mock_run.return_value.stdout = "" # No live DNS found
            dns_servers = detect_system_dns()

        # 3. Verify results
        self.assertIn("8.8.8.8", dns_servers)
        self.assertIn("2001:4860:4860::8888", dns_servers)
        self.assertNotIn("127.0.0.1", dns_servers)
        self.assertNotIn("::1", dns_servers)
        print("✅ detect_system_dns correctly recovered DNS from state file.")

    @patch("blockers.dns_server.DNS_STATE_FILE", new_callable=lambda: "non_existent_file.json")
    def test_detect_system_dns_fallback(self, mock_state_path):
        # Test fallback when no state file and no system DNS found
        with patch("subprocess.run") as mock_run:
            mock_run.return_value.stdout = "" 
            dns_servers = detect_system_dns()
        
        self.assertIn("8.8.8.8", dns_servers)
        self.assertIn("1.1.1.1", dns_servers)
        print("✅ detect_system_dns correctly fell back to public DNS.")

if __name__ == "__main__":
    unittest.main()
