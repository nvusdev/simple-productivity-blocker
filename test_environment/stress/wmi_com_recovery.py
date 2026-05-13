import time
import subprocess
import os
import sys
import psutil

def main():
    print("--- Phase D: WMI/COM Recovery Stress ---")
    
    # 1. Setup a dummy blocked folder for testing COM interception
    test_dir = os.path.join(os.environ.get("TEMP", "C:\\temp"), "spb_com_test")
    if not os.path.exists(test_dir):
        os.makedirs(test_dir)
    
    print(f"[INFO] Using test directory: {test_dir}")
    
    # 2. Simulate Explorer Window Storm & Termination
    # In a lab setting, we would open multiple explorer windows and then kill explorer.exe
    # To verify if SPB re-attaches to the new shell instance.
    
    print("[STEP 1] Spawning explorer windows...")
    subprocess.run(["explorer.exe", test_dir])
    time.sleep(2)
    
    print("[STEP 2] Killing explorer.exe to trigger COM/Shell re-initialization...")
    for proc in psutil.process_iter(['name']):
        if proc.info['name'].lower() == 'explorer.exe':
            try:
                proc.kill()
            except:
                pass
    
    # Wait for Explorer to restart automatically
    print("[INFO] Waiting for Explorer to restart...")
    time.sleep(5)
    
    # 3. Verification Logic
    # We check if the SPB daemon is still active and if its _watcher_thread 
    # re-acquired the Shell.Application object.
    
    print("[VERIFY] Check SPB logs for 'ProcessMonitor started' or COM re-dispatch events.")
    print("Pass: Manual check required - verify that new windows to blocked folders are still closed.")
    
    # Cleanup
    try:
        import shutil
        shutil.rmtree(test_dir)
    except:
        pass
    
    print("--- WMI/COM RECOVERY TEST COMPLETED ---")

if __name__ == "__main__":
    main()
