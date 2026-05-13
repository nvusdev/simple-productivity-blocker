import os
import sys
import subprocess

def set_startup(enabled: bool, name="SimpleProductivityBlocker"):
    if os.name == 'nt':
        return _set_startup_windows(enabled, name)
    else:
        return _set_startup_linux(enabled, name)

def register_task(task_name, exe_path, args="", working_dir=None):
    """Public helper to register a high-integrity task via PowerShell."""
    if not working_dir:
        working_dir = os.path.dirname(exe_path)
    
    # Normalize paths
    exe_path = os.path.normpath(exe_path)
    working_dir = os.path.normpath(working_dir)
    
    # Variable-based assignment with escaped single quotes is the ONLY way to reliably avoid quote hell
    # We escape ' as '' for PowerShell's single-quoted strings
    e_esc = exe_path.replace("'", "''")
    a_esc = args.replace("'", "''")
    w_esc = working_dir.replace("'", "''")
    
    arg_part = "-Argument $a" if args else ""
    ps_cmd = (
        f"$e = '{e_esc}'; "
        f"$a = '{a_esc}'; "
        f"$w = '{w_esc}'; "
        f"$action = New-ScheduledTaskAction -Execute $e {arg_part} -WorkingDirectory $w; "
        f"$trigger = New-ScheduledTaskTrigger -AtLogOn; "
        f"$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -ExecutionTimeLimit 0; "
        f"Register-ScheduledTask -TaskName '{task_name}' -Action $action -Trigger $trigger -Settings $settings -RunLevel Highest -Force"
    )

    try:
        # Pass as a single command string to powershell
        subprocess.run(['powershell', '-Command', ps_cmd], check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        print(f"PowerShell Error: {e.stderr}")
        raise RuntimeError(f"Failed to register task via PowerShell: {e.stderr}")

    # Run now and verify
    result = subprocess.run(['schtasks', '/run', '/tn', task_name], capture_output=True, creationflags=0x08000000)
    if result.returncode != 0:
        raise RuntimeError(f"Failed to start task {task_name}: {result.stderr.decode()}")

def _set_startup_windows(enabled: bool, name: str):
    """
    Upgrades persistence to Scheduled Tasks (Highest Integrity).
    """
    # 1. Clear legacy Registry Run keys (Cleanup)
    try:
        import winreg
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE)
        winreg.DeleteValue(key, name)
        winreg.CloseKey(key)
    except: pass

    # 2. Manage Scheduled Task
    task_name = "SPB_Daemon"
    
    if getattr(sys, 'frozen', False):
        exe_dir = os.path.dirname(sys.executable)
        daemon_exe = os.path.join(exe_dir, "SPB_Daemon.exe")
        if not os.path.exists(daemon_exe):
            daemon_exe = sys.executable
        args = ""
        working_dir = exe_dir
    else:
        # Development mode
        daemon_exe = sys.executable
        daemon_script = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "daemon.py")
        args = f'"{daemon_script}"'
        working_dir = os.path.dirname(daemon_script)

    try:
        if enabled:
            register_task(task_name, daemon_exe, args, working_dir)
        else:
            # Remove task
            subprocess.run(['schtasks', '/delete', '/tn', task_name, '/f'], capture_output=True, creationflags=0x08000000)
        return True
    except Exception as e:
        print(f"Failed to set Windows persistence: {e}")
        return False

def is_startup_enabled(name="SimpleProductivityBlocker"):
    if os.name == 'nt':
        # Check Scheduled Task existence
        try:
            res = subprocess.run(['schtasks', '/query', '/tn', 'SPB_Daemon'], capture_output=True, text=True, creationflags=0x08000000)
            return res.returncode == 0
        except:
            return False
    else:
        autostart_dir = os.path.expanduser("~/.config/autostart")
        return os.path.exists(os.path.join(autostart_dir, f"{name}.desktop"))

def harden_config_dir(config_dir: str) -> bool:
    if os.name != 'nt':
        return False
    if not config_dir:
        return False
    try:
        os.makedirs(config_dir, exist_ok=True)
        # System/Admins full control; Users read/execute only.
        # Tighten ACLs:
        # 1. Disable inheritance to clear ambient user permissions
        # 2. Grant SYSTEM/Admins full control
        # 3. Grant Users ONLY Read/Execute (explicitly remove Write)
        # 4. Remove CREATOR OWNER to prevent the user who created a file from editing it later
        subprocess.run([
            'icacls', config_dir,
            '/inheritance:r',
            '/grant:r', '*S-1-5-18:(OI)(CI)(F)',      # SYSTEM
            '/grant:r', '*S-1-5-32-544:(OI)(CI)(F)',   # Administrators
            '/grant:r', '*S-1-5-32-545:(OI)(CI)(RX)',  # Users (Read-Only)
            '/remove:g', '*S-1-3-0',                   # Remove CREATOR OWNER
            '/remove:g', '*S-1-5-32-545',              # Clear existing User ACEs before re-granting
            '/grant:r', '*S-1-5-32-545:(OI)(CI)(RX)'   # Re-apply strict Read-Only
        ], capture_output=True, creationflags=0x08000000)
        return True
    except Exception:
        return False

def _set_startup_linux(enabled: bool, name: str):
    autostart_dir = os.path.expanduser("~/.config/autostart")
    os.makedirs(autostart_dir, exist_ok=True)
    desktop_file = os.path.join(autostart_dir, f"{name}.desktop")
    
    if enabled:
        if getattr(sys, 'frozen', False):
            app_path = sys.executable
        else:
            main_py = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "main.py")
            app_path = f"{sys.executable} {main_py}"
            
        content = f"""[Desktop Entry]
Type=Application
Exec={app_path}
Hidden=false
NoDisplay=false
X-GNOME-Autostart-enabled=true
Name={name}
Comment=Start {name} at login
"""
        try:
            with open(desktop_file, "w") as f:
                f.write(content)
            return True
        except Exception:
            return False
    else:
        if os.path.exists(desktop_file):
            try:
                os.remove(desktop_file)
                return True
            except Exception:
                return False
        return True
