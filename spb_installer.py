import os
import sys
import shutil
import ctypes
import subprocess
import time
import psutil
import winreg
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
    """Securely resolve Program Files path bypassing environment variables."""
    try:
        SHGetKnownFolderPath = ctypes.windll.shell32.SHGetKnownFolderPath
        SHGetKnownFolderPath.argtypes = [ctypes.POINTER(GUID), wintypes.DWORD, wintypes.HANDLE, ctypes.POINTER(ctypes.c_wchar_p)]
        SHGetKnownFolderPath.restype = wintypes.HRESULT
        
        # FOLDERID_ProgramFiles
        PROGRAM_FILES_GUID = "{905e63b6-c1bf-494e-b29c-65b732d3d21a}"
        folder_id = GUID(PROGRAM_FILES_GUID)
        path_ptr = ctypes.c_wchar_p()
        
        result = SHGetKnownFolderPath(ctypes.byref(folder_id), 0, None, ctypes.byref(path_ptr))
        if result == 0:
            path = path_ptr.value
            ctypes.windll.ole32.CoTaskMemFree(path_ptr)
            return path
    except Exception:
        pass
    # Fallback if API fails
    return os.environ.get("ProgramFiles", "C:\\Program Files")

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def terminate_ghost_instances():
    """Surgically terminate any instances of the app or daemon."""
    print("\nStopping existing processes and legacy ghost instances...")
    for proc in psutil.process_iter(['name', 'cmdline']):
        try:
            name = proc.info['name']
            cmd = proc.info['cmdline'] or []
            if name in ["python.exe", "pythonw.exe"]:
                if any("SimpleProductivityBlocker" in s or "main.py" in s or "daemon.py" in s for s in cmd):
                    proc.kill()
            elif name in ["SPB_Daemon.exe", "SimpleProductivityBlocker.exe"]:
                proc.kill()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    time.sleep(1)

def cleanup_legacy_registry():
    """Clear legacy startup keys for ALL users on the machine."""
    print("Cleaning legacy registry stubs...")
    try:
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
                                print(f"Cleared legacy stub for user {sid}")
                        except FileNotFoundError:
                            pass
                    idx += 1
                except OSError:
                    break
    except Exception as e:
        print(f"Note: Registry cleanup encountered an issue: {e}")

def install_files(dest_dir):
    """Handles the file deployment logic."""
    print(f"\nInstalling to: {dest_dir}")
    os.makedirs(dest_dir, exist_ok=True)
    
    src_dir = os.path.dirname(os.path.abspath(__file__))
    for item in os.listdir(src_dir):
        s = os.path.join(src_dir, item)
        d = os.path.join(dest_dir, item)
        if os.path.isfile(s) and item != "spb_installer.py":
            shutil.copy2(s, d)
        elif os.path.isdir(s) and item not in ["build", "dist", "__pycache__", ".git"]:
            if os.path.exists(d):
                shutil.rmtree(d)
            shutil.copytree(s, d)

def register_daemon_task(daemon_path):
    """Registers the background daemon as a high-integrity scheduled task."""
    print("\nRegistering Antigravity Daemon...")
    # Using 'highest' is necessary to allow the daemon to manage DNS and system processes
    subprocess.run([
        'schtasks', '/create', '/tn', 'SPB_Daemon', 
        '/tr', f'"{daemon_path}"', 
        '/sc', 'onlogon', '/rl', 'highest', '/f'
    ], capture_output=True)
    subprocess.run(['schtasks', '/run', '/tn', 'SPB_Daemon'], capture_output=True)

def create_shortcut(target, shortcut_path, icon=None):
    """Creates a Windows shortcut (.lnk) using COM via PowerShell."""
    try:
        icon_arg = f"-IconLocation '{icon}'" if icon else ""
        ps_command = (
            f"$s=(New-Object -ComObject WScript.Shell).CreateShortcut('{shortcut_path}');"
            f"$s.TargetPath='{target}';"
            f"{icon_arg};"
            f"$s.Save()"
        )
        subprocess.run(["powershell", "-Command", ps_command], capture_output=True, check=True)
        return True
    except Exception:
        return False

def main():
    print("Simple Productivity Blocker v1.3.3 Installer")
    print("---------------------------------------------")
    
    if not is_admin():
        print("Requesting Administrator privileges...")
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv), None, 1)
        sys.exit()

    try:
        terminate_ghost_instances()
        cleanup_legacy_registry()
        
        # 1. Resolve Secure Path
        base_prog_files = get_program_files_path()
        dest_dir = os.path.join(base_prog_files, "Simple Productivity Blocker")
        
        # 2. Deploy Binaries
        install_files(dest_dir)

        # 3. Register Background Task
        daemon_path = os.path.join(dest_dir, "SPB_Daemon.exe")
        register_daemon_task(daemon_path)

        # 4. Create Desktop Shortcut
        desktop = os.path.join(os.environ["USERPROFILE"], "Desktop")
        app_path = os.path.join(dest_dir, "SimpleProductivityBlocker.exe")
        shortcut_path = os.path.join(desktop, "Simple Productivity Blocker.lnk")
        icon_loc = f"{app_path},0"
        
        if create_shortcut(app_path, shortcut_path, icon=icon_loc):
            print("Desktop shortcut created successfully!")

        print("\nInstallation Complete!")
        print("v1.3.3 Antigravity Protocol is now active.")
        time.sleep(2)

    except Exception as e:
        print(f"\nERROR during installation: {e}")
        input("Press Enter to exit...")
        sys.exit(1)

    input("\nPress Enter to exit...")

if __name__ == "__main__":
    main()
