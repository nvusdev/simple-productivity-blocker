import argparse
import subprocess
import sys
import time


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--confirm", action="store_true", help="Launch explorer windows")
    parser.add_argument("--count", type=int, default=20)
    args = parser.parse_args()

    if not args.confirm:
        print("[DRY] Would spawn", args.count, "explorer windows.")
        sys.exit(0)

    for _ in range(args.count):
        subprocess.Popen(["explorer.exe"]) 
        time.sleep(0.1)

    print("[OK] Spawned explorer windows. Close them and monitor watchdog.")


if __name__ == "__main__":
    main()
