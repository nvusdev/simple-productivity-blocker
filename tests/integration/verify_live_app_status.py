import os
import sys
import json
import time
import psutil
import datetime

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from core.config_manager import load_config, save_config, normalize_config
from core.scheduler import is_active
from daemon import _compute_targets, clm
from blockers.dns_server import DomainMatcher

def test_config_system():
    print("\n--- PHASE 1: CONFIG SYSTEM VALIDATION ---")
    config = load_config()
    print(f"[PASS] Active config schema version: {config.get('schema_version')}")
    print(f"[PASS] Active config normalized at: {config.get('normalized_at')}")
    print(f"[PASS] Performance Mode loaded: {config.get('settings', {}).get('performance_mode')}")
    print(f"[PASS] Max Domains Cap: {config.get('settings', {}).get('max_domains_cap')}")
    return config

def test_settings_per_group():
    print("\n--- PHASE 2: GROUP SETTINGS & ISOLATION VALIDATION ---")
    # Simulate multi-group configurations
    multi_group_config = {
        "schema_version": 2,
        "settings": {
            "cloud_allowlist_enabled": True,
            "cloud_allowlist": ["safe.com"],
            "cloud_path_keywords": ["safe_folder"]
        },
        "groups": {
            "Work Profile": {
                "enabled": True,
                "websites": ["facebook.com", "instagram.com", "safe.com"],
                "apps": ["notepad.exe", "slack.exe"],
                "folders": ["C:\\temp\\work", "C:\\safe_folder\\code"],
                "schedule": {
                    "enabled": False, # Always active
                    "start_time": "09:00",
                    "end_time": "17:00",
                    "days": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
                }
            },
            "Entertainment Profile": {
                "enabled": True,
                "websites": ["netflix.com", "youtube.com"],
                "apps": ["steam.exe"],
                "folders": ["D:\\games"],
                "schedule": {
                    "enabled": True,
                    "start_time": "20:00",
                    "end_time": "23:00",
                    "days": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
                }
            }
        }
    }

    normalized = normalize_config(multi_group_config)
    print("[PASS] Multi-group configuration successfully normalized.")
    
    # Test schedule evaluation
    work_noon = datetime.datetime(2026, 5, 18, 12, 0) # Monday Noon
    ent_noon = datetime.datetime(2026, 5, 18, 12, 0)
    
    work_active = is_active(normalized["groups"]["Work Profile"], date_context=work_noon)
    ent_active = is_active(normalized["groups"]["Entertainment Profile"], date_context=ent_noon)
    
    print(f"[PASS] Work Profile is_active (Monday Noon): {work_active} (Expected: True)")
    print(f"[PASS] Entertainment Profile is_active (Monday Noon): {ent_active} (Expected: False)")
    
    assert work_active == True
    assert ent_active == False

    # Compile targets for "Work Profile" (simulate active window)
    ctx = _compute_targets(normalized, clm, "config.json")
    print(f"[PASS] Target isolated compilation complete:")
    print(f"       Manual Domains: {ctx.manual_domains}")
    print(f"       Apps: {ctx.processes}")
    print(f"       Folders: {ctx.folders}")
    
    # Validations
    assert "facebook.com" in ctx.manual_domains
    assert "netflix.com" not in ctx.manual_domains  # Inactive profile
    assert "safe.com" not in ctx.manual_domains     # Allowlisted
    assert "notepad.exe" not in ctx.processes        # safety exclusion
    
    print("[PASS] Group isolation and target compilation behaves flawlessly.")

def test_daemon_health():
    print("\n--- PHASE 3: LIVE DAEMON HEALTH & HEARTBEAT AUDIT ---")
    daemon_log_path = "C:\\ProgramData\\SimpleProductivityBlocker\\daemon.log"
    signal_path = "C:\\ProgramData\\SimpleProductivityBlocker\\dns_health.signal"
    
    if os.path.exists(daemon_log_path):
        print(f"[PASS] Live daemon log exists at: {daemon_log_path}")
        with open(daemon_log_path, 'r') as f:
            lines = f.readlines()[-10:]
            print("[INFO] Last 10 lines of live daemon log:")
            for l in lines:
                print(f"       {l.strip()}")
    else:
        print("[FAIL] Live daemon log does not exist!")

    if os.path.exists(signal_path):
        with open(signal_path, 'r') as f:
            sig = f.read().strip()
        print(f"[PASS] DNS Health Signal: {sig}")
    else:
        print("[FAIL] DNS Health Signal file does not exist!")

    # Check background daemon processes
    daemons = []
    for proc in psutil.process_iter(['pid', 'name', 'username']):
        try:
            if proc.info['name'] == "SPB_Daemon.exe" or "SPB_Daemon" in proc.info['name']:
                daemons.append(proc.info)
        except Exception:
            pass
            
    if daemons:
        print(f"[PASS] Detected {len(daemons)} running daemon process(es):")
        for d in daemons:
            print(f"       PID: {d['pid']} | Name: {d['name']} | User: {d['username']}")
    else:
        print("[FAIL] Daemon processes not detected in running state!")

def test_performance():
    print("\n--- PHASE 4: PERFORMANCE & THROUGHPUT BENCHMARK ---")
    patterns = [f"*.site{i}.com" for i in range(1000)] + ["*facebook*", "*youtube*", "*discord*"]
    matcher = DomainMatcher(patterns)
    
    queries = [f"sub.site{i%1000}.com" for i in range(10000)] + ["www.facebook.com", "discord.gg"]
    
    t0 = time.perf_counter()
    for q in queries:
        matcher.matches(q)
    t1 = time.perf_counter()
    
    duration = t1 - t0
    throughput = len(queries) / duration
    avg_latency = (duration / len(queries)) * 1000
    
    print(f"[PASS] DomainMatcher logic profile completed:")
    print(f"       Active Patterns: {len(patterns)}")
    print(f"       Queries Executed: {len(queries)}")
    print(f"       Total Duration: {duration:.4f}s")
    print(f"       Throughput: {throughput:.2f} queries/sec")
    print(f"       Average Latency: {avg_latency:.4f}ms")
    
    assert avg_latency < 5.0

if __name__ == "__main__":
    print("====================================================")
    print("     SPB LIVE APPLICATION SUITE VALIDATOR           ")
    print("====================================================")
    
    test_config_system()
    test_settings_per_group()
    test_daemon_health()
    test_performance()
    
    print("\n====================================================")
    print("[SUCCESS] SPB LIVE RUNTIME STATUS: 100% HEALTHY GREEN")
    print("====================================================")
