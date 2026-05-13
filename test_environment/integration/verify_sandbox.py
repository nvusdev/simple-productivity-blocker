import argparse
import os
import subprocess
import sys


def _is_hyperv_guest():
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", "(Get-CimInstance Win32_ComputerSystem).Model"],
            capture_output=True,
            text=True
        )
        model = (result.stdout or "").strip().lower()
        if "virtual machine" in model or "hyper-v" in model:
            return True
        # Fallback: check manufacturer for Microsoft Corporation
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", "(Get-CimInstance Win32_ComputerSystem).Manufacturer"],
            capture_output=True,
            text=True
        )
        manufacturer = (result.stdout or "").strip().lower()
        return "microsoft corporation" in manufacturer
    except Exception:
        return False


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true", help="Proceed even if sandbox is not detected")
    args = parser.parse_args()

    is_vm = _is_hyperv_guest()
    if not is_vm and not args.force:
        print("[FAIL] Hyper-V VM not detected. Run inside a Hyper-V guest or pass --force.")
        sys.exit(2)

    print("[OK] Sandbox check passed." if is_vm else "[WARN] Sandbox check forced.")
    sys.exit(0)


if __name__ == "__main__":
    main()
