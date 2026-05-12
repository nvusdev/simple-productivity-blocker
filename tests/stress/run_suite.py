import subprocess
import sys
import os

def run_test(script_path):
    print(f"\n>> Executing {os.path.basename(script_path)}...")
    result = subprocess.run([sys.executable, script_path], capture_output=True, text=True)
    print(result.stdout)
    if result.returncode != 0:
        print(f"ERROR: {os.path.basename(script_path)} failed with code {result.returncode}")
        print(result.stderr)
        return False
    return True

def main():
    print("==========================================")
    print("   SPB v1.4.3 GOLD MASTER STRESS SUITE   ")
    print("==========================================")
    
    tests = [
        "perf_bench.py",
        "proxy_load.py",
        "config_churn.py"
    ]
    
    base_dir = os.path.dirname(__file__)
    all_passed = True
    
    for test in tests:
        path = os.path.join(base_dir, test)
        if not run_test(path):
            all_passed = False
            break
            
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
