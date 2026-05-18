import os
import sys
import subprocess
import tempfile
import json
import time

def run_system_command(args, check=True):
    return subprocess.run(args, capture_output=True, text=True, check=check)

def main():
    print("====================================================")
    print("   SPB STRESS TEST - INSTALLATION CORRUPTION       ")
    print("====================================================")

    # 1. Locate repository paths relative to this script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    repo_root = os.path.abspath(os.path.join(script_dir, "..", ".."))
    daemon_path = os.path.join(repo_root, "daemon.py")
    app_blocker_path = os.path.join(repo_root, "blockers", "app_blocker.py")
    app_blocker_tmp = app_blocker_path + ".tmp"

    print(f"[*] Repository root: {repo_root}")
    print(f"[*] App blocker path: {app_blocker_path}")

    # 2. Setup sandboxed directory
    with tempfile.TemporaryDirectory() as sandbox_dir:
        print(f"[*] Created sandbox directory: {sandbox_dir}")
        
        # Define sandboxed files
        config_path = os.path.join(sandbox_dir, "config.json")
        history_path = os.path.join(sandbox_dir, "recovery_history.json")
        test_file = os.path.join(sandbox_dir, "test_installation_corruption_lock.txt")

        # Write dummy config
        dummy_config = {
            "settings": {
                "performance_mode": "Balanced",
                "cloud_allowlist_enabled": False
            },
            "groups": {}
        }
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(dummy_config, f)

        # Create simulated locked target file
        with open(test_file, "w", encoding="utf-8") as f:
            f.write("Failsafe recovery audit content")
        
        # Apply NTFS Deny ACL to simulate an active SPB lock
        print(f"[*] Applying strict deny ACL on test file: {test_file}")
        target = "*S-1-1-0" # Everyone
        run_system_command(["icacls", test_file, "/inheritance:r", "/deny", f"{target}:(F)", "/c", "/q"], check=False)
        
        # Verify access is denied
        try:
            with open(test_file, "r") as f:
                content = f.read()
            print("[!] FAIL: File remained readable after lock! Run test as Administrator.")
            sys.exit(1)
        except PermissionError:
            print("[PASS] File is successfully locked.")

        # Write test file path to recovery history in the sandbox
        with open(history_path, "w", encoding="utf-8") as f:
            json.dump([test_file], f)

        # 3. Simulate installation corruption by renaming the blocker dependency
        print("[*] Renaming blocker dependency to trigger ImportError...")
        if not os.path.exists(app_blocker_path):
            print(f"[!] FAIL: Could not find dependency at {app_blocker_path}")
            sys.exit(1)
        
        os.rename(app_blocker_path, app_blocker_tmp)

        # 4. Launch the daemon under sandboxed environment
        print("[*] Spawning daemon under sandboxed conditions...")
        env = os.environ.copy()
        env["SPB_DATA_DIR"] = sandbox_dir
        env["SPB_GHOST_MODE"] = "1"

        try:
            # The daemon should raise ImportError, run recovery, and exit with code 1 immediately.
            result = subprocess.run(
                [sys.executable, daemon_path],
                env=env,
                capture_output=True,
                text=True,
                timeout=10
            )
            print(f"[*] Daemon execution complete. Return code: {result.returncode}")
            
            # Print output for debugging in case of failure
            if result.returncode != 1:
                print(f"[!] Warning: Expected return code 1, got {result.returncode}")
                print(f"Daemon STDOUT:\n{result.stdout}")
                print(f"Daemon STDERR:\n{result.stderr}")
        except subprocess.TimeoutExpired:
            print("[!] FAIL: Daemon hung or timed out.")
            sys.exit(1)
        finally:
            # Always restore the blocker dependency immediately
            print("[*] Restoring blocker dependency...")
            if os.path.exists(app_blocker_tmp):
                os.rename(app_blocker_tmp, app_blocker_path)
            else:
                print("[!] ERROR: Temp backup file missing!")

        # 5. Assertions to verify the fail-safe recovery successfully completed
        print("[*] Performing assertions...")

        # A. Assert test file remains locked (fail-closed behavior)
        try:
            with open(test_file, "r") as f:
                content = f.read()
            print("[FAIL] NTFS lock was lifted! Eager import failure did not fail closed.")
            sys.exit(1)
        except PermissionError:
            print("[PASS] NTFS lock remained active under fail-closed eager import failure!")

        # B. Check that dns_health.signal indicates CRITICAL ERROR
        signal_path = os.path.join(sandbox_dir, "dns_health.signal")
        if os.path.exists(signal_path):
            with open(signal_path, "r") as f:
                signal_status = f.read().strip()
            if signal_status == "CRITICAL ERROR":
                print("[PASS] health monitor signal updated correctly.")
            else:
                print(f"[FAIL] Health monitor signal has unexpected status: {signal_status}")
                sys.exit(1)
        else:
            print("[FAIL] health monitor signal was not written.")
            sys.exit(1)

        # C. Check log file to confirm the fatal exception and recovery triggers
        log_path = os.path.join(sandbox_dir, "daemon.log")
        if os.path.exists(log_path):
            with open(log_path, "r", encoding="utf-8") as f:
                log_data = f.read()
            if "FATAL: Protection modules failed to load" in log_data:
                print("[PASS] Daemon log correctly captured the ImportError.")
            else:
                print("[WARN] ImportError was not found in daemon log.")
        else:
            print("[WARN] Daemon log was not created.")

        print("[*] Cleaning up NTFS rules for test file...")
        run_system_command(["icacls", test_file, "/inheritance:e", "/remove:d", target, "/c", "/q"], check=False)

    print("\n[SUCCESS] INSTALLATION CORRUPTION FAIL-SAFE RESILIENCE VALIDATED GREEN!")
    sys.exit(0)

if __name__ == "__main__":
    main()
