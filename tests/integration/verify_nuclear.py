# filepath: tests/integration/verify_nuclear.py
import sys
import os

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from blockers.dns_server import DomainMatcher

def test_keyword_matching():
    print("--- Verifying Strict Keyword Matching (No Asterisks) ---")
    strict_matcher = DomainMatcher(["youtube", "fb"])
    
    # Positive Matches (Keyword is its own bounded segment)
    assert strict_matcher.matches("youtube.com"), "Failed to match root domain segment"
    assert strict_matcher.matches("www.youtube.com"), "Failed to match subdomain segment"
    assert strict_matcher.matches("fb.com"), "Failed to match short segment"
    
    # Negative Matches (Prevents false positives because there are no asterisks)
    assert not strict_matcher.matches("myyoutube.com"), "Security Risk: Plain keyword bled into 'myyoutube.com'"
    assert not strict_matcher.matches("youtube-proxy.net"), "Security Risk: Plain keyword bled across hyphen"
    assert not strict_matcher.matches("facebook.com"), "Security Risk: 'fb' substring matched inside 'facebook'"

    print("Pass: Plain keywords remain specific to their own segments.")

    print("--- Verifying Explicit Nuclear Wildcarding (With Asterisks) ---")
    wildcard_matcher = DomainMatcher(["*youtube*", "fb-*"])
    
    # Asterisks explicitly authorize substring/segment bleeding
    assert wildcard_matcher.matches("myyoutube.com"), "Failed prefix wildcard match"
    assert wildcard_matcher.matches("youtube-proxy.net"), "Failed suffix wildcard match"
    assert wildcard_matcher.matches("fb-messenger.com"), "Failed targeted suffix wildcard match"
    assert not wildcard_matcher.matches("fake-fb.com"), "Matched prefix when only suffix wildcard was provided"
    
    print("Pass: Explicit asterisks trigger nuclear wildcarding.")

    print("--- Verifying Exact Domain Matching (With Dots) ---")
    exact_matcher = DomainMatcher(["youtube.com"])
    
    assert exact_matcher.matches("youtube.com"), "Failed exact match"
    assert not exact_matcher.matches("www.youtube.com"), "Security Risk: exact domain 'youtube.com' matched 'www.youtube.com'"
    assert not exact_matcher.matches("myyoutube.com"), "Exact domain match bled into prefix domain"
    
    print("--- Verifying Subdomain Wildcarding (*.domain.com) ---")
    subdomain_matcher = DomainMatcher(["*.youtube.com"])
    assert subdomain_matcher.matches("youtube.com"), "Failed to match root domain via *. prefix"
    assert subdomain_matcher.matches("www.youtube.com"), "Failed to match subdomain via *. prefix"
    assert subdomain_matcher.matches("api.v1.youtube.com"), "Failed to match nested subdomain via *. prefix"
    
    print("Pass: Exact vs Wildcard domain matching confirmed.")
    print("--- ALL DOMAIN MATCHER CASES PASSED ---")

if __name__ == "__main__":
    test_keyword_matching()
