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
try:
    import win32com.client
    import pythoncom
except ImportError:
    pass

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

def get_known_folder_path(folder_guid_str):
    """Securely resolve Windows Known Folders (Desktop, Program Files, etc)."""
    try:
        SHGetKnownFolderPath = ctypes.windll.shell32.SHGetKnownFolderPath
        SHGetKnownFolderPath.argtypes = [ctypes.POINTER(GUID), wintypes.DWORD, wintypes.HANDLE, ctypes.POINTER(ctypes.c_void_p)]
        SHGetKnownFolderPath.restype = wintypes.HRESULT
        
        folder_id = GUID(folder_guid_str)
        path_ptr = ctypes.c_void_p()
        
        result = SHGetKnownFolderPath(ctypes.byref(folder_id), 0, None, ctypes.byref(path_ptr))
        if result == 0:
            path = ctypes.cast(path_ptr, ctypes.c_wchar_p).value
            ctypes.windll.ole32.CoTaskMemFree(path_ptr)
            return path
    except Exception:
        pass
    return None

def get_program_files_path():
    # FOLDERID_ProgramFiles: {905e63b6-c1bf-494e-b29c-65b732d3d21a}
    path = get_known_folder_path("{905e63b6-c1bf-494e-b29c-65b732d3d21a}")
    return path or os.environ.get("ProgramFiles", "C:\\Program Files")

def get_desktop_path():
    # FOLDERID_Desktop: {B4BFCC3A-DB2C-424C-B029-7FE99A87C641}
    path = get_known_folder_path("{B4BFCC3A-DB2C-424C-B029-7FE99A87C641}")
    return path or os.path.join(os.environ["USERPROFILE"], "Desktop")

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def terminate_ghost_instances():
    """Surgically terminate any instances of the app or daemon."""
    print("\nStopping existing processes and legacy ghost instances...")
    for proc in psutil.process_iter(['name']):
        try:
            name = proc.info['name']
            if name in ["python.exe", "pythonw.exe"]:
                cmd = proc.cmdline()
                if any("SimpleProductivityBlocker" in s or "main.py" in s or "daemon.py" in s for s in cmd):
                    print(f"Terminating {name} (PID: {proc.pid})...")
                    proc.kill()
            elif name in ["SPB_Daemon.exe", "SimpleProductivityBlocker.exe"]:
                print(f"Terminating {name} (PID: {proc.pid})...")
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
    
    # If compiled, we should source from the extracted _MEIPASS directory (onefile) 
    # or the executable directory (onedir).
    if getattr(sys, 'frozen', False):
        src_dir = getattr(sys, '_MEIPASS', os.path.dirname(sys.executable))
    else:
        src_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Special check: if we are in '_internal', go up one level
    if os.path.basename(src_dir) == "_internal":
        src_dir = os.path.dirname(src_dir)
        
    print(f"Sourcing files from: {src_dir}")
    
    for item in os.listdir(src_dir):
        s = os.path.join(src_dir, item)
        d = os.path.join(dest_dir, item)
        
        # Skip the installer itself, build artifacts, and _internal (we'll handle _internal surgically)
        if item.lower() in ["spb_installer.exe", "spb_installer.py", "spb_uninstaller.exe", "spb_uninstaller.py", "_internal"]:
            continue
            
        if os.path.isfile(s):
            shutil.copy2(s, d)
        elif os.path.isdir(s) and item not in ["build", "dist", "__pycache__", ".git"]:
            if os.path.exists(d):
                try:
                    shutil.rmtree(d)
                except Exception:
                    pass
            shutil.copytree(s, d)
    
    # Surgical deployment of _internal folders from binaries
    # In --onedir builds, _internal is shared or adjacent.
    internal_src = os.path.join(src_dir, "_internal")
    if os.path.isdir(internal_src):
        internal_dest = os.path.join(dest_dir, "_internal")
        if not os.path.exists(internal_dest):
            print("Deploying system assets...")
            shutil.copytree(internal_src, internal_dest)

def harden_install_dir(dest_dir):
    """Locks the installation directory so only System/Admins can write to it."""
    print("Hardening directory permissions...")
    # SIDs: System (S-1-5-18), Admins (S-1-5-32-544), Users (S-1-5-32-545)
    # /inheritance:r = remove inheritance, /grant = give specific perms
    # OI/CI/F = Object/Container Inherit, Full Control
    # OI/CI/RX = Read/Execute
    subprocess.run([
        'icacls', dest_dir, 
        '/inheritance:r', 
        '/grant:r', '*S-1-5-18:(OI)(CI)(F)', 
        '/grant:r', '*S-1-5-32-544:(OI)(CI)(F)', 
        '/grant:r', '*S-1-5-32-545:(OI)(CI)(RX)'
    ], capture_output=True)

