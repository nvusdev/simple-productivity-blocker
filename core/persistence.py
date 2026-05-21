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
    
    try:
        from core.config_manager import load_config
        cfg = load_config()
        trigger_type = cfg.get("settings", {}).get("startup_trigger_type", "Both")
    except Exception:
        trigger_type = "Both"

    if trigger_type == "At Startup":
        trigger_ps = "$trigger = New-ScheduledTaskTrigger -AtStartup; "
        fallback_trigger = "onstart"
    elif trigger_type == "At Logon":
        trigger_ps = "$trigger = New-ScheduledTaskTrigger -AtLogOn; "
        fallback_trigger = "onlogon"
    else:
        trigger_ps = (
            "$trig1 = New-ScheduledTaskTrigger -AtStartup; "
            "$trig2 = New-ScheduledTaskTrigger -AtLogOn; "
            "$trigger = @($trig1, $trig2); "
        )
        fallback_trigger = "onlogon"
        
    ps_cmd = (
        f"$e = '{e_esc}'; "
        f"$a = '{a_esc}'; "
        f"$w = '{w_esc}'; "
        f"$action = New-ScheduledTaskAction -Execute $e {arg_part} -WorkingDirectory $w; "
        f"{trigger_ps}"
        f"$principal = New-ScheduledTaskPrincipal -GroupId 'BUILTIN\\Administrators' -RunLevel Highest; "
        f"$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -ExecutionTimeLimit 0; "
        f"Register-ScheduledTask -TaskName '{task_name}' -Action $action -Trigger $trigger -Principal $principal -Settings $settings -Force"
    )

    try:
        # Pass as a single command string to powershell
        subprocess.run(['powershell', '-Command', ps_cmd], check=True, capture_output=True, text=True)
    except (subprocess.CalledProcessError, OSError) as e:
        err_msg = e.stderr if hasattr(e, 'stderr') else str(e)
        print(f"PowerShell registration failed (WMI/CIM issue?): {err_msg}")
        print("[*] Attempting fallback registration via schtasks.exe...")
        
        # Fallback to legacy schtasks.exe (bypasses CIM repository)
        # Note: schtasks has fewer granular settings than PS, but it's more robust on broken systems.
        fallback_args = ["schtasks", "/create", "/tn", task_name, "/tr", f'"{exe_path}" {args}'.strip(), "/sc", fallback_trigger, "/ru", "BUILTIN\\Administrators", "/rl", "highest", "/f"]
        try:
            subprocess.run(fallback_args, check=True, capture_output=True, text=True)
            # Robust XML modification fallback for battery settings
            try:
                import tempfile
                xml_temp_dir = tempfile.gettempdir()
                xml_path = os.path.join(xml_temp_dir, f"spb_task_{task_name}.xml")
                # Export XML
                export_res = subprocess.run(["schtasks", "/query", "/tn", task_name, "/xml"], capture_output=True, text=True, check=True)
                xml_content = export_res.stdout
                # Modify XML
                xml_content = xml_content.replace("<DisallowStartIfOnBatteries>true</DisallowStartIfOnBatteries>", "<DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>")
                xml_content = xml_content.replace("<StopIfGoingOnBatteries>true</StopIfGoingOnBatteries>", "<StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>")
                # Write XML (UTF-8)
                with open(xml_path, "w", encoding="utf-8") as f:
                    f.write(xml_content)
                # Re-import XML
                subprocess.run(["schtasks", "/create", "/tn", task_name, "/xml", xml_path, "/f"], check=True, capture_output=True, text=True)
                # Cleanup
                if os.path.exists(xml_path):
                    os.remove(xml_path)
                print("[+] Fallback registration and XML configuration successful.")
            except Exception as xml_err:
                print(f"[-] Fallback XML modification failed: {xml_err}. Task remains registered with default settings.")
        except subprocess.CalledProcessError as f_err:
            raise RuntimeError(f"Complete registration failure. PS: {err_msg} | schtasks: {f_err.stderr}")

    # Run now and verify
    result = subprocess.run(['schtasks', '/run', '/tn', task_name], capture_output=True, creationflags=0x08000000)
    if result.returncode != 0:
        raise RuntimeError(f"Failed to start task {task_name}: {result.stderr.decode(errors='replace')}")

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
            # Register watchdog task if enabled in config settings
            try:
                from core.config_manager import load_config
                cfg = load_config()
                if cfg.get("settings", {}).get("process_watchdog_enabled", True):
                    register_watchdog_task(task_name, "SPB_Watchdog")
            except Exception as w_err:
                print(f"Failed to auto-register watchdog task: {w_err}")
        else:
            # Remove both tasks
            subprocess.run(['schtasks', '/delete', '/tn', task_name, '/f'], capture_output=True, creationflags=0x08000000)
            subprocess.run(['schtasks', '/delete', '/tn', 'SPB_Watchdog', '/f'], capture_output=True, creationflags=0x08000000)
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

