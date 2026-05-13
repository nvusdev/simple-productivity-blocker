import sys
import os
import json

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from daemon import _compute_targets, clm

def test_compute_targets():
    print("--- Verifying Target Computation Logic ---")
    
    config = {
        "settings": {
            "cloud_allowlist_enabled": True,
            "cloud_allowlist": ["git.exe", "safe.com", "*.google.com"],
            "cloud_path_keywords": ["workspace"]
        },
        "groups": {
            "group1": {
                "name": "Work",
                "enabled": True,
                "schedule": {"enabled": False}, # Always active
                "websites": ["facebook.com", "git.com", "google.com", "safe.com"],
                "apps": ["notepad.exe", "git.exe"],
                "folders": ["C:\\temp\\work", "C:\\workspace\\project"]
            }
        }
    }
    
    # Mocking config path
    ctx = _compute_targets(config, clm, "config.json")
    
    print(f"Manual Domains: {ctx.manual_domains}")
    print(f"Apps: {ctx.processes}")
    print(f"Folders: {ctx.folders}")
    
    # facebook.com should be blocked
    assert "facebook.com" in ctx.manual_domains
    # git.com should be blocked (it's not git.exe)
    assert "git.com" in ctx.manual_domains
    # safe.com should NOT be blocked (in cloud allowlist)
    assert "safe.com" not in ctx.manual_domains
    # google.com should NOT be blocked (*.google.com in cloud allowlist)
    assert "google.com" not in ctx.manual_domains
    
    # notepad.exe should be blocked
    assert "notepad.exe" in ctx.processes
    # git.exe should NOT be blocked (in cloud allowlist)
    assert "git.exe" not in ctx.processes
    
    # C:\temp\work should be blocked
    assert "C:\\temp\\work" in ctx.folders
    # C:\workspace\project should NOT be blocked (contains 'workspace' keyword)
    assert "C:\\workspace\\project" not in ctx.folders
    
    print("Pass: Target computation with cloud allowlist")
    print("--- ALL TARGET COMPUTATION CASES PASSED ---")

if __name__ == "__main__":
    test_compute_targets()
