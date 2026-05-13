import argparse
import subprocess
import sys
import time


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--confirm", action="store_true", help="Actually spawn load")
    parser.add_argument("--count", type=int, default=50, help="Process count to spawn")
    args = parser.parse_args()

    if not args.confirm:
        print("[DRY] Would spawn", args.count, "processes.")
        sys.exit(0)

    procs = []
    for _ in range(args.count):
        procs.append(subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)"]))

    time.sleep(5)
    for p in procs:
        p.terminate()
    print("[OK] Spawned and cleaned up processes.")


if __name__ == "__main__":
    main()
