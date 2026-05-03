import os
import sys
import shutil
import ctypes
import subprocess
import time

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def kill_processes():
    print("Terminating background processes...")
    try:
        subprocess.run(["taskkill", "/F", "/IM", "spb.exe"], capture_output=True)
        subprocess.run(["taskkill", "/F", "/IM", "daemon.exe"], capture_output=True)
    except:
        pass
    time.sleep(2)

def remove_scheduled_task():
    print("Removing Scheduled Task...")
    try:
        subprocess.run(['schtasks', '/delete', '/tn', 'SPB_Daemon', '/f'], capture_output=True)
    except:
        pass

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
            
    print("Flushing DNS...")
    subprocess.run(["ipconfig", "/flushdns"], capture_output=True)

def remove_files():
    dest_dir = os.path.join(os.environ.get("ProgramFiles", "C:\\Program Files"), "Simple Productivity Blocker")
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

def main():
    print("Welcome to the Simple Productivity Blocker Uninstaller")
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
    remove_scheduled_task()
    restore_hosts()
    remove_files()
    
    print("\nUninstallation Complete.")
    print("All files, blocks, and configurations have been successfully removed.")
    input("\nPress Enter to exit...")

if __name__ == "__main__":
    main()
