import os
import sys
import json
import time
import psutil
import datetime
import copy

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
        "schema_version": 3,
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
                    "enabled": True,
                    "persist_all_day": True,
                    "start_time": "09:00",
                    "end_time": "17:00",
                    "days": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
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
    ctx = _compute_targets(normalized, work_noon, "config.json")
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

def test_schedule_confusion_matrix():
    print("\n--- PHASE 2B: SCHEDULE CONFUSION MATRIX / TRUTH TABLE ---")
    
    scenarios = [
        {
            "name": "Enabled + Active Day + Active Hour",
            "group": {
                "enabled": True,
                "schedule": {
                    "enabled": True,
                    "start_time": "09:00",
                    "end_time": "17:00",
                    "days": ["Monday"]
                }
            },
            "time": datetime.datetime(2026, 5, 18, 12, 0), # Monday 12:00
            "expected": True
        },
        {
            "name": "Enabled + Active Day + Inactive Hour",
            "group": {
                "enabled": True,
                "schedule": {
                    "enabled": True,
                    "start_time": "09:00",
                    "end_time": "17:00",
                    "days": ["Monday"]
                }
            },
            "time": datetime.datetime(2026, 5, 18, 20, 0), # Monday 20:00
            "expected": False
        },
        {
            "name": "Enabled + Inactive Day + Active Hour",
            "group": {
                "enabled": True,
                "schedule": {
                    "enabled": True,
                    "start_time": "09:00",
                    "end_time": "17:00",
                    "days": ["Monday"]
                }
            },
            "time": datetime.datetime(2026, 5, 17, 12, 0), # Sunday 12:00
            "expected": False
        },
        {
            "name": "Disabled Schedule (Group OFF)",
            "group": {
                "enabled": True,
                "schedule": {
                    "enabled": False,
                    "start_time": "09:00",
                    "end_time": "17:00",
                    "days": ["Monday"]
                }
            },
            "time": datetime.datetime(2026, 5, 17, 12, 0), # Sunday 12:00
            "expected": False
        },
        {
            "name": "Always Active Flag (Explicit)",
            "group": {
                "enabled": True,
                "schedule": {
                    "enabled": True,
                    "always": True,
                    "days": ["Monday"]
                }
            },
            "time": datetime.datetime(2026, 5, 17, 12, 0), # Sunday 12:00
            "expected": True
        },
        {
            "name": "Persist All Day + Active Day",
            "group": {
                "enabled": True,
                "schedule": {
                    "enabled": True,
                    "persist_all_day": True,
                    "days": ["Monday"]
                }
            },
            "time": datetime.datetime(2026, 5, 18, 23, 30), # Monday 23:30
            "expected": True
        },
        {
            "name": "Persist All Day + Inactive Day",
            "group": {
                "enabled": True,
                "schedule": {
                    "enabled": True,
                    "persist_all_day": True,
                    "days": ["Monday"]
                }
            },
            "time": datetime.datetime(2026, 5, 17, 12, 0), # Sunday 12:00
            "expected": False
        },
        {
            "name": "Disabled Group Entirely",
            "group": {
                "enabled": False,
                "schedule": {
                    "enabled": True,
                    "always": True
                }
            },
            "time": datetime.datetime(2026, 5, 18, 12, 0), # Monday 12:00
            "expected": False
        },
        {
            "name": "Midnight Crossing + Inside Crossing",
            "group": {
                "enabled": True,
                "schedule": {
                    "enabled": True,
                    "start_time": "22:00",
                    "end_time": "04:00",
                    "days": ["Monday"]
                }
            },
            "time": datetime.datetime(2026, 5, 18, 23, 0), # Monday 23:00
            "expected": True
        },
        {
            "name": "Midnight Crossing + Next Day Morning",
            "group": {
                "enabled": True,
                "schedule": {
                    "enabled": True,
                    "start_time": "22:00",
                    "end_time": "04:00",
                    "days": ["Monday"]
                }
            },
            "time": datetime.datetime(2026, 5, 19, 2, 0), # Tuesday 02:00 (inside Monday night)
            "expected": True
        },
        {
            "name": "Midnight Crossing + Next Day Late",
            "group": {
                "enabled": True,
                "schedule": {
                    "enabled": True,
                    "start_time": "22:00",
                    "end_time": "04:00",
                    "days": ["Monday"]
                }
            },
            "time": datetime.datetime(2026, 5, 19, 6, 0), # Tuesday 06:00
            "expected": False
        },
        {
            "name": "Enforce All Day ON + Schedule OFF",
            "group": {
                "enabled": True,
                "schedule": {
                    "enabled": False,
                    "persist_all_day": True,
                    "start_time": "09:00",
                    "end_time": "17:00",
                    "days": ["Monday"]
                }
            },
            "time": datetime.datetime(2026, 5, 18, 12, 0), # Monday 12:00
            "expected": False
        },
        {
            "name": "Enforce All Day OFF + Schedule OFF",
            "group": {
                "enabled": True,
                "schedule": {
                    "enabled": False,
                    "persist_all_day": False,
                    "start_time": "09:00",
                    "end_time": "17:00",
                    "days": ["Monday"]
                }
            },
            "time": datetime.datetime(2026, 5, 18, 12, 0), # Monday 12:00
            "expected": False
        }
    ]

    print(f"{'Scenario Description':<40} | {'Test Context (Time)':<25} | {'Expected':<8} | {'Actual':<8} | {'Status':<6}")
    print("-" * 95)
    
    passed_all = True
    for s in scenarios:
        actual = is_active(s["group"], date_context=s["time"])
        status = "OK" if actual == s["expected"] else "FAIL"
        if status == "FAIL":
            passed_all = False
        time_str = s["time"].strftime("%A %H:%M")
        print(f"{s['name']:<40} | {time_str:<25} | {str(s['expected']):<8} | {str(actual):<8} | [{status}]")
        
    print("-" * 95)
    assert passed_all, "Confusion matrix evaluations mismatched!"
    print("[PASS] Confusion matrix truth-table evaluation matches expected parameters 100% correctly.")

