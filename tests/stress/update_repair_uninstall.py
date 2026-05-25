import argparse
import os
import sys
import subprocess
import time
import psutil
import ctypes
import winreg


class Tee:
    def __init__(self, filepath):
        self.file = open(filepath, "w", encoding="utf-8")
        self.stdout = sys.stdout

    def write(self, data):
        self.file.write(data)
        self.file.flush()
        try:
            self.stdout.write(data)
            self.stdout.flush()
        except:
            pass

    def flush(self):
        self.file.flush()
        try:
            self.stdout.flush()
        except:
            pass


def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except:
        return False


def run_command(cmd, check=True):
    print(f"[*] Running command: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if check and result.returncode != 0:
        print(f"[!] Command failed (code {result.returncode}): {result.stderr}")
        raise RuntimeError(f"Command failed: {cmd}")
    return result


def execute_test(log_path, sentinel_path):
    print("====================================================")
    print("     SPB LIFECYCLE INTEGRATION TEST SUITE           ")
    print("====================================================")

    # We will locate setup
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    sys.path.append(repo_root)
    setup_exe = os.path.join(repo_root, "dist", "spb_setup.exe")

    if not os.path.exists(setup_exe):
        print(f"[!] ERROR: Native setup compiler output not found at: {setup_exe}")
        print("[!] Please run build.ps1 first to compile spb_setup.exe.")
        with open(sentinel_path, "w", encoding="utf-8") as f:
            f.write("FAILED")
        sys.exit(1)

    print(f"[*] Verified setup executable at: {setup_exe}")

    inst_dir = os.path.join(os.environ.get("ProgramFiles", "C:\\Program Files"), "Simple Productivity Blocker")
    print(f"[*] Target installation directory: {inst_dir}")

    # Step 1: Pre-cleanup of any existing instance
    print("\n[STEP 1] Performing pre-cleanup of any existing installation...")
    try:
        # Kill processes first
        for proc in psutil.process_iter(['name']):
            try:
                if proc.info['name'] in ["SPB_Daemon.exe", "SimpleProductivityBlocker.exe", "spb_uninstaller.exe", "recovery_uplift.exe"]:
                    print(f"  - Terminating running process: {proc.info['name']} (PID: {proc.pid})")
                    proc.kill()
                    proc.wait(timeout=3)
            except Exception:
                pass

        # Check if uninstaller exists in target dir and run it silently to clean
        prior_uninstaller = os.path.join(inst_dir, "uninstall.exe")
        if os.path.exists(prior_uninstaller):
            print(f"  - Found existing uninstall.exe at {prior_uninstaller}. Running silent uninstallation...")
            subprocess.run(f'"{prior_uninstaller}" /S', shell=True, capture_output=True, timeout=60)
            
            # Wait for the uninstaller to finish and delete itself
            for _ in range(60):
                if not os.path.exists(prior_uninstaller):
                    break
                time.sleep(0.5)

        # Explicit delete task
        subprocess.run(["schtasks", "/delete", "/tn", "SPB_Daemon", "/f"], capture_output=True)
    except Exception as e:
        print(f"  - Pre-cleanup warning: {e}")

    try:
        # Step 2: Run Native Installer Silently
        print("\n[STEP 2] Running native NSIS installer silently...")
        print(f"[*] Command: {setup_exe} /S")
        t0 = time.time()
        result = subprocess.run([setup_exe, "/S"], capture_output=True, text=True, timeout=120)
        duration = time.time() - t0
        print(f"[PASS] Installer execution complete. Duration: {duration:.2f}s")

        # Step 3: Verify File Staging
        print("\n[STEP 3] Verifying staged file layout in Program Files...")
        required_files = [
            "SimpleProductivityBlocker.exe",
            "SPB_Daemon.exe",
            "uninstall.exe",
            "recovery_uplift.exe",
            "spb_uninstaller.exe",
            "spb_installer.exe",
        ]

        missing_files = []
        # Give the installer up to 5 seconds to finish writing files in case of background staging
        for _ in range(5):
            missing_files = [f for f in required_files if not os.path.exists(os.path.join(inst_dir, f))]
            if not missing_files:
                break
            time.sleep(1)

        if missing_files:
            raise RuntimeError(f"Staging layout verification failed. Missing files: {missing_files}")
        else:
            print("[PASS] All native executable files staged correctly.")

        # Step 4: Verify Task Registration
        print("\n[STEP 4] Verifying native Scheduled Task registration...")
        task_check = subprocess.run(["schtasks", "/query", "/tn", "SPB_Daemon"], capture_output=True, text=True)
        if task_check.returncode == 0:
            print("[PASS] Scheduled Task 'SPB_Daemon' successfully registered.")
        else:
            raise RuntimeError(f"Scheduled Task 'SPB_Daemon' is missing from the system: {task_check.stderr}")

        # Step 5: Verify Background Daemon Running
        print("\n[STEP 5] Verifying background daemon execution...")
        daemon_running = False
        for _ in range(15):
            for proc in psutil.process_iter(['name']):
                try:
                    if proc.info['name'] == "SPB_Daemon.exe":
                        daemon_running = True
                        break
                except Exception:
                    pass
            if daemon_running:
                break
            time.sleep(1)

        if daemon_running:
            print("[PASS] SPB_Daemon.exe is successfully running in background (SYSTEM context).")
        else:
            raise RuntimeError("SPB_Daemon.exe process is not running after scheduled task trigger.")

        # Step 6: Verify Add/Remove Programs Registry Key
        print("\n[STEP 6] Verifying Add/Remove Programs registry registration...")
        reg_key_path = r"Software\Microsoft\Windows\CurrentVersion\Uninstall\Simple Productivity Blocker"
        key = None
        for access in [winreg.KEY_READ | winreg.KEY_WOW64_64KEY, winreg.KEY_READ | winreg.KEY_WOW64_32KEY, winreg.KEY_READ]:
            try:
                key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, reg_key_path, 0, access)
                break
            except Exception:
                continue

        if key is not None:
            try:
                publisher, _ = winreg.QueryValueEx(key, "Publisher")
                version, _ = winreg.QueryValueEx(key, "DisplayVersion")
                from core import __version__ as expected_version
                if publisher == "nvusdev" and version == expected_version:
                    print("[PASS] Add/Remove Programs registry key correctly registered.")
                else:
                    raise RuntimeError(f"Registry values mismatched: Publisher={publisher}, Version={version}")
                winreg.CloseKey(key)
            except Exception as e:
                raise RuntimeError(f"Failed to query registry values: {e}")
        else:
            raise RuntimeError("Could not find Add/Remove Programs registry key in 32-bit or 64-bit registry views.")

        # Step 7: Run Uninstaller Silently
        print("\n[STEP 7] Running native uninstaller silently...")
        uninstaller_exe = os.path.join(inst_dir, "uninstall.exe")
        print(f"[*] Command: {uninstaller_exe} /S")
        t0 = time.time()
        result = subprocess.run(f'"{uninstaller_exe}" /S', shell=True, capture_output=True, text=True, timeout=120)
        duration = time.time() - t0
        print(f"[PASS] Uninstaller execution complete. Duration: {duration:.2f}s")

        # Wait for the uninstaller to finish and delete itself
        for _ in range(60):
            if not os.path.exists(uninstaller_exe):
                break
            time.sleep(0.5)

        # Step 8: Verify Complete Cleanup
        print("\n[STEP 8] Auditing post-uninstall system state...")
        time.sleep(3)  # Give a brief moment for locks/file deletes to finalize

        errors = []

        # 1. Verify Task is deleted
        task_check = subprocess.run(["schtasks", "/query", "/tn", "SPB_Daemon"], capture_output=True, text=True)
        if task_check.returncode == 0:
            errors.append("Scheduled Task 'SPB_Daemon' still exists.")
        else:
            print("[PASS] Scheduled Task 'SPB_Daemon' successfully removed.")

        # 2. Verify Daemon Process is terminated
        daemon_found = False
        for proc in psutil.process_iter(['name']):
            try:
                if proc.info['name'] == "SPB_Daemon.exe":
                    daemon_found = True
            except Exception:
                pass
        if daemon_found:
            errors.append("SPB_Daemon.exe process is still running after uninstall.")
        else:
            print("[PASS] SPB_Daemon.exe process successfully terminated.")

        # 3. Verify Install Directory is deleted
        if os.path.exists(inst_dir):
            remaining_files = os.listdir(inst_dir)
            if remaining_files:
                errors.append(f"Installation directory still exists and contains files: {remaining_files}")
            else:
                print("[PASS] Installation directory exists but is empty.")
        else:
            print("[PASS] Installation directory completely removed.")

        # 4. Verify Registry Key is deleted
        reg_found = False
        for access in [winreg.KEY_READ | winreg.KEY_WOW64_64KEY, winreg.KEY_READ | winreg.KEY_WOW64_32KEY, winreg.KEY_READ]:
            try:
                key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, reg_key_path, 0, access)
                winreg.CloseKey(key)
                reg_found = True
                break
            except WindowsError:
                pass
        if reg_found:
            errors.append("Add/Remove Programs registry key still exists in HKLM registry views.")
        else:
            print("[PASS] Add/Remove Programs registry key successfully removed.")

        if errors:
            raise RuntimeError("Post-uninstall audit failed:\n  " + "\n  ".join(errors))

        print("\n" + "=" * 50)
        print("[SUCCESS] SPB FULL LIFECYCLE VALIDATION GREEN!")
        print("=" * 50)

        with open(sentinel_path, "w", encoding="utf-8") as f:
            f.write("SUCCESS")

    except Exception as exc:
        print(f"\n[FAIL] SPB Lifecycle Integration Test failed: {exc}")
        with open(sentinel_path, "w", encoding="utf-8") as f:
            f.write(f"FAILED: {exc}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-elevated", action="store_true")
    parser.add_argument("--log", type=str)
    parser.add_argument("--sentinel", type=str)
    args = parser.parse_args()

    if args.run_elevated:
        if args.log:
            sys.stdout = Tee(args.log)
            sys.stderr = sys.stdout
        execute_test(args.log, args.sentinel)
        sys.exit(0)

    # Parent Process Context
    temp_dir = os.environ.get("TEMP", "C:\\Users\\You\\AppData\\Local\\Temp")
    log_path = os.path.join(temp_dir, "spb_lifecycle_test.log")
    sentinel_path = os.path.join(temp_dir, "spb_lifecycle_test.done")

    # Clean prior stubs
    for path in [log_path, sentinel_path]:
        if os.path.exists(path):
            try:
                os.remove(path)
            except:
                pass

    if is_admin():
        # Already elevated, run directly
        execute_test(log_path, sentinel_path)
        sys.exit(0)

    # Request UAC elevation and run asynchronously
    script_abs = os.path.abspath(sys.argv[0])
    cwd_abs = os.getcwd()
    params = f'"{script_abs}" --run-elevated --log "{log_path}" --sentinel "{sentinel_path}"'

    print("[*] Requesting Administrator UAC privilege elevation...")
    ret = ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, params, cwd_abs, 1)
    if ret <= 32:
        print(f"[!] UAC Elevation request rejected or failed (code {ret}).")
        sys.exit(1)

    print("[*] Elevated process started successfully. Polling real-time outputs:\n")

    # Read the log file in real-time
    last_position = 0
    while not os.path.exists(sentinel_path):
        if os.path.exists(log_path):
            try:
                with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
                    f.seek(last_position)
                    chunk = f.read()
                    if chunk:
                        sys.stdout.write(chunk)
                        sys.stdout.flush()
                        last_position = f.tell()
            except Exception:
                pass
        time.sleep(0.5)

    # Read any remaining log content
    if os.path.exists(log_path):
        try:
            with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
                f.seek(last_position)
                chunk = f.read()
                if chunk:
                    sys.stdout.write(chunk)
                    sys.stdout.flush()
        except Exception:
            pass

    # Read final result from sentinel
    try:
        with open(sentinel_path, "r", encoding="utf-8") as f:
            status = f.read().strip()
        if status == "SUCCESS":
            print("\n[INFO] Lifecycle Integration Test Status: SUCCESS")
            sys.exit(0)
        else:
            print(f"\n[ERROR] Lifecycle Integration Test Status: {status}")
            sys.exit(1)
    except Exception as e:
        print(f"\n[!] Failed to read sentinel file status: {e}")
        sys.exit(1)
    finally:
        # Cleanup
        for path in [log_path, sentinel_path]:
            if os.path.exists(path):
                try:
                    os.remove(path)
                except:
                    pass


if __name__ == "__main__":
    main()
