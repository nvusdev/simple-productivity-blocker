import os
import sys

# Mocking enough for the test
class DomainMatcher:
    def __init__(self, patterns):
        import re
        self.patterns = patterns
        self.exact_set = set()
        regex_parts = []
        for p in patterns:
            p = str(p).lower().strip()
            if not p: continue
            if "*" not in p and "." in p:
                self.exact_set.add(p)
            regex_parts.append(self.compile_pattern_str(p))
        self.regex_pattern = re.compile("|".join(regex_parts), re.IGNORECASE) if regex_parts else None

    def compile_pattern_str(self, p: str) -> str:
        import re
        p = p.lower().strip()
        if p.startswith("*."):
            base = re.escape(p[2:])
            return f"(?:^|.*\\.){base}$"
        parts = p.split('*')
        escaped_parts = [re.escape(part) for part in parts]
        core_regex = "[^.]*".join(escaped_parts)
        if "." not in p and "*" not in p:
            core_regex = f"{core_regex}[^.]*"
        
        # The updated logic from dns_server.py
        if "." not in p:
             return f"(?:^|\\.|\\\\|/){core_regex}(?:\\.|\\\\|/|$)"
        return f"(?:^|\\.){core_regex}(?:\\.|$)"

    def matches(self, val: str) -> bool:
        if not val: return False
        val = val.lower().rstrip('.')
        if val in self.exact_set: return True
        if self.regex_pattern and self.regex_pattern.search(val): return True
        return False

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

    print(f"{'Value':<40} | {'Expected':<8} | {'Actual':<8} | {'Status'}")
    print("-" * 80)
    for val, expected, desc in tests:
        actual = is_cloud_allowed(val)
        status = "✅ PASS" if actual == expected else "❌ FAIL"
        print(f"{val:<40} | {str(expected):<8} | {str(actual):<8} | {status} ({desc})")

if __name__ == "__main__":
    test_cloud_allowlist()
