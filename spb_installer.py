import os
import sys
import shutil
import ctypes

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def create_shortcut(target, shortcut_path, icon=None):
    try:
        import win32com.client
        shell = win32com.client.Dispatch("WScript.Shell")
        shortcut = shell.CreateShortCut(shortcut_path)
        shortcut.Targetpath = target
        shortcut.WorkingDirectory = os.path.dirname(target)
        if icon:
            shortcut.IconLocation = icon
        shortcut.save()
        return True
    except Exception as e:
        print(f"Error creating shortcut: {e}")
        return False

def main():
    print("Welcome to the Simple Productivity Blocker Installer!")
    print("-----------------------------------------------------")
    
    if not is_admin():
        print("Administrator privileges required for installation. Requesting UAC prompt...")
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv), None, 1)
        sys.exit()
        
    src_dir = os.path.dirname(os.path.abspath(sys.executable if getattr(sys, 'frozen', False) else __file__))
    app_exe = os.path.join(src_dir, "SimpleProductivityBlocker.exe")
    daemon_exe = os.path.join(src_dir, "SPB_Daemon.exe")
    uninstaller_exe = os.path.join(src_dir, "spb_uninstaller.exe")

    
    if not os.path.exists(app_exe) or not os.path.exists(daemon_exe):
        print("Error: Could not find spb.exe or daemon.exe in the installation directory.")
        print(f"Looked in: {src_dir}")
        input("Press Enter to exit...")
        sys.exit(1)
        
    dest_dir = os.path.join(os.environ.get("ProgramFiles", "C:\\Program Files"), "Simple Productivity Blocker")
    
    print(f"\nInstalling to: {dest_dir}")
    
    try:
        import subprocess
        import time

        print("\nStopping existing processes for update...")
        # Try to stop them nicely first, then force
        procs_to_kill = ["SPB_Daemon.exe", "SimpleProductivityBlocker.exe"]
        for proc in procs_to_kill:
            subprocess.run(["taskkill", "/F", "/IM", proc], capture_output=True)
        
        # Short wait to ensure handles are released
        time.sleep(2)

        if not os.path.exists(dest_dir):
            os.makedirs(dest_dir)
            
        print("Copying new application files...")
        shutil.copy2(app_exe, os.path.join(dest_dir, "SimpleProductivityBlocker.exe"))
        shutil.copy2(daemon_exe, os.path.join(dest_dir, "SPB_Daemon.exe"))

        if os.path.exists(uninstaller_exe):
            shutil.copy2(uninstaller_exe, os.path.join(dest_dir, "spb_uninstaller.exe"))
        
        # Copy _internal if it exists (for PyInstaller --onedir builds)
        internal_src = os.path.join(src_dir, "_internal")
        internal_dest = os.path.join(dest_dir, "_internal")
        if os.path.exists(internal_src):
            print("Updating library components...")
            if os.path.exists(internal_dest):
                try:
                    shutil.rmtree(internal_dest)
                except Exception:
                    # If rmtree fails, try to copy over it file-by-file or warn
                    pass
            shutil.copytree(internal_src, internal_dest, dirs_exist_ok=True)
        
        print("Files updated successfully. Your configuration at ProgramData has been preserved.")
        
        print("\nRe-starting background protection...")
        daemon_dest = os.path.join(dest_dir, "SPB_Daemon.exe")

        # schtasks /run will start the daemon in the background
        subprocess.run(['schtasks', '/create', '/tn', 'SPB_Daemon', '/tr', f'"{daemon_dest}"', '/sc', 'onlogon', '/rl', 'highest', '/f'], capture_output=True)
        subprocess.run(['schtasks', '/run', '/tn', 'SPB_Daemon'], capture_output=True)
        
    except Exception as e:
        print(f"Error during update: {e}")
        print("Make sure to close all SPB windows before installing.")
        input("Press Enter to exit...")
        sys.exit(1)
        
    desktop = os.path.join(os.environ["USERPROFILE"], "Desktop")
    shortcut_path = os.path.join(desktop, "Simple Productivity Blocker.lnk")
    
    icon_location = f"{os.path.join(dest_dir, 'SimpleProductivityBlocker.exe')},0"

    if create_shortcut(os.path.join(dest_dir, "SimpleProductivityBlocker.exe"), shortcut_path, icon=icon_location):

        print("\nDesktop shortcut created successfully!")
    else:
        print("\nWarning: Failed to create desktop shortcut. You may need to run 'pip install pywin32'.")
        
    print("\nInstallation Complete!")
    print("You can now run 'Simple Productivity Blocker' from your desktop.")
    input("\nPress Enter to exit...")

if __name__ == "__main__":
    main()
