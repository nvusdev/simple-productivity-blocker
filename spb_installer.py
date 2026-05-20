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
    import win32security
    import ntsecuritycon as con
except ImportError:
    pass

from core.win32_utils import is_admin, get_program_files_path, get_desktop_path
from core.subprocess_utils import run_system_command

def terminate_ghost_instances():
    """Surgically terminate any instances of the app or daemon."""
    print("\nStopping existing processes and legacy ghost instances...")
    current_pid = os.getpid()
    for proc in psutil.process_iter(['name']):
        try:
            name = proc.info['name']
            if name in ["python.exe", "pythonw.exe"]:
                cmd = proc.cmdline()
                if any("SimpleProductivityBlocker" in s or "main.py" in s or "daemon.py" in s for s in cmd):
                    print(f"Terminating {name} (PID: {proc.pid})...")
                    proc.kill()
            elif name in ["SPB_Daemon.exe", "SimpleProductivityBlocker.exe", "spb_installer.exe"]:
                if proc.pid != current_pid:
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
        
        # Skip the installer itself, source files, and build artifacts.
        # We explicitly WANT to copy the uninstaller and recovery helper.
        if item.lower() in ["spb_installer.exe", "spb_installer.py", "spb_uninstaller.py", "_internal"]:
            continue
            
        if os.path.isfile(s):
            if os.path.abspath(s) != os.path.abspath(d):
                shutil.copy2(s, d)
        elif os.path.isdir(s) and item not in ["build", "dist", "__pycache__", ".git"]:
            if os.path.abspath(s) != os.path.abspath(d):
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
        if os.path.abspath(internal_src) != os.path.abspath(internal_dest):
            if not os.path.exists(internal_dest):
                print("Deploying system assets...")
                shutil.copytree(internal_src, internal_dest)

def harden_install_dir(dest_dir):
    """Locks the installation directory so only System/Admins can write to it using native Win32 API for speed."""
    print("Hardening directory permissions (Native)...")
    try:
        # Define SIDs
        everyone, _, _ = win32security.LookupAccountName("", "Everyone")
        admins, _, _ = win32security.LookupAccountName("", "Administrators")
        system, _, _ = win32security.LookupAccountName("", "SYSTEM")
        users, _, _ = win32security.LookupAccountName("", "Users")

        # Create DACL
        dacl = win32security.ACL()
        
        # Add ACEs (Object Inherit + Container Inherit)
        # Administrators: Full Control
        dacl.AddAccessAllowedAceEx(win32security.ACL_REVISION, con.OBJECT_INHERIT_ACE | con.CONTAINER_INHERIT_ACE, con.FILE_ALL_ACCESS, admins)
        # SYSTEM: Full Control
        dacl.AddAccessAllowedAceEx(win32security.ACL_REVISION, con.OBJECT_INHERIT_ACE | con.CONTAINER_INHERIT_ACE, con.FILE_ALL_ACCESS, system)
        # Users: Read & Execute
        dacl.AddAccessAllowedAceEx(win32security.ACL_REVISION, con.OBJECT_INHERIT_ACE | con.CONTAINER_INHERIT_ACE, con.FILE_GENERIC_READ | con.FILE_GENERIC_EXECUTE, users)

        # Apply to directory
        # SE_FILE_OBJECT, DACL_SECURITY_INFORMATION, owner, group, dacl, sacl
        # PROTECTED_DACL_SECURITY_INFORMATION = disable inheritance
        win32security.SetNamedSecurityInfo(
            dest_dir, win32security.SE_FILE_OBJECT, 
            win32security.DACL_SECURITY_INFORMATION | win32security.PROTECTED_DACL_SECURITY_INFORMATION,
            None, None, dacl, None
        )
        return True
    except Exception as e:
        print(f"Warning: Native hardening failed ({e}). Falling back to icacls...")
        # Fallback to icacls if pywin32 is not fully functional
        run_system_command([
            'icacls', dest_dir, 
            '/inheritance:r', 
            '/grant:r', '*S-1-5-18:(OI)(CI)(F)', 
            '/grant:r', '*S-1-5-32-544:(OI)(CI)(F)', 
            '/grant:r', '*S-1-5-32-545:(OI)(CI)(RX)'
        ], check=False)
        return False

def register_daemon_task(daemon_path, args=""):
    """Registers the background daemon as a high-integrity scheduled task."""
    from core.persistence import register_task
    try:
        register_task("SPB_Daemon", daemon_path, args)
    except Exception as e:
        print(f"  [ERROR] Task registration failed: {e}")
        raise

def verify_daemon_running():
    """Ensures the daemon task is actually running after registration."""
    for _ in range(8):
        try:
            for proc in psutil.process_iter(['name']):
                if proc.info.get('name') == "SPB_Daemon.exe":
                    return True
        except Exception:
            pass
        time.sleep(1)
    return False