def register_daemon_task(daemon_path, args=""):
    """Registers the background daemon as a high-integrity scheduled task."""
    from core.persistence import register_task
    try:
        register_task("SPB_Daemon", daemon_path, args)
    except Exception as e:
        print(f"  [ERROR] Task registration failed: {e}")
        raise

def create_shortcut(target, shortcut_path, icon=None):
    """Creates a Windows shortcut (.lnk) using native COM via win32com."""
    try:
        pythoncom.CoInitialize() # Initialize COM for the thread
        shell = win32com.client.Dispatch("WScript.Shell")
        shortcut = shell.CreateShortcut(shortcut_path)
        shortcut.TargetPath = target
        shortcut.WorkingDirectory = os.path.dirname(target)
        if icon:
            shortcut.IconLocation = icon
        shortcut.Save()
        
        # Explicit cleanup to prevent "Win32 exception occurred releasing IUnknown"
        shortcut = None
        shell = None
        return True
    except Exception as e:
        print(f"Warning: Native shortcut creation failed ({e}). Falling back to PowerShell...")
        # Fallback to PowerShell if win32com fails or isn't available
        try:
            icon_cmd = f"$s.IconLocation=\\\"{icon}\\\";" if icon else ""
            ps_command = (
                f"$s=(New-Object -ComObject WScript.Shell).CreateShortcut(\\\"{shortcut_path}\\\");"
                f"$s.TargetPath=\\\"{target}\\\";"
                f"$s.WorkingDirectory=\\\"{os.path.dirname(target)}\\\";"
                f"{icon_cmd}"
                f"$s.Save()"
            )
            subprocess.run(["powershell", "-Command", ps_command], capture_output=True, check=True)
            return True
        except Exception:
            return False
    finally:
        try:
            pythoncom.CoUninitialize()
        except:
            pass

def _has_flag(name: str) -> bool:
    name = name.lower()
    return any(arg.lower() == name for arg in sys.argv[1:])

def main():
    dry_run = _has_flag("--dry-run")
    print("Simple Productivity Blocker v1.4.3 Installer")
    print("---------------------------------------------")
    if dry_run:
        print("[DRY-RUN] No system changes will be made.")
    
    if not dry_run and not is_admin():
        print("Requesting Administrator privileges...")
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv), None, 1)
        sys.exit()

    try:
        if dry_run:
            print("[DRY-RUN] Would terminate ghost instances.")
            print("[DRY-RUN] Would clean legacy registry stubs.")
        else:
            terminate_ghost_instances()
            cleanup_legacy_registry()
        
        # 1. Resolve Secure Path
        base_prog_files = get_program_files_path()
        dest_dir = os.path.join(base_prog_files, "Simple Productivity Blocker")
        
        # 3. Deploy Binaries
        if dry_run:
            print(f"[DRY-RUN] Would install files into: {dest_dir}")
        else:
            install_files(dest_dir)
        
        # 4. Harden Installation Directory (Admin-only write access)
        if dry_run:
            print(f"[DRY-RUN] Would harden install directory ACLs: {dest_dir}")
        else:
            harden_install_dir(dest_dir)
        
        # 5. Register Background Daemon (Do this AFTER hardening)
        daemon_exe = os.path.normpath(os.path.join(dest_dir, "SPB_Daemon.exe"))
        if dry_run:
            print(f"[DRY-RUN] Would register scheduled task: SPB_Daemon -> {daemon_exe}")
        else:
            register_daemon_task(daemon_exe)
        
        print("\n" + "="*50)
        print("INSTALLATION COMPLETE!")
        print("="*50)

        # 4. Create Desktop Shortcut
        desktop = get_desktop_path()
        app_path = os.path.join(dest_dir, "SimpleProductivityBlocker.exe")
        shortcut_path = os.path.join(desktop, "Simple Productivity Blocker.lnk")
        icon_loc = f"{app_path},0"
        
        if dry_run:
            print(f"[DRY-RUN] Would create desktop shortcut: {shortcut_path}")
        else:
            if create_shortcut(app_path, shortcut_path, icon=icon_loc):
                print("Desktop shortcut created successfully!")
            else:
                print("Warning: Could not create desktop shortcut automatically.")

        print("\nInstallation Complete!")
        print("v1.4.3 Hardened Engine is now active.")
        
        print("\n" + "="*50)
        print("  REBOOT RECOMMENDED")
        print("="*50)
        print("For optimal performance and full file-system protection:")
        print("1. A system reboot is recommended to ensure all blocks are active.")
        print("2. If you restore a configuration backup, a reboot is also advised.")
        print("\nThis ensures that kernel-level enforcement is correctly applied.")
        print("="*50)
        
        if not dry_run:
            time.sleep(2)

    except Exception as e:
        print(f"\nERROR during installation: {e}")
        input("Press Enter to exit...")
        sys.exit(1)

    if not dry_run:
        input("\nPress Enter to exit...")

if __name__ == "__main__":
    main()
