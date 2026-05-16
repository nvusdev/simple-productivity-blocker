import os
import sys

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from blockers.dns_server import DomainMatcher

def test_cloud_allowlist():
    cloud_list = ["OneDrive.exe", "*.google.com", "code.exe", "work*", "*dev*"]
    cloud_kws = ["appdata", "program files", ".vscode"]
    
    matcher = DomainMatcher(cloud_list)
    
    def is_cloud_allowed(val: str) -> bool:
        v_low = val.lower()
        if matcher.matches(v_low): return True
        for kw in cloud_kws:
            if kw in v_low: return True
        basename = os.path.basename(val).lower()
        if basename in {p.lower() for p in cloud_list}:
            return True
        return False

    tests = [
        ("C:\\Users\\You\\OneDrive.exe", True, "App path with allowed basename"),
        ("google.com", True, "Allowed domain"),
        ("sub.google.com", True, "Allowed subdomain"),
        ("C:\\Program Files\\App\\app.exe", True, "Path with allowed keyword"),
        ("C:\\Users\\You\\.vscode\\settings.json", True, "Path with dot-keyword"),
        ("C:\\Work\\project\\main.py", True, "Path with wildcard 'work*'"),
        ("C:\\Games\\Steam\\game.exe", False, "Unrelated path"),
        ("work-domain.com", True, "Domain matching 'work*'"),
        ("my-dev-site.io", True, "Broad wildcard '*dev*'"),
        ("C:\\Development\\src\\main.cpp", True, "Path matching '*dev*'"),
    ]

    for val, expected, desc in tests:
        actual = is_cloud_allowed(val)
        assert actual == expected, f"{desc}: expected {expected}, got {actual} for {val}"

    print("Pass: Cloud allowlist behavior validated against production DomainMatcher.")

if __name__ == "__main__":
    test_cloud_allowlist()
