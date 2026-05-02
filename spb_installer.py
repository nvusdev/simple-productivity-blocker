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
    app_exe = os.path.join(src_dir, "spb.exe")
    daemon_exe = os.path.join(src_dir, "daemon.exe")
    
    if not os.path.exists(app_exe) or not os.path.exists(daemon_exe):
        print("Error: Could not find spb.exe or daemon.exe in the installation directory.")
        print(f"Looked in: {src_dir}")
        input("Press Enter to exit...")
        sys.exit(1)
        
    dest_dir = os.path.join(os.environ.get("ProgramFiles", "C:\\Program Files"), "Simple Productivity Blocker")
    
    print(f"\nInstalling to: {dest_dir}")
    
    try:
        if not os.path.exists(dest_dir):
            os.makedirs(dest_dir)
            
        shutil.copy2(app_exe, os.path.join(dest_dir, "spb.exe"))
        shutil.copy2(daemon_exe, os.path.join(dest_dir, "daemon.exe"))
        
        # Copy _internal if it exists
        internal_src = os.path.join(src_dir, "_internal")
        internal_dest = os.path.join(dest_dir, "_internal")
        if os.path.exists(internal_src):
            if os.path.exists(internal_dest):
                shutil.rmtree(internal_dest)
            shutil.copytree(internal_src, internal_dest)
        
        print("Files copied successfully.")
    except Exception as e:
        print(f"Error copying files: {e}")
        input("Press Enter to exit...")
        sys.exit(1)
        
    desktop = os.path.join(os.environ["USERPROFILE"], "Desktop")
    shortcut_path = os.path.join(desktop, "Simple Productivity Blocker.lnk")
    
    if create_shortcut(os.path.join(dest_dir, "spb.exe"), shortcut_path):
        print("\nDesktop shortcut created successfully!")
    else:
        print("\nWarning: Failed to create desktop shortcut. You may need to run 'pip install pywin32'.")
        
    print("\nInstallation Complete!")
    print("You can now run 'Simple Productivity Blocker' from your desktop.")
    input("\nPress Enter to exit...")

if __name__ == "__main__":
    main()
