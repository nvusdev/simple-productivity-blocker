import sys
import os

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from blockers.dns_server import DomainMatcher

def test_nuclear_matching():
    print("--- Verifying Nuclear Keyword Matching ---")
    
    # Verify that plain keywords match anywhere in the domain
    matcher = DomainMatcher(["youtube", "fb"])
    
    # Positive matches
    assert matcher.matches("youtube.com")
    assert matcher.matches("www.youtube.com")
    assert matcher.matches("myyoutube.com")
    assert matcher.matches("youtube-proxy.net")
    assert matcher.matches("fb.com")
    assert matcher.matches("facebook.com") == False # "fb" is in "facebook" only if it's a substring
    assert matcher.matches("fb-messenger.com")
    assert matcher.matches("myfb.com")
    
    # Negative matches (not containing the keyword)
    assert matcher.matches("google.com") == False
    assert matcher.matches("you-tube.com") == False # because of hyphen it's not the same string
    
    print("Pass: Nuclear matching confirmed")

    # Verify that dots disable nuclear matching
    matcher_dots = DomainMatcher(["youtube.com"])
    assert matcher_dots.matches("youtube.com")
    assert matcher_dots.matches("www.youtube.com")
    assert matcher_dots.matches("myyoutube.com") == False # dots make it an exact domain match (plus subdomains)
    print("Pass: Dots disable nuclear matching")

    print("--- ALL NUCLEAR MATCHING CASES PASSED ---")

if __name__ == "__main__":
    test_nuclear_matching()
