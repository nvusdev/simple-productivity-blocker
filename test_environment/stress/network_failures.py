import argparse
import sys


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--confirm", action="store_true", help="Run live network changes")
    args = parser.parse_args()

    if not args.confirm:
        print("[DRY] Disable network adapters manually in Hyper-V, then re-enable.")
        sys.exit(0)

    print("[WARN] Live network changes are not automated. Use Hyper-V manager.")
    sys.exit(0)


if __name__ == "__main__":
    main()