def register_watchdog_task(daemon_task_name="SPB_Daemon", watchdog_task_name="SPB_Watchdog"):
    """Registers the watchdog process task to monitor and restart SPB_Daemon if killed."""
    if os.name != 'nt':
        return False
        
    cmd_args = f"-NoProfile -WindowStyle Hidden -Command \"`$running = Get-Process -Name 'SPB_Daemon' -ErrorAction SilentlyContinue; if (-not `$running) {{ Start-ScheduledTask -TaskName '{daemon_task_name}' }}\""
    
    try:
        from core.config_manager import load_config
        cfg = load_config()
        trigger_type = cfg.get("settings", {}).get("startup_trigger_type", "Both")
    except Exception:
        trigger_type = "Both"

    if trigger_type == "At Startup":
        trigger_ps = (
            "$trigger = New-ScheduledTaskTrigger -AtStartup; "
            "$rep = (New-ScheduledTaskTrigger -Once -At (Get-Date) -RepetitionInterval (New-TimeSpan -Minutes 1)).Repetition; "
            "$trigger.Repetition = $rep; "
        )
    elif trigger_type == "At Logon":
        trigger_ps = (
            "$trigger = New-ScheduledTaskTrigger -AtLogOn; "
            "$rep = (New-ScheduledTaskTrigger -Once -At (Get-Date) -RepetitionInterval (New-TimeSpan -Minutes 1)).Repetition; "
            "$trigger.Repetition = $rep; "
        )
    else:
        trigger_ps = (
            "$trig1 = New-ScheduledTaskTrigger -AtStartup; "
            "$trig2 = New-ScheduledTaskTrigger -AtLogOn; "
            "$rep = (New-ScheduledTaskTrigger -Once -At (Get-Date) -RepetitionInterval (New-TimeSpan -Minutes 1)).Repetition; "
            "$trig1.Repetition = $rep; "
            "$trig2.Repetition = $rep; "
            "$trigger = @($trig1, $trig2); "
        )
        
    ps_cmd = (
        f"$action = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument '{cmd_args}'; "
        f"{trigger_ps}"
        f"$principal = New-ScheduledTaskPrincipal -GroupId 'BUILTIN\\Administrators' -RunLevel Highest; "
        f"$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -ExecutionTimeLimit 0; "
        f"Register-ScheduledTask -TaskName '{watchdog_task_name}' -Action $action -Trigger $trigger -Principal $principal -Settings $settings -Force"
    )
    try:
        subprocess.run(['powershell', '-Command', ps_cmd], check=True, capture_output=True, text=True)
        return True
    except Exception as e:
        print(f"Failed to register watchdog task via PowerShell: {e}")
        # Fallback to schtasks
        fallback_cmd = [
            "schtasks", "/create", "/tn", watchdog_task_name,
            "/tr", f"powershell.exe -NoProfile -WindowStyle Hidden -Command \"\\$running = Get-Process -Name 'SPB_Daemon' -ErrorAction SilentlyContinue; if (-not \\$running) {{ Start-ScheduledTask -TaskName '{daemon_task_name}' }}\"",
            "/sc", "minute", "/mo", "1", "/ru", "BUILTIN\\Administrators", "/rl", "highest", "/f"
        ]
        try:
            subprocess.run(fallback_cmd, check=True, capture_output=True, text=True)
            return True
        except Exception as f_err:
            print(f"Fallback watchdog registration failed: {f_err}")
            return False

def set_process_watchdog(enabled: bool, daemon_task_name="SPB_Daemon", watchdog_task_name="SPB_Watchdog") -> bool:
    """Enables or disables/deletes the process watchdog task based on user setting."""
    if os.name != 'nt':
        return False
    try:
        if enabled:
            # Only register if startup is enabled (daemon task exists)
            if is_startup_enabled():
                register_watchdog_task(daemon_task_name, watchdog_task_name)
        else:
            # Delete watchdog task to ensure it doesn't run at all
            subprocess.run(['schtasks', '/delete', '/tn', watchdog_task_name, '/f'], capture_output=True, creationflags=0x08000000)
        return True
    except Exception as e:
        print(f"Failed to set process watchdog: {e}")
        return False