def uninstall_existing_installation(dest_dir):
    """If a prior install is present, run the bundled uninstaller in preserve-config mode."""
    if not os.path.isdir(dest_dir):
        return

    prior_uninstaller = os.path.join(dest_dir, "spb_uninstaller.exe")
    print("\nDetected existing installation. Starting upgrade-safe uninstall...")
    terminate_ghost_instances()
    cleanup_legacy_registry()
    run_system_command(['schtasks', '/delete', '/tn', 'SPB_Daemon', '/f'], check=False)

    if os.path.isfile(prior_uninstaller):
        result = run_system_command([prior_uninstaller, "--silent", "--preserve-config"], check=False, timeout=240)
        if result is None or result.returncode != 0:
            err = (result.stderr if result and hasattr(result, "stderr") else "").strip() if result else ""
            raise RuntimeError(f"Existing uninstall failed before upgrade. {err}".strip())
    else:
        print("Prior uninstaller missing. Continuing with best-effort cleanup.")

    # Wait briefly for file handles to clear after uninstall.
    for _ in range(10):
        if not os.path.exists(dest_dir):
            break
        time.sleep(1)

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
            run_system_command(["powershell", "-Command", ps_command], check=True)
            return True
        except Exception:
            return False
    finally:
        try:
            pythoncom.CoUninitialize()
        except:
            pass

def main():
    print("Simple Productivity Blocker v1.4.9 Installer")
    print("---------------------------------------------")
    
    import pythoncom
    
    # Check for silent flag (for automated testing)
    is_silent = "--silent" in sys.argv
    
    if not is_admin():
        if is_silent:
            print("[!] ERROR: Silent installation requires an elevated terminal.")
            sys.exit(1)
        print("Requesting Administrator privileges...")
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, subprocess.list2cmdline(sys.argv[1:]), None, 1)
        sys.exit()

    rollback_stack = []
    try:
        pythoncom.CoInitialize()
        
        terminate_ghost_instances()
        cleanup_legacy_registry()
        
        # 1. Resolve Secure Path
        base_prog_files = get_program_files_path()
        dest_dir = os.path.join(base_prog_files, "Simple Productivity Blocker")
        uninstall_existing_installation(dest_dir)

        # 3. Create Directory
        if not os.path.exists(dest_dir):
            os.makedirs(dest_dir, exist_ok=True)
            rollback_stack.append(lambda: shutil.rmtree(dest_dir, ignore_errors=True))

        # 4. Harden it FIRST (If hardening fails, we should still rollback)
        if harden_install_dir(dest_dir):
            # If we hardened it, rollback needs to take ownership to delete it
            def _rollback_hardened_dir():
                try:
                    run_system_command(['takeown', '/f', dest_dir, '/a', '/r'], check=False)
                    run_system_command(['icacls', dest_dir, '/grant', 'Administrators:(F)', '/t', '/c', '/q'], check=False)
                    shutil.rmtree(dest_dir, ignore_errors=True)
                except: pass
            # Replace previous simple rmtree with hardened version
            if rollback_stack:
                rollback_stack[-1] = _rollback_hardened_dir
            else:
                rollback_stack.append(_rollback_hardened_dir)

        # 5. Deploy Binaries
        install_files(dest_dir)
        
        # 6. Register Background Daemon
        daemon_exe = os.path.normpath(os.path.join(dest_dir, "SPB_Daemon.exe"))
        register_daemon_task(daemon_exe)
        rollback_stack.append(lambda: run_system_command(['schtasks', '/delete', '/tn', 'SPB_Daemon', '/f'], check=False))
        if not verify_daemon_running():
            raise RuntimeError("Daemon registration succeeded but SPB_Daemon.exe is not running.")
        
        # 7. Create Desktop Shortcut
        desktop = get_desktop_path()
        app_path = os.path.join(dest_dir, "SimpleProductivityBlocker.exe")
        shortcut_path = os.path.join(desktop, "Simple Productivity Blocker.lnk")
        icon_loc = f"{app_path},0"
        if create_shortcut(app_path, shortcut_path, icon=icon_loc):
            rollback_stack.append(lambda: os.remove(shortcut_path) if os.path.exists(shortcut_path) else None)
        
        print("\n" + "="*50)
        print("INSTALLATION COMPLETE!")
        print("="*50)

    except Exception as e:
        print(f"\n[!] ERROR during installation: {e}")
        print("[*] Initiating rollback of partial installation...")
        for undo_action in reversed(rollback_stack):
            try:
                undo_action()
            except Exception as rollback_err:
                print(f"  - Rollback warning: {rollback_err}")
        
        if not is_silent:
            input("Press Enter to exit...")
        sys.exit(1)
    finally:
        try:
            pythoncom.CoUninitialize()
        except:
            pass

    if not is_silent:
        input("\nPress Enter to exit...")

if __name__ == "__main__":
    main()
