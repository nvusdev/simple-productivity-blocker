import os
import subprocess
import ctypes
import sys
import json
import psutil
import time
from core.subprocess_utils import run_system_command

def is_admin():
    if os.name == "nt":
        from core.win32_utils import is_admin as win_is_admin
        return win_is_admin()
    return os.getuid() == 0

def terminate_spb_processes():
    """Aggressively kill all SPB-related processes to release file handles."""
    print("[*] Terminating SPB processes...")
    procs = ["SimpleProductivityBlocker.exe", "SPB_Daemon.exe", "spb_installer.exe"]
    for proc in psutil.process_iter(['pid', 'name']):
        try:
            if proc.info['name'] in procs:
                print(f"    - Killing {proc.info['name']} (PID: {proc.info['pid']})")
                proc.kill()
        except: pass
    time.sleep(1)


def force_unlock(path):
    path = os.path.normpath(os.path.abspath(path))
    if not os.path.exists(path):
        print(f"[-] Path does not exist: {path}")
        return False

    print(f"[*] Attempting to unlock: {path}")
    try:
        # Rely purely on icacls / takeown to strip permissions and overwrite the file.
        # Aggressive handle-hunting via psutil is avoided to prevent kernel deadlocks.
        # 1. Take ownership (The Sledgehammer)
        # /f path, /a (give ownership to Administrators group)
        print("    - Taking ownership...")
        run_system_command(['takeown', '/f', path, '/a'], check=False)
        
        # 2. Grant Administrators full control
        print("    - Granting Administrator access...")
        run_system_command(['icacls', path, '/grant', 'Administrators:(F)', '/c', '/q'], check=False)

        # 3. Re-enable inheritance and remove ALL deny rules
        print("    - Resetting inheritance and removing deny rules...")
        run_system_command(['icacls', path, '/reset', '/c', '/q'], check=False)
        
        # 4. Explicitly remove everyone-deny just in case reset wasn't enough
        # S-1-1-0 is the SID for 'Everyone'
        run_system_command(['icacls', path, '/remove:d', '*S-1-1-0', '/c', '/q'], check=False)
        
        print(f"[+] Successfully processed: {path}")
        return True
    except Exception as e:
        print(f"[!] Error unlocking {path}: {e}")
        return False

def restore_dns_state(config_dir):
    state_path = os.path.join(config_dir, "dns_state.json")
    if not os.path.exists(state_path):
        print("[-] No SPB DNS state file found.")
        return False
    print("[*] Restoring adapter DNS state...")
    try:
        with open(state_path, "r", encoding="utf-8") as f:
            state = json.load(f)
        eligible = set(state.get("eligible", []))
        restored = 0
        for adapter in state.get("adapters", []):
            idx = adapter.get("index")
            if idx not in eligible:
                continue
            servers = list(adapter.get("ipv4", []) or []) + list(adapter.get("ipv6", []) or [])
            if servers:
                quoted = ", ".join("'" + str(s).replace("'", "''") + "'" for s in servers)
                ps = f"Set-DnsClientServerAddress -InterfaceIndex {int(idx)} -ServerAddresses @({quoted})"
            else:
                ps = f"Set-DnsClientServerAddress -InterfaceIndex {int(idx)} -ResetServerAddresses"
            run_system_command(["powershell", "-NoProfile", "-Command", ps], check=False)
            restored += 1
        try:
            os.remove(state_path)
        except:
            pass
        print(f"[+] Restored DNS state for {restored} adapter(s).")
        return True
    except Exception as e:
        print(f"[!] Critical error during DNS restoration: {e}")
        import traceback
        traceback.print_exc()
        return False

def clear_browser_doh_policies():
    print("[*] Clearing SPB browser DoH policies...")
    try:
        import winreg
        policies = [
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Policies\Google\Chrome", "DnsOverHttpsMode"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Policies\Microsoft\Edge", "DnsOverHttpsMode"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Policies\Mozilla\Firefox\DNSOverHTTPS", "Enabled"),
        ]
        for root, path, name in policies:
            try:
                key = winreg.OpenKey(root, path, 0, winreg.KEY_SET_VALUE)
                winreg.DeleteValue(key, name)
                winreg.CloseKey(key)
            except FileNotFoundError:
                pass
            except OSError:
                pass
    except Exception as e:
        print(f"[!] Failed to clear browser policies: {e}")
        return False
    return True

def cleanup_scheduled_task():
    print("[*] Removing SPB scheduled task if present...")
    try:
        run_system_command(['schtasks', '/delete', '/tn', 'SPB_Daemon', '/f'], check=False)
    except Exception as e:
        print(f"[!] Failed to remove scheduled task: {e}")

