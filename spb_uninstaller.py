import os
import sys
import shutil
import ctypes
import subprocess
import time

SPB_BEGIN = "# SPB BEGIN"
SPB_END = "# SPB END"

def _strip_spb_block(lines):
    begin_idx = None
    end_idx = None
    for idx, line in enumerate(lines):
        if line.strip() == SPB_BEGIN:
            begin_idx = idx
            break

    if begin_idx is not None:
        for idx in range(begin_idx + 1, len(lines)):
            if lines[idx].strip() == SPB_END:
                end_idx = idx
                break

    if begin_idx is not None and end_idx is not None and end_idx > begin_idx:
        cleaned = lines[:begin_idx] + lines[end_idx + 1:]
    else:
        cleaned = list(lines)

    cleaned = [line for line in cleaned if not line.strip().endswith("# SPB")]
    cleaned = [line for line in cleaned if line.strip() not in (SPB_BEGIN, SPB_END)]
    return cleaned

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def kill_processes():
    print("Terminating background processes and ghost instances...")
    procs_to_kill = ["SimpleProductivityBlocker.exe", "SPB_Daemon.exe", "python.exe", "pythonw.exe"]
    try:
        import psutil
        for proc in psutil.process_iter(['name', 'cmdline']):
            try:
                name = proc.info['name']
                cmd = proc.info['cmdline'] or []
                if name in ["python.exe", "pythonw.exe"]:
                    if any("SimpleProductivityBlocker" in s or "main.py" in s or "daemon.py" in s for s in cmd):
                        proc.kill()
                elif name in ["SimpleProductivityBlocker.exe", "SPB_Daemon.exe"]:
                    proc.kill()
            except:
                continue
    except:
        pass
    time.sleep(2)

def remove_scheduled_task():
    print("Removing Scheduled Tasks and Registry entries...")
    try:
        subprocess.run(['schtasks', '/delete', '/tn', 'SPB_Daemon', '/f'], capture_output=True)
        # Clear legacy registry entry
        import winreg
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE)
        winreg.DeleteValue(key, "SimpleProductivityBlocker")
    except:
        pass

def restore_hosts():
    print("Restoring hosts file...")
    hosts_path = os.path.join(os.environ.get('SystemRoot', 'C:\\Windows'), 'System32', 'drivers', 'etc', 'hosts')
    backup_path = hosts_path + '.backup'
    
    if os.path.exists(backup_path):
        try:
            shutil.copy2(backup_path, hosts_path)
            print("Hosts file restored from backup.")
        except Exception as e:
            print(f"Failed to restore hosts file: {e}")
    else:
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
            
    print("Flushing DNS...")
    subprocess.run(["ipconfig", "/flushdns"], capture_output=True)

def remove_files():
    dest_dir = os.path.join(os.environ.get("ProgramFiles", "C:\\Program Files"), "Simple Productivity Blocker")
    if os.path.exists(dest_dir):
        print(f"Removing installation directory: {dest_dir}")
        try:
            shutil.rmtree(dest_dir)
        except Exception as e:
            print(f"Failed to remove installation directory: {e}")
            
    config_dir = os.path.join(os.getenv('PROGRAMDATA', 'C:\\ProgramData'), 'SimpleProductivityBlocker')
    if os.path.exists(config_dir):
        print(f"Removing configuration and cache: {config_dir}")
        try:
            shutil.rmtree(config_dir)
        except Exception as e:
            print(f"Failed to remove config directory: {e}")
            
    desktop = os.path.join(os.environ["USERPROFILE"], "Desktop")
    shortcut_path = os.path.join(desktop, "Simple Productivity Blocker.lnk")
    if os.path.exists(shortcut_path):
        print("Removing desktop shortcut...")
        try:
            os.remove(shortcut_path)
        except:
            pass

def main():
    print("Welcome to the Simple Productivity Blocker Uninstaller")
    print("-------------------------------------------------------")
    
    if not is_admin():
        print("Administrator privileges required. Requesting UAC prompt...")
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv), None, 1)
        sys.exit()
        
    confirm = input("Are you sure you want to completely remove Simple Productivity Blocker? (y/n): ")
    if confirm.lower() != 'y':
        print("Uninstallation cancelled.")
        time.sleep(2)
        sys.exit(0)
        
    kill_processes()
    remove_scheduled_task()
    restore_hosts()
    remove_files()
    
    print("\nUninstallation Complete.")
    print("All files, blocks, and configurations have been successfully removed.")
    input("\nPress Enter to exit...")

if __name__ == "__main__":
    main()
