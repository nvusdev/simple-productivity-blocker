import os
import sys
import shutil
import ctypes
import subprocess
import time
import uuid
from ctypes import wintypes

from core.win32_utils import is_admin, get_program_files_path, get_desktop_path
from core.subprocess_utils import run_system_command

SPB_BEGIN = "# SPB BEGIN"
SPB_END = "# SPB END"
SPB_BLOCK_BEGIN = "# --- SPB Block Begin ---"
SPB_BLOCK_END = "# --- SPB Block End ---"

def _strip_spb_block(lines):
    begin_idx = None
    end_idx = None
    for idx, line in enumerate(lines):
        if line.strip() in (SPB_BEGIN, SPB_BLOCK_BEGIN):
            begin_idx = idx
            break

    if begin_idx is not None:
        for idx in range(begin_idx + 1, len(lines)):
            if lines[idx].strip() in (SPB_END, SPB_BLOCK_END):
                end_idx = idx
                break

    if begin_idx is not None and end_idx is not None and end_idx > begin_idx:
        cleaned = lines[:begin_idx] + lines[end_idx + 1:]
    else:
        cleaned = list(lines)

    cleaned = [line for line in cleaned if not line.strip().endswith("# SPB")]
    cleaned = [line for line in cleaned if line.strip() not in (SPB_BEGIN, SPB_END, SPB_BLOCK_BEGIN, SPB_BLOCK_END)]
    return cleaned


def kill_processes():
    print("Terminating background processes and ghost instances...")
    current_pid = os.getpid()
    procs_to_kill = ["SimpleProductivityBlocker.exe", "SPB_Daemon.exe", "spb_installer.exe", "python.exe", "pythonw.exe"]
    try:
        import psutil
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                name = proc.info['name']
                cmd = proc.info['cmdline'] or []
                pid = proc.info['pid']
                
                should_kill = False
                if name in ["python.exe", "pythonw.exe"]:
                    if any("SimpleProductivityBlocker" in s or "main.py" in s or "daemon.py" in s for s in cmd):
                        should_kill = True
                elif name in ["SimpleProductivityBlocker.exe", "SPB_Daemon.exe", "spb_installer.exe"]:
                    should_kill = True
                
                if should_kill and pid != current_pid:
                    print(f"  - Killing {name} (PID: {pid})...")
                    proc.kill()
                    # Verify death
                    try:
                        proc.wait(timeout=3)
                    except psutil.TimeoutExpired:
                        print(f"  [!] WARNING: Process {pid} did not exit gracefully. Force killing...")
                        proc.kill() # Second attempt or aggressive terminate
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
            except Exception as e:
                print(f"  [!] Error killing process: {e}")
    except ImportError:
        print("  [!] psutil not available, skipping advanced process termination.")
    except Exception as e:
        print(f"  [!] Process termination encountered an error: {e}")
    time.sleep(2)

