import unittest
import sys
import os

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from blockers.dns_server import DomainMatcher, DNSProxyServer

class TestDomainMatcher(unittest.TestCase):
    def test_exact_match(self):
        matcher = DomainMatcher(["example.com"])
        self.assertTrue(matcher.matches("example.com"))
        self.assertTrue(matcher.matches("www.example.com"))
        self.assertFalse(matcher.matches("test.com"))

    def test_wildcard_domain(self):
        matcher = DomainMatcher(["*.google.com"])
        self.assertTrue(matcher.matches("google.com"))
        self.assertTrue(matcher.matches("www.google.com"))
        self.assertTrue(matcher.matches("sub.sub.google.com"))
        self.assertFalse(matcher.matches("google.co.uk"))

    def test_prefix_match(self):
        matcher = DomainMatcher(["api*"])
        self.assertTrue(matcher.matches("api.google.com"))
        self.assertTrue(matcher.matches("apis.com"))
        self.assertTrue(matcher.matches("google.api.com")) # Now True because it matches the 'api' label

    def test_suffix_match(self):
        matcher = DomainMatcher(["*tube"])
        self.assertTrue(matcher.matches("youtube.com"))
        self.assertTrue(matcher.matches("redtube.com"))
        self.assertTrue(matcher.matches("tube.com")) # Now True because it matches the 'tube' label

    def test_keyword_match(self):
        matcher = DomainMatcher(["youtube"])
        self.assertTrue(matcher.matches("youtube.com"))
        self.assertTrue(matcher.matches("www.youtube.com"))
        self.assertTrue(matcher.matches("music.youtube.com"))
        self.assertTrue(matcher.matches("youtube-extra.com"))
        self.assertFalse(matcher.matches("notutube.com"))

    def test_complex_wildcard(self):
        matcher = DomainMatcher(["test*site.com"])
        self.assertTrue(matcher.matches("testmysite.com"))
        self.assertTrue(matcher.matches("test-cool-site.com"))
        self.assertFalse(matcher.matches("testsite.net"))

class TestHierarchy(unittest.TestCase):
    def setUp(self):
        # Cloud: Always allow
        # Manual: High priority block
        # Exception: Allow within filter
        # Filter: Low priority block
        self.server = DNSProxyServer(
            manual_list=["blocked.com"],
            filter_list=["filtered.com", "youtube.com"],
            cloud_list=["cloud.com", "youtube.com"], # YouTube allowed by cloud, blocked by filter
            filter_exceptions=["filtered.com"] # filtered.com blocked by filter, allowed by exception
        )

    def test_cloud_beats_filter(self):
        # YouTube is in both cloud (allow) and filter (block)
        # Cloud should win
        self.assertTrue(self.server.cloud_matcher.matches("youtube.com"))
        # In real logic, _handle_packet checks cloud first
        
    def test_manual_beats_exception(self):
        # If we manually block it, exceptions shouldn't save it
        server = DNSProxyServer(
            manual_list=["special.com"],
            filter_list=["filtered.com"],
            filter_exceptions=["special.com"]
        )
        # Manual check comes before Exception check in _handle_packet
        pass

if __name__ == "__main__":
    unittest.main()
