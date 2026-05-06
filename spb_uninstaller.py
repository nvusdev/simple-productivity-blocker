import os
import sys
import shutil
import ctypes
import subprocess
import time
import uuid
from ctypes import wintypes

# --- Win32 API Helpers ---
class GUID(ctypes.Structure):
    _fields_ = [
        ("Data1", wintypes.DWORD),
        ("Data2", wintypes.WORD),
        ("Data3", wintypes.WORD),
        ("Data4", ctypes.c_byte * 8)
    ]
    def __init__(self, uuid_str):
        u = uuid.UUID(uuid_str)
        ctypes.Structure.__init__(self)
        self.Data1 = u.time_low
        self.Data2 = u.time_mid
        self.Data3 = u.time_hi_version
        for i in range(8):
            self.Data4[i] = u.bytes[8 + i]

def get_program_files_path():
    try:
        SHGetKnownFolderPath = ctypes.windll.shell32.SHGetKnownFolderPath
        # Update argtypes to accept void_p pointer
        SHGetKnownFolderPath.argtypes = [ctypes.POINTER(GUID), wintypes.DWORD, wintypes.HANDLE, ctypes.POINTER(ctypes.c_void_p)]
        SHGetKnownFolderPath.restype = wintypes.HRESULT
        PROGRAM_FILES_GUID = "{905e63b6-c1bf-494e-b29c-65b732d3d21a}"
        folder_id = GUID(PROGRAM_FILES_GUID)
        path_ptr = ctypes.c_void_p()
        result = SHGetKnownFolderPath(ctypes.byref(folder_id), 0, None, ctypes.byref(path_ptr))
        if result == 0:
            path = ctypes.cast(path_ptr, ctypes.c_wchar_p).value
            ctypes.windll.ole32.CoTaskMemFree(path_ptr)
            return path
    except Exception:
        pass
    return os.environ.get("ProgramFiles", "C:\\Program Files")

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

def cleanup_persistence():
    print("Removing Scheduled Tasks and Registry entries...")
    try:
        # 1. Remove Task
        subprocess.run(['schtasks', '/delete', '/tn', 'SPB_Daemon', '/f'], capture_output=True)
        
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
    base_prog_files = get_program_files_path()
    dest_dir = os.path.join(base_prog_files, "Simple Productivity Blocker")
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

def cleanup_acls():
    """Removes all NTFS ACL blocks before uninstallation to prevent permanent lockouts."""
    print("Releasing all physical file/folder blocks...")
    config_dir = os.path.join(os.getenv('PROGRAMDATA', 'C:\\ProgramData'), 'SimpleProductivityBlocker')
    history_file = os.path.join(config_dir, "recovery_history.json")
    
    if os.path.exists(history_file):
        try:
            import json
            with open(history_file, 'r') as f:
                paths = json.load(f)
            
            for path in paths:
                if os.path.exists(path):
                    # Remove the 'Everyone' Deny ACE
                    subprocess.run(['icacls', path, '/remove:d', '*S-1-1-0', '/c', '/q'], 
                                   capture_output=True, creationflags=0x08000000) # CREATE_NO_WINDOW
            print("Physical blocks released successfully.")
        except Exception as e:
            print(f"Warning: Could not clear all physical blocks: {e}")

def main():
    print("Simple Productivity Blocker v1.4.0 Uninstaller")
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
    cleanup_persistence()
    restore_hosts()
    cleanup_acls() # Essential before deleting history and files
    remove_files()
    
    print("\nUninstallation Complete.")
    print("All files, blocks, and configurations have been successfully removed.")
    input("\nPress Enter to exit...")

if __name__ == "__main__":
    main()