def fallback_dns_reset():
    print("Running DNS fallback loopback reset...")
    try:
        ps = (
            "Get-DnsClientServerAddress | "
            "Where-Object { $_.ServerAddresses -contains '127.0.0.1' -or $_.ServerAddresses -contains '::1' } | "
            "ForEach-Object { Set-DnsClientServerAddress -InterfaceIndex $_.InterfaceIndex -ResetServerAddresses }"
        )
        run_system_command(["powershell", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-Command", ps], check=False, timeout=60)
        print("DNS fallback loopback reset complete.")
    except Exception as e:
        print(f"  [!] DNS fallback loopback reset failed: {e}")

def cleanup_persistence():
    print("Removing Scheduled Tasks and Registry entries...")
    try:
        # 1. Remove Task
        run_system_command(['schtasks', '/delete', '/tn', 'SPB_Daemon', '/f'], check=False)
        
        # 2. Clear registry for ALL user profiles
        import winreg
        with winreg.ConnectRegistry(None, winreg.HKEY_USERS) as hkey_users:
            idx = 0
            while True:
                try:
                    sid = winreg.EnumKey(hkey_users, idx)
                    if sid.startswith("S-1-5-21") and not sid.endswith("_Classes"):
                        try:
                            key_path = fr"{sid}\Software\Microsoft\Windows\CurrentVersion\Run"
                            with winreg.OpenKey(winreg.HKEY_USERS, key_path, 0, winreg.KEY_SET_VALUE) as key:
                                winreg.DeleteValue(key, "SimpleProductivityBlocker")
                        except FileNotFoundError:
                            pass
                    idx += 1
                except OSError:
                    break
    except Exception as e:
        print(f"Note: Persistence cleanup encountered an issue: {e}")

def restore_hosts():
    print("Restoring hosts file...")
    hosts_path = os.path.join(os.environ.get('SystemRoot', 'C:\\Windows'), 'System32', 'drivers', 'etc', 'hosts')
    backup_path = hosts_path + '.backup'
    
    # --- HARDENING: Force-clear ACLs before any operation ---
    if os.name == 'nt':
        try:
            # 1. Take ownership if we are locked out
            run_system_command(['takeown', '/f', hosts_path, '/a'], check=False)
            # 2. Grant full access to Administrators
            run_system_command(['icacls', hosts_path, '/grant', 'Administrators:(F)', '/c', '/q'], check=False)
            # 3. Reset inheritance and remove all deny rules
            run_system_command(['icacls', hosts_path, '/reset', '/c', '/q'], check=False)
        except Exception as e:
            print(f"  [!] Warning: Failed to force-clear hosts ACLs during restoration: {e}")

    if os.path.exists(backup_path):
        try:
            # Attempt to unlock backup too if it exists
            if os.name == 'nt':
                run_system_command(['icacls', backup_path, '/reset', '/c', '/q'], check=False)
            
            shutil.copy2(backup_path, hosts_path)
            print("Hosts file restored from backup.")
        except Exception as e:
            print(f"Failed to restore hosts file from backup: {e}")
            # Fallback to manual cleaning if copy fails
            _manual_clean_hosts(hosts_path)
    else:
        _manual_clean_hosts(hosts_path)
            
    print("Flushing DNS...")
    run_system_command(["ipconfig", "/flushdns"], check=False)

def restore_dns_state():
    print("Restoring adapter DNS state...")
    config_dir = os.path.join(os.getenv('PROGRAMDATA', 'C:\\ProgramData'), 'SimpleProductivityBlocker')
    state_path = os.path.join(config_dir, "dns_state.json")
    if not os.path.exists(state_path):
        print("No SPB DNS state file found.")
        fallback_dns_reset()
        return
    try:
        import json
        with open(state_path, "r", encoding="utf-8") as f:
            state = json.load(f)
        eligible = set(state.get("eligible", []))
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
        try:
            os.remove(state_path)
        except Exception as e:
            print(f"  [!] Note: Could not remove DNS state file: {e}")
        print("Adapter DNS state restored.")
    except Exception as e:
        print(f"Failed to restore adapter DNS state: {e}")
        fallback_dns_reset()

def _manual_clean_hosts(hosts_path):
    try:
        if os.path.exists(hosts_path):
            with open(hosts_path, 'r') as f:
                lines = f.readlines()
            cleaned = _strip_spb_block(lines)
            with open(hosts_path, 'w') as f:
                f.writelines(cleaned)
            print("Removed SPB entries from hosts file.")
    except Exception as e:
        print(f"Failed to clean hosts file: {e}")

def _reset_path_access(path):
    run_system_command(['takeown', '/f', path, '/a', '/r', '/d', 'Y'], check=False, timeout=30)
    run_system_command(['icacls', path, '/grant', 'Administrators:(F)', '/t', '/c', '/q'], check=False, timeout=30)
    run_system_command(['icacls', path, '/reset', '/t', '/c', '/q'], check=False, timeout=30)

def _remove_installation_directory(dest_dir):
    print(f"Removing installation directory: {dest_dir}")
    _reset_path_access(dest_dir)
    try:
        shutil.rmtree(dest_dir)
        return True
    except Exception as first_err:
        print(f"  [!] Initial directory removal failed: {first_err}")

    # Surgical file cleanup retry for locked attributes/ACL drift.
    for root, dirs, files in os.walk(dest_dir, topdown=False):
        for name in files:
            fpath = os.path.join(root, name)
            try:
                run_system_command(['icacls', fpath, '/grant', 'Administrators:(F)', '/c', '/q'], check=False)
                run_system_command(['attrib', '-R', '-H', '-S', fpath], check=False)
                os.chmod(fpath, 0o777)
                os.remove(fpath)
            except Exception as e:
                print(f"  [!] Could not remove file '{fpath}': {e}")
        for name in dirs:
            dpath = os.path.join(root, name)
            try:
                run_system_command(['icacls', dpath, '/grant', 'Administrators:(F)', '/c', '/q'], check=False)
                run_system_command(['attrib', '-R', '-H', '-S', dpath], check=False)
                os.rmdir(dpath)
            except Exception:
                pass

    try:
        os.rmdir(dest_dir)
        return True
    except Exception as final_err:
        print(f"Failed to remove installation directory: {final_err}")
        return False

def remove_files(preserve_config=False):
    base_prog_files = get_program_files_path()
    dest_dir = os.path.join(base_prog_files, "Simple Productivity Blocker")
    if os.path.exists(dest_dir):
        _remove_installation_directory(dest_dir)
             
    config_dir = os.path.join(os.getenv('PROGRAMDATA', 'C:\\ProgramData'), 'SimpleProductivityBlocker')
    if preserve_config:
        print(f"Preserving configuration directory: {config_dir}")
    elif os.path.exists(config_dir):
        print(f"Removing configuration and cache: {config_dir}")
        try:
            shutil.rmtree(config_dir)
        except Exception as e:
            print(f"Failed to remove config directory: {e}")
            
    desktop = get_desktop_path()
    shortcut_path = os.path.join(desktop, "Simple Productivity Blocker.lnk")
    if os.path.exists(shortcut_path):
        print("Removing desktop shortcut...")
        try:
            os.remove(shortcut_path)
        except Exception as e:
            print(f"  [!] Note: Could not remove desktop shortcut: {e}")

def cleanup_acls():
    """Removes all NTFS ACL blocks before uninstallation to prevent permanent lockouts."""
    print("Releasing all physical file/folder blocks...")
    config_dir = os.path.join(os.getenv('PROGRAMDATA', 'C:\\ProgramData'), 'SimpleProductivityBlocker')
    
    # Support current, legacy, and daemon-specific recovery files
    paths = set()
    history_files = ["recovery.json", "recovery_history.json", "recovery_v142.json"]
    
    for fname in history_files:
        h_file = os.path.join(config_dir, fname)
        if os.path.exists(h_file):
            try:
                import json
                with open(h_file, 'r') as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        paths.update(data)
            except Exception as e:
                print(f"  [!] Warning: Failed to parse recovery history file '{fname}': {e}")

    # Always add the hosts file to the cleanup set
    hosts_path = os.path.join(os.environ.get('SystemRoot', 'C:\\Windows'), 'System32', 'drivers', 'etc', 'hosts')
    paths.add(hosts_path)

    target = "*S-1-1-0" # Everyone
    for path in paths:
        path = os.path.normpath(path)
        if os.path.exists(path):
            try:
                # 1. Take ownership (The Sledgehammer)
                run_system_command(['takeown', '/f', path, '/a'], check=False)
                
                # 2. Grant Administrators full control
                run_system_command(['icacls', path, '/grant', 'Administrators:(F)', '/c', '/q'], check=False)

                # 3. Restore inheritance (Critical for UI access)
                run_system_command(['icacls', path, '/inheritance:e', '/c', '/q'], check=False)
                
                # 4. Explicitly remove everyone-deny
                run_system_command(['icacls', path, '/remove:d', target, '/c', '/q'], check=False)
                
                # 5. Reset to default state if possible
                run_system_command(['icacls', path, '/reset', '/c', '/q'], check=False)
            except Exception as e:
                print(f"  [!] Failed to release block on {path}: {e}")
    
    print("Physical blocks released successfully.")

def main():
    print("Simple Productivity Blocker v1.4.10 Uninstaller")
    print("-------------------------------------------------------")
    
    import pythoncom
    
    is_silent = "--silent" in sys.argv
    preserve_config = "--preserve-config" in sys.argv
    
    if not is_admin():
        if is_silent:
            print("[!] ERROR: Silent uninstallation requires an elevated terminal.")
            sys.exit(1)
        print("Administrator privileges required. Requesting UAC prompt...")
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, subprocess.list2cmdline(sys.argv[1:]), None, 1)
        sys.exit()
        
    if not is_silent:
        confirm = input("Are you sure you want to completely remove Simple Productivity Blocker? (y/n): ")
        if confirm.lower() != 'y':
            print("Uninstallation cancelled.")
            time.sleep(2)
            sys.exit(0)
    
    try:
        pythoncom.CoInitialize()
        
        kill_processes()
        cleanup_persistence()
        restore_dns_state()
        restore_hosts()
        cleanup_acls()
        remove_files(preserve_config=preserve_config)
        
        # --- Post-Condition Audit ---
        print("\n[*] Auditing system state...")
        errors = []
        
        # 1. Verify Task is gone
        task_check = run_system_command(['schtasks', '/query', '/tn', 'SPB_Daemon'], check=False)
        if task_check is not None and task_check.returncode == 0:
            errors.append("Scheduled Task 'SPB_Daemon' still exists.")
        elif task_check is None:
            errors.append("Failed to query scheduled task state (Command timed out or failed).")
            
        # 2. Verify Hosts is clean
        hosts_path = os.path.join(os.environ.get('SystemRoot', 'C:\\Windows'), 'System32', 'drivers', 'etc', 'hosts')
        if os.path.exists(hosts_path):
            with open(hosts_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                if "# SPB BEGIN" in content or "# --- SPB Block Begin ---" in content:
                    errors.append("SPB markers still present in hosts file.")
        
        if errors:
            raise RuntimeError("Uninstallation audit failed:\n  " + "\n  ".join(errors))
            
        print("\nUninstallation Complete.")
        print("All files, blocks, and configurations have been successfully removed.")
    except Exception as e:
        print(f"\nERROR during uninstallation: {e}")
        if not is_silent:
            input("Press Enter to exit...")
        sys.exit(1)
    finally:
        try:
            pythoncom.CoUninitialize()
        except Exception:
            pass # CoUninitialize failure is non-critical at script exit

    if not is_silent:
        input("\nPress Enter to exit...")

if __name__ == "__main__":
    main()
