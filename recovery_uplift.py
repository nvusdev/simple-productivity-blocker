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


def is_safe_path_to_unlock(path: str) -> bool:
    """Validate path to ensure core Windows directories are protected, except hosts."""
    try:
        resolved = os.path.normcase(os.path.abspath(path))
        system_root = os.path.normcase(os.environ.get('SystemRoot', 'C:\\Windows'))
        hosts_file = os.path.normcase(os.path.join(system_root, 'System32', 'drivers', 'etc', 'hosts'))
        
        if resolved == hosts_file:
            return True
            
        if resolved == system_root or resolved.startswith(system_root + os.path.sep):
            return False
    except Exception:
        return False
    return True

def path_exists_safe(path):
    try:
        os.stat(path)
        return True
    except PermissionError:
        return True
    except OSError:
        return False

def force_unlock(path):
    path = os.path.normpath(os.path.abspath(path))
    
    if not is_safe_path_to_unlock(path):
        print(f"[!] Security rejection: Unlocking parent system directory '{path}' is not permitted.")
        return False

    if not path_exists_safe(path):
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

def check_dns_connectivity():
    import socket
    try:
        socket.gethostbyname('google.com')
        return True
    except socket.error:
        return False

def fallback_dns_reset():
    print("[*] Running DNS fallback loopback check...")
    
    # 1. Reset explicit loopbacks
    try:
        ps_loopback = (
            "Get-DnsClientServerAddress | "
            "Where-Object { $_.ServerAddresses -contains '127.0.0.1' -or $_.ServerAddresses -contains '::1' } | "
            "ForEach-Object { Set-DnsClientServerAddress -InterfaceIndex $_.InterfaceIndex -ResetServerAddresses }"
        )
        run_system_command(["powershell", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-Command", ps_loopback], check=False, timeout=60)
    except Exception as e:
        print(f"[!] Error resetting loopback DNS: {e}")
        
    # 2. Check general DNS connectivity, if it fails, aggressively reset ALL up adapters to DHCP
    print("[*] Verifying system DNS connectivity...")
    if not check_dns_connectivity():
        print("[!] DNS connectivity test failed. Aggressively resetting ALL active network adapters to DHCP...")
        try:
            ps_all = (
                "Get-NetAdapter | Where-Object {$_.Status -eq 'Up'} | "
                "ForEach-Object { Set-DnsClientServerAddress -InterfaceIndex $_.ifIndex -ResetServerAddresses }"
            )
            run_system_command(["powershell", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-Command", ps_all], check=False, timeout=60)
            
            if check_dns_connectivity():
                print("[+] DNS connectivity successfully restored via DHCP fallback.")
            else:
                print("[-] DHCP fallback applied, but DNS still cannot be resolved. Check your router/network connection.")
        except Exception as e:
            print(f"[!] Aggressive DHCP fallback failed: {e}")
    else:
        print("[+] System DNS connectivity is functional.")
        
    return True

def restore_dns_state(config_dir):
    state_path = os.path.join(config_dir, "dns_state.json")
    json_restored = False
    
    if os.path.exists(state_path):
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
                run_system_command(["powershell", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-Command", ps], check=False, timeout=60)
                restored += 1
            try:
                os.remove(state_path)
            except:
                pass
            print(f"[+] Restored DNS state for {restored} adapter(s).")
            json_restored = True
        except Exception as e:
            print(f"[!] Error during DNS restoration: {e}")
            import traceback
            traceback.print_exc()

    if not json_restored:
        print("[-] dns_state.json missing or restore failed. Reverting local loopback DNS to DHCP fallback...")
        fallback_dns_reset()
        
    return json_restored


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
        run_system_command(['schtasks', '/delete', '/tn', 'SPB_Watchdog', '/f'], check=False)
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
        print(f"[!] Corruption detected in {filename}: {e}.")
        return set()
    except Exception as e:
        print(f"[!] Failed to read {filename}: {e}")
        return set()

def run_auto_recovery():
    """Runs a fully automated, silent recovery to lift all locks and clean hosts."""
    print("[!] Safe Mode detected! Running automated emergency recovery...")
    config_dir = os.environ.get("SPB_DATA_DIR") or os.path.join(os.getenv('PROGRAMDATA', 'C:\\ProgramData'), 'SimpleProductivityBlocker')
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
    config_dir = os.environ.get("SPB_DATA_DIR") or os.path.join(os.getenv('PROGRAMDATA', 'C:\\ProgramData'), 'SimpleProductivityBlocker')
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
            try:
                manual_path = input("\nEnter path to force-unlock: ").strip().strip('"')
            except EOFError:
                break
            if not manual_path:
                break
            force_unlock(manual_path)

    print("\n[*] Recovery process complete.")
    if not is_silent:
        try:
            input("Press Enter to exit...")
        except EOFError:
            pass

if __name__ == "__main__":
    main()
