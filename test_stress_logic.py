import sys
import logging

# Add project root to path
sys.path.insert(0, ".")

from blockers.dns_server import DomainMatcher
from daemon import _resolve_hosts_fallback_domains
from blockers.website_blocker import expand_keyword_list

logging.basicConfig(level=logging.ERROR)

def test_dns_matcher():
    # Keywords
    matcher = DomainMatcher(["youtube", "facebook.com", "google.*", "*.twitter.com", "*mybook.com", "reddit.com*"])
    
    # Assert true matches
    assert matcher.matches("youtube.com")
    assert matcher.matches("www.youtube.com")
    assert matcher.matches("music.youtube.com")
    assert matcher.matches("facebook.com")
    assert matcher.matches("www.facebook.com")
    assert matcher.matches("google.co.uk")
    assert matcher.matches("api.google.com")
    assert matcher.matches("api.twitter.com")
    assert matcher.matches("twitter.com")
    assert matcher.matches("testmybook.com")
    assert matcher.matches("reddit.com.br")
    assert matcher.matches("reddit.com")
    
    # Assert false positive preventions
    assert not matcher.matches("myyoutube.com")
    assert not matcher.matches("notfacebook.com")

    print("[SUCCESS] DNS DomainMatcher edge cases validated.")

def test_hosts_fallback_hierarchy():
    # 1. Cloud Allowlist > Manual Block
    resolved = _resolve_hosts_fallback_domains(
        manual_domains={"youtube.com", "facebook.com"},
        filter_keywords=set(),
        cloud_allowlist={"youtube.com"},
        filter_exceptions=set()
    )
    assert "facebook.com" in resolved, "Manual block should be active if not allowlisted."
    assert "youtube.com" not in resolved, "Cloud allowlist must override manual blocks."

    # 2. Cloud Allowlist > Content Filter
    resolved = _resolve_hosts_fallback_domains(
        manual_domains=set(),
        filter_keywords={"ads.google.com", "tracker.com"},
        cloud_allowlist={"ads.google.com"},
        filter_exceptions=set()
    )
    assert "tracker.com" in resolved, "Content filter should be active."
    assert "ads.google.com" not in resolved, "Cloud allowlist must override content filters."

    # 3. Exceptions > Content Filter
    resolved = _resolve_hosts_fallback_domains(
        manual_domains=set(),
        filter_keywords={"ads.google.com", "tracker.com"},
        cloud_allowlist=set(),
        filter_exceptions={"ads.google.com"}
    )
    assert "tracker.com" in resolved, "Content filter should be active."
    assert "ads.google.com" not in resolved, "Exceptions must override content filters."

    # 4. Manual Block > Exceptions (If Group A blocks and Group B excepts)
    resolved = _resolve_hosts_fallback_domains(
        manual_domains={"ads.google.com"},
        filter_keywords={"ads.google.com"},
        cloud_allowlist=set(),
        filter_exceptions={"ads.google.com"}
    )
    assert "ads.google.com" in resolved, "Manual blocks must strictly override exceptions."

    print("[SUCCESS] Fallback hierarchy strict prioritization validated.")

def test_expand_keyword():
    expanded = expand_keyword_list(["youtube", "x.com"])
    
    # Verify standard TLD and subdomain coverage for keywords
    assert "youtube.com" in expanded
    assert "www.youtube.com" in expanded
    assert "m.youtube.com" in expanded
    
    # Verify exact domains retain www coverage
    assert "x.com" in expanded
    assert "www.x.com" in expanded
    
    print("[SUCCESS] Hosts keyword list expansion and permutation validated.")

if __name__ == "__main__":
    try:
        print("--- STARTING STRESS TESTS ---")
        test_dns_matcher()
        test_hosts_fallback_hierarchy()
        test_expand_keyword()
        print("--- ALL TESTS PASSED ---")
    except AssertionError as e:
        print(f"[FAILED] Assertion Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"[FAILED] Unexpected Error: {e}")
        sys.exit(1)
