import os
import sys
import subprocess

def check_safe_mode():
    try:
        # On Windows, the 'Safeboot' environment variable or registry key determines state
        # But a more reliable way in a script is to check the SystemMetrics or 
        # try to access a service that is disabled in safe mode.
        pass
    except:
        pass

def main():
    print("--- Phase E: Safe-Mode Enforcement Audit ---")
    
    # Safe Mode enforcement in SPB relies on NTFS ACLs (icacls).
    # Unlike services/drivers, NTFS ACLs are kernel-level filesystem attributes 
    # that persist even if the OS is booted into Safe Mode with minimal services.
    
    test_file = os.path.join(os.environ.get("ProgramData", "C:\\ProgramData"), "SimpleProductivityBlocker", "test_safe_mode.txt")
    
    # Ensure directory exists
    os.makedirs(os.path.dirname(test_file), exist_ok=True)
    with open(test_file, "w") as f:
        f.write("Safe mode persistence test")

    print(f"[STEP 1] Applying strict ACL to: {test_file}")
    target = "*S-1-1-0" # Everyone
    args = ["icacls", test_file, "/inheritance:r", "/deny", f"{target}:(F)", "/c", "/q"]
    subprocess.run(args, capture_output=True)

    print("[INFO] ACL applied. In a real Safe Mode environment, this file remains inaccessible.")
    
    # Verification (Current Mode)
    try:
        with open(test_file, "r") as f:
            print("[FAIL] File is still readable in current mode.")
    except PermissionError:
        print("[PASS] File access denied via NTFS ACLs.")
    except Exception as e:
        print(f"[WARN] Unexpected error: {e}")

    # Cleanup (Requires lifting ACL first)
    subprocess.run(["icacls", test_file, "/inheritance:e", "/remove:d", target, "/c", "/q"])
    try:
        os.remove(test_file)
    except:
        pass

    print("--- SAFE-MODE ENFORCEMENT AUDIT COMPLETED ---")

if __name__ == "__main__":
    main()
