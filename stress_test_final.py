import os
import sys
import json
import time
import subprocess
import shutil
import ctypes
import datetime

# --- Configuration ---
UNIQUE_ID = int(time.time())
TEST_SANDBOX = os.path.join(os.getcwd(), f"Stress_Test_{UNIQUE_ID}")
TEST_FILE = os.path.join(TEST_SANDBOX, "blocked_file.txt")
TEST_FOLDER = os.path.join(TEST_SANDBOX, "blocked_folder")
TEST_APP_PATH = os.path.join(TEST_SANDBOX, "target_app.exe")
CONFIG_PATH = os.path.join(os.environ.get("PROGRAMDATA", "C:\\ProgramData"), "SimpleProductivityBlocker", "config.json")
LOG_FILE = os.getcwd() + f"\\stress_test_final_{UNIQUE_ID}.log"
HOSTS_PATH = os.path.join(os.environ.get("SystemRoot", "C:\\Windows"), "System32", "drivers", "etc", "hosts")

TARGET_APP_NAME = "target_app.exe"

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def log(msg):
    timestamp = datetime.datetime.now().strftime('%H:%M:%S')
    formatted_msg = f"[{timestamp}] {msg}"
    print(formatted_msg)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(formatted_msg + "\n")

def setup_sandbox():
    log(f"[*] Setting up Sandbox {TEST_SANDBOX}...")
    os.makedirs(TEST_SANDBOX, exist_ok=True)
    os.makedirs(TEST_FOLDER, exist_ok=True)
    with open(TEST_FILE, "w") as f:
        f.write("Baseline")
    
    # Copy powershell to sandbox so it's NOT in windows\system32
    ps_path = os.path.join(os.environ.get("SystemRoot", "C:\\Windows"), "System32", "WindowsPowerShell", "v1.0", "powershell.exe")
    if os.path.exists(ps_path):
        shutil.copy2(ps_path, TEST_APP_PATH)
    else:
        # Fallback to a simpler binary if PS not found
        shutil.copy2(sys.executable, TEST_APP_PATH)
        
    log("    [OK] Sandbox ready.")

def backup_config():
    if os.path.exists(CONFIG_PATH):
        shutil.copy2(CONFIG_PATH, CONFIG_PATH + ".bak")
        log("    [OK] Config backed up.")

def restore_config():
    if os.path.exists(CONFIG_PATH + ".bak"):
        shutil.move(CONFIG_PATH + ".bak", CONFIG_PATH)
        log("    [OK] Config restored.")

def write_config(config):
    with open(CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=4)

def run_test_scenario(name, config_patch, verify_fn):
    log(f"\n>>> SCENARIO: {name}")
    group_name = f"STRESS_TEST_{UNIQUE_ID}"
    config = {
        "groups": {
            group_name: {
                "enabled": True,
                "websites": [],
                "apps": [],
                "files": [],
                "folders": [],
                "schedule": {"enabled": False},
                "adblocker": {"enabled": False, "exceptions": []}
            }
        },
        "settings": {
            "performance_mode": "Aggressive",
            "cloud_allowlist_enabled": True,
            "cloud_allowlist": ["python.exe", "pythonw.exe", "SimpleProductivityBlocker.exe", "SPB_Daemon.exe", "explorer.exe"],
            "cloud_path_keywords": [] # Clear keywords to avoid system-32 exemptions
        }
    }
    if "groups" in config_patch: config["groups"][group_name].update(config_patch["groups"])
    if "settings" in config_patch: config["settings"].update(config_patch["settings"])
    write_config(config)
    log(f"    [WAIT] 30s for sync...")
    time.sleep(30)
    result = verify_fn()
    if result: log(f"    [PASS] {name}")
    else: log(f"    [FAIL] {name}")
    return result

def check_file_blocked():
    try:
        with open(TEST_FILE, "a") as f: f.write("!")
        return False
    except PermissionError: return True
    except: return False

def check_file_accessible():
    try:
        with open(TEST_FILE, "a") as f: f.write("!")
        return True
    except: return False

def check_app_blocked():
    proc = subprocess.Popen([TEST_APP_PATH, "-NoExit", "Start-Sleep 60"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    time.sleep(10)
    if proc.poll() is not None: return True
    proc.terminate()
    return False

def check_app_running():
    proc = subprocess.Popen([TEST_APP_PATH, "-NoExit", "Start-Sleep 60"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    time.sleep(10)
    if proc.poll() is None:
        proc.terminate()
        return True
    return False

def check_website_hierarchy():
    with open(HOSTS_PATH, "r") as f: content = f.read()
    return "blocked.com" in content and "excepted.com" not in content

def test_everything():
    setup_sandbox()
    backup_config()
    results = []
    try:
        results.append(run_test_scenario("Nuclear Engine", {"groups": {"files": [os.path.abspath(TEST_FILE)]}}, check_file_blocked))
        results.append(run_test_scenario("App Name Block", {"groups": {"apps": [TARGET_APP_NAME]}}, check_app_blocked))
        results.append(run_test_scenario("Allowlist Override", {"groups": {"apps": [TARGET_APP_NAME]}, "settings": {"cloud_allowlist": ["python.exe", TARGET_APP_NAME]}}, check_app_running))
        results.append(run_test_scenario("Schedule (Inactive)", {"groups": {"files": [os.path.abspath(TEST_FILE)], "schedule": {"enabled": True, "days": []}}}, check_file_accessible))
        results.append(run_test_scenario("Website Hierarchy", {"groups": {"websites": ["blocked.com"], "adblocker": {"enabled": True, "exceptions": ["excepted.com"]}}}, check_website_hierarchy))
    finally:
        restore_config()
        subprocess.run(['icacls', TEST_SANDBOX, '/inheritance:e', '/remove:d', '*S-1-1-0', '/t', '/c', '/q'], capture_output=True)
        shutil.rmtree(TEST_SANDBOX, ignore_errors=True)
    return all(results)

if __name__ == "__main__":
    if not is_admin():
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv), None, 1)
        sys.exit()
    log("="*50 + "\nFINAL STRESS TEST AUDIT\n" + "="*50)
    daemon_script = os.path.abspath("daemon.py")
    daemon_proc = subprocess.Popen([sys.executable, daemon_script], creationflags=subprocess.CREATE_NEW_CONSOLE)
    time.sleep(10)
    try:
        if test_everything(): log("\nALL TESTS PASSED! ✅")
        else: log("\nTESTS FAILED! ❌")
    finally:
        daemon_proc.terminate()
        print(f"\nFinal log saved to {LOG_FILE}")
