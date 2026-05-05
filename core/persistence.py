import os
import sys
import subprocess

def set_startup(enabled: bool, name="SimpleProductivityBlocker"):
    if os.name == 'nt':
        return _set_startup_windows(enabled, name)
    else:
        return _set_startup_linux(enabled, name)

def _set_startup_windows(enabled: bool, name: str):
    import winreg
    key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
    
    if getattr(sys, 'frozen', False):
        app_path = f'"{sys.executable}"'
    else:
        # Development mode
        main_py = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "main.py")
        app_path = f'"{sys.executable}" "{main_py}"'

    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE)
        if enabled:
            winreg.SetValueEx(key, name, 0, winreg.REG_SZ, app_path)
        else:
            try:
                winreg.DeleteValue(key, name)
            except FileNotFoundError:
                pass
        winreg.CloseKey(key)
        return True
    except Exception as e:
        print(f"Failed to set Windows startup: {e}")
        return False

def is_startup_enabled(name="SimpleProductivityBlocker"):
    if os.name == 'nt':
        import winreg
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_READ)
            winreg.QueryValueEx(key, name)
            winreg.CloseKey(key)
            return True
        except FileNotFoundError:
            return False
        except Exception:
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