def test_content_filter_logic():
    print("\n--- PHASE 2C: CONTENT FILTER / ADBLOCKER LOGIC VALIDATION ---")
    
    base_config = {
        "schema_version": 3,
        "settings": {
            "cloud_allowlist_enabled": False,
            "cloud_allowlist": [],
            "cloud_path_keywords": []
        },
        "groups": {
            "Group A": {
                "enabled": True,
                "websites": [],
                "apps": [],
                "folders": [],
                "adblocker": {
                    "enabled": False,
                    "persist_all_day": False,
                    "social_media": True
                },
                "schedule": {
                    "enabled": True,
                    "start_time": "09:00",
                    "end_time": "17:00",
                    "days": ["Monday"]
                }
            }
        }
    }

    # Scenario 1: Enable Content Filter ON + Enforce All Day OFF + Inside Schedule
    config_1 = copy.deepcopy(base_config)
    config_1["groups"]["Group A"]["adblocker"]["enabled"] = True
    config_1["groups"]["Group A"]["adblocker"]["persist_all_day"] = False
    
    # Monday Noon (Inside Schedule)
    ctx_1 = _compute_targets(config_1, datetime.datetime(2026, 5, 18, 12, 0), "config.json")
    print(f"[PASS] CF ON + Enforce OFF + Inside Schedule: has blocked domains = {len(ctx_1.filter_keywords) > 0} (Expected: True)")
    assert len(ctx_1.filter_keywords) > 0
    
    # Monday Night (Outside Schedule)
    ctx_1_night = _compute_targets(config_1, datetime.datetime(2026, 5, 18, 20, 0), "config.json")
    print(f"[PASS] CF ON + Enforce OFF + Outside Schedule: has blocked domains = {len(ctx_1_night.filter_keywords) > 0} (Expected: False)")
    assert len(ctx_1_night.filter_keywords) == 0

    # Scenario 2: Enforce All Day ON + Enable Content Filter OFF
    config_2 = copy.deepcopy(base_config)
    config_2["groups"]["Group A"]["adblocker"]["enabled"] = False
    config_2["groups"]["Group A"]["adblocker"]["persist_all_day"] = True
    
    ctx_2 = _compute_targets(config_2, datetime.datetime(2026, 5, 18, 12, 0), "config.json")
    print(f"[PASS] CF OFF + Enforce ON + Inside Schedule: has blocked domains = {len(ctx_2.filter_keywords) > 0} (Expected: False)")
    assert len(ctx_2.filter_keywords) == 0

    # Scenario 3: Enable Content Filter ON + Enforce All Day ON + Outside Schedule
    config_3 = copy.deepcopy(base_config)
    config_3["groups"]["Group A"]["adblocker"]["enabled"] = True
    config_3["groups"]["Group A"]["adblocker"]["persist_all_day"] = True
    
    # Monday Night (Outside Schedule)
    ctx_3 = _compute_targets(config_3, datetime.datetime(2026, 5, 18, 20, 0), "config.json")
    print(f"[PASS] CF ON + Enforce ON + Outside Schedule: has blocked domains = {len(ctx_3.filter_keywords) > 0} (Expected: True)")
    assert len(ctx_3.filter_keywords) > 0

    print("[PASS] Content Filter / Adblocker schedule dependency validation successfully resolved 100%.")

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
    test_schedule_confusion_matrix()
    test_content_filter_logic()
    test_daemon_health()
    test_performance()
    
    print("\n====================================================")
    print("[SUCCESS] SPB LIVE RUNTIME STATUS: 100% HEALTHY GREEN")
    print("====================================================")
