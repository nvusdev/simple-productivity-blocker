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
        self.assertFalse(matcher.matches("www.example.com"))
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
        self.assertFalse(matcher.matches("youtube-extra.com"))
        self.assertFalse(matcher.matches("notutube.com"))

    def test_complex_wildcard(self):
        matcher = DomainMatcher(["test*site.com"])
        self.assertTrue(matcher.matches("testmysite.com"))
        self.assertTrue(matcher.matches("test-cool-site.com"))
        self.assertFalse(matcher.matches("testsite.net"))



if __name__ == "__main__":
    unittest.main()
