import subprocess
import sys
import os

def run_test(script_path, extra_args=None):
    extra_args = extra_args or []
    print(f"\n>> Executing {os.path.basename(script_path)}...", flush=True)
    result = subprocess.run([sys.executable, script_path] + extra_args)
    if result.returncode != 0:
        print(f"ERROR: {os.path.basename(script_path)} failed with code {result.returncode}")
        return False
    return True

def main():
    print("==========================================")
    print("   SPB v1.4.3 GOLD MASTER STRESS SUITE   ")
    print("==========================================")
    
    tests = [
        # Integration & Logic Checks
        ("../integration/verify_sandbox.py", ["--force"]),
        "../integration/verify_nuclear.py",
        "../integration/verify_scheduler.py",
        "../integration/verify_targets.py",
        "../integration/verify_allowlist.py",
        
        # Performance & Load
        "../performance/perf_bench.py",
        "../performance/proxy_load.py",
        
        # Stress & Resilience
        "config_churn.py",
        "resource_exhaustion.py",
        "network_failures.py",
        "power_loss_sim.py",
        "privilege_acl_test.py",
        "schedule_edge_cases.py",
        ("config_corruption.py", ["--confirm"]),
        ("dns_proxy_failure.py", ["--confirm"]),
        "wmi_com_recovery.py",
        "safe_mode_audit.py",
        "update_repair_uninstall.py",
        "window_storms.py"
    ]
    
    base_dir = os.path.dirname(__file__)
    all_passed = True
    try:
        for test in tests:
            if isinstance(test, tuple):
                name, args = test
            else:
                name, args = test, []
            path = os.path.join(base_dir, name)
            if not run_test(path, args):
                all_passed = False
                break
    finally:
        print("\n" + "="*42)
        print("   INITIATING AUTOMATED RECOVERY UPLIFT   ")
        print("="*42)
        recovery_path = os.path.abspath(os.path.join(base_dir, "../../recovery_uplift.py"))
        # Run elevated if on Windows, but since we are in a script, we'll try direct run first
        subprocess.run([sys.executable, recovery_path, "--dry-run"], capture_output=False) # Visual confirmation
        subprocess.run([sys.executable, recovery_path], input="\n", text=True) # Send Enter to exit
            
    if all_passed:
        print("\n" + "="*42)
        print("   ALL STRESS TESTS PASSED: STATUS GREEN   ")
        print("="*42)
        sys.exit(0)
    else:
        print("\n" + "="*42)
        print("   STRESS TEST FAILED: STATUS RED   ")
        print("="*42)
        sys.exit(1)

if __name__ == "__main__":
    main()
