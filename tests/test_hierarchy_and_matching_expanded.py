import unittest
import sys
import os
import socket
from unittest.mock import MagicMock, patch
from dnslib import DNSRecord, QTYPE

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from blockers.dns_server import DomainMatcher, DNSProxyServer

class TestPatternMatching(unittest.TestCase):
    def test_wildcard_label_boundary(self):
        # Wildcard should NOT cross dots
        matcher = DomainMatcher(["a*b.com"])
        self.assertTrue(matcher.matches("axb.com"))
        self.assertTrue(matcher.matches("a-long-string-b.com"))
        self.assertFalse(matcher.matches("a.b.com")) # Wildcard [^.]* shouldn't match a dot
        
    def test_prefix_matching(self):
        matcher = DomainMatcher(["work*"])
        self.assertTrue(matcher.matches("work.com"))
        self.assertTrue(matcher.matches("workspace.com"))
        self.assertTrue(matcher.matches("sub.work-extra.com"))
        self.assertFalse(matcher.matches("artwork.com")) # Should be prefix only
        
    def test_suffix_matching(self):
        matcher = DomainMatcher(["*tube"])
        self.assertTrue(matcher.matches("youtube.com"))
        self.assertTrue(matcher.matches("redtube.com"))
        self.assertTrue(matcher.matches("tube.com"))
        self.assertFalse(matcher.matches("tubular.com"))
        
    def test_keyword_matching(self):
        matcher = DomainMatcher(["youtube"])
        self.assertTrue(matcher.matches("youtube.com"))
        self.assertTrue(matcher.matches("music.youtube.com"))
        self.assertTrue(matcher.matches("youtube-extra.com"))
        self.assertFalse(matcher.matches("notutube.com"))

class TestHierarchyLogic(unittest.TestCase):
    def setUp(self):
        # 1. Cloud: youtube.com (Allow)
        # 2. Manual: facebook.com (Block), youtube.com (Block - but cloud should win)
        # 3. Exception: reddit.com (Allow)
        # 4. Filter: reddit.com (Block - but exception should win), twitter.com (Block)
        self.server = DNSProxyServer(
            manual_list=["facebook.com", "youtube.com"],
            filter_list=["twitter.com", "reddit.com"],
            cloud_list=["youtube.com", "allowed.com"],
            filter_exceptions=["reddit.com"]
        )
        self.mock_sock = MagicMock()
        self.addr = ("127.0.0.1", 12345)

    @patch('blockers.dns_server.DNSProxyServer._forward_query')
    @patch('blockers.dns_server.DNSProxyServer._send_block')
    def test_tier1_cloud_wins(self, mock_block, mock_forward):
        # youtube.com is in Cloud AND Manual
        # Cloud should win (Forwarded)
        data = DNSRecord.question("youtube.com").pack()
        self.server._handle_packet(self.mock_sock, data, self.addr)
        
        mock_forward.assert_called_once()
        mock_block.assert_not_called()

    @patch('blockers.dns_server.DNSProxyServer._forward_query')
    @patch('blockers.dns_server.DNSProxyServer._send_block')
    def test_tier2_manual_wins(self, mock_block, mock_forward):
        # facebook.com is in Manual
        data = DNSRecord.question("facebook.com").pack()
        self.server._handle_packet(self.mock_sock, data, self.addr)
        
        mock_block.assert_called_once()
        mock_forward.assert_not_called()

    @patch('blockers.dns_server.DNSProxyServer._forward_query')
    @patch('blockers.dns_server.DNSProxyServer._send_block')
    def test_tier3_exception_wins(self, mock_block, mock_forward):
        # reddit.com is in Exception AND Filter
        # Exception should win (Forwarded)
        data = DNSRecord.question("reddit.com").pack()
        self.server._handle_packet(self.mock_sock, data, self.addr)
        
        mock_forward.assert_called_once()
        mock_block.assert_not_called()

    @patch('blockers.dns_server.DNSProxyServer._forward_query')
    @patch('blockers.dns_server.DNSProxyServer._send_block')
    def test_tier4_filter_blocks(self, mock_block, mock_forward):
        # twitter.com is in Filter
        data = DNSRecord.question("twitter.com").pack()
        self.server._handle_packet(self.mock_sock, data, self.addr)
        
        mock_block.assert_called_once()
        mock_forward.assert_not_called()

    @patch('blockers.dns_server.DNSProxyServer._forward_query')
    def test_default_forward(self, mock_forward):
        # unknown.com should be forwarded
        data = DNSRecord.question("unknown.com").pack()
        self.server._handle_packet(self.mock_sock, data, self.addr)
        
        mock_forward.assert_called_once()

if __name__ == "__main__":
    unittest.main()
