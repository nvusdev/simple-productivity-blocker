import os
import sys
import subprocess

def set_startup(enabled: bool, name="SimpleProductivityBlocker"):
    if os.name == 'nt':
        return _set_startup_windows(enabled, name)
    else:
        return _set_startup_linux(enabled, name)

def _set_startup_windows(enabled: bool, name: str):
    """
    Upgrades persistence to Scheduled Tasks (Highest Integrity).
    Registry keys are insufficient for NTFS ACL management.
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
        daemon_path = os.path.join(exe_dir, "SPB_Daemon.exe")
        if not os.path.exists(daemon_path):
            daemon_path = sys.executable # Fallback
    else:
        # Development mode
        daemon_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "daemon.py")
        python_exe = sys.executable
        daemon_path = f'"{python_exe}" "{daemon_path}"'

    try:
        if enabled:
            # Create elevated task
            subprocess.run([
                'schtasks', '/create', '/tn', task_name,
                '/tr', f'{daemon_path}',
                '/sc', 'onlogon', '/rl', 'highest', '/f'
            ], capture_output=True, creationflags=0x08000000)
            # Run now
            subprocess.run(['schtasks', '/run', '/tn', task_name], capture_output=True, creationflags=0x08000000)
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