def clean_hosts_file():
    hosts_path = os.path.join(os.environ.get('SystemRoot', 'C:\\Windows'), 'System32', 'drivers', 'etc', 'hosts')
    markers = {
        "# SPB BEGIN": "# SPB END",
        "# --- SPB Block Begin ---": "# --- SPB Block End ---",
    }
    print("[*] Cleaning SPB hosts entries...")
    try:
        with open(hosts_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        cleaned = []
        active_end = None
        for line in lines:
            stripped = line.strip()
            if active_end:
                if stripped == active_end:
                    active_end = None
                continue
            if stripped in markers:
                active_end = markers[stripped]
                continue
            if stripped.endswith("# SPB") or stripped.endswith("# ProductivityApp"):
                continue
            cleaned.append(line)
        with open(hosts_path, "w", encoding="utf-8") as f:
            f.writelines(cleaned)
        run_system_command(["ipconfig", "/flushdns"], check=False)
        print("[+] Hosts file cleaned.")
    except Exception as e:
        print(f"[!] Failed to clean hosts file: {e}")

def _get_history(config_dir: str, filename: str) -> set:
    """Safely parse recovery JSON files, resisting corruption."""
    file_path = os.path.join(config_dir, filename)
    if not os.path.exists(file_path):
        return set()
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            if not content:
                return set()
            data = json.loads(content)
            
            # Validate structure: must be a list of strings
            if isinstance(data, list):
                return {str(item) for item in data if isinstance(item, str) and item.strip()}
            return set()
    except json.JSONDecodeError as e:
        print(f"[!] Corruption detected in {filename}: {e}. Attempting raw string extraction.")
        # Fallback: regex extraction if JSON is partially corrupted
        import re
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                raw_text = f.read()
                # Extract anything that looks like a Windows path or basic string between quotes
                matches = re.findall(r'"([a-zA-Z]:\\[^"\*<>\|]+)"', raw_text)
                if matches:
                    print(f"[*] Recovered {len(matches)} paths via raw extraction.")
                    return set(matches)
        except Exception:
            pass
        return set()
    except Exception as e:
        print(f"[!] Failed to read {filename}: {e}")
        return set()

def run_auto_recovery():
    """Runs a fully automated, silent recovery to lift all locks and clean hosts."""
    print("[!] Safe Mode detected! Running automated emergency recovery...")
    config_dir = os.path.join(os.getenv('PROGRAMDATA', 'C:\\ProgramData'), 'SimpleProductivityBlocker')
    paths_to_unlock = set()
    try:
        terminate_spb_processes()
    except Exception:
        pass
    try:
        restore_dns_state(config_dir)
    except Exception:
        pass
    try:
        clear_browser_doh_policies()
    except Exception:
        pass
    try:
        cleanup_scheduled_task()
    except Exception:
        pass
    
    for fname in ["recovery.json", "recovery_history.json"]:
        try:
            recovered_paths = _get_history(config_dir, fname)
            if recovered_paths:
                paths_to_unlock.update(recovered_paths)
        except Exception:
            pass

    hosts_path = os.path.join(os.environ.get('SystemRoot', 'C:\\Windows'), 'System32', 'drivers', 'etc', 'hosts')
    paths_to_unlock.add(hosts_path)

    for p in sorted(list(paths_to_unlock)):
        try:
            force_unlock(p)
        except Exception:
            pass

    try:
        clean_hosts_file()
    except Exception:
        pass
    print("[+] Automated emergency recovery complete. All blocks lifted.")

def main():
    print("====================================================")
    print("   Simple Productivity Blocker - EMERGENCY RECOVERY")
    print("====================================================")
    
    is_silent = "--silent" in sys.argv
    
    if not is_admin():
        if is_silent:
            print("[!] ERROR: Silent recovery requires an elevated terminal.")
            sys.exit(1)
        print("[!] Administrator privileges required.")
        print("[*] Restarting with elevated privileges...")
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, subprocess.list2cmdline(sys.argv[1:]), None, 1)
        sys.exit()

    # Try to find recovery history
    config_dir = os.path.join(os.getenv('PROGRAMDATA', 'C:\\ProgramData'), 'SimpleProductivityBlocker')
    paths_to_unlock = set()
    terminate_spb_processes()
    restore_dns_state(config_dir)
    clear_browser_doh_policies()
    cleanup_scheduled_task()
    
    for fname in ["recovery.json", "recovery_history.json"]:
        recovered_paths = _get_history(config_dir, fname)
        if recovered_paths:
            print(f"[*] Found valid recovery data in: {fname}")
            paths_to_unlock.update(recovered_paths)

    # Add hosts file to the batch unlock set
    hosts_path = os.path.join(os.environ.get('SystemRoot', 'C:\\Windows'), 'System32', 'drivers', 'etc', 'hosts')
    paths_to_unlock.add(hosts_path)

    if paths_to_unlock:
        print(f"[*] Found {len(paths_to_unlock)} unique paths to restore.")
        for p in sorted(list(paths_to_unlock)):
            force_unlock(p)
    else:
        print("[-] No automated recovery history found.")

    # Now clean the hosts file content (it's already unlocked)
    clean_hosts_file()

    if not is_silent:
        print("\n--- MANUAL RECOVERY ---")
        print("If you still can't access certain files/folders, enter the path below.")
        print("Leave blank to exit.")
        
        while True:
            manual_path = input("\nEnter path to force-unlock: ").strip().strip('"')
            if not manual_path:
                break
            force_unlock(manual_path)

    print("\n[*] Recovery process complete.")
    if not is_silent:
        input("Press Enter to exit...")

if __name__ == "__main__":
    main()
