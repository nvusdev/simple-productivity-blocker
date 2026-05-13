import argparse
import sys


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--confirm", action="store_true", help="Run update/repair/uninstall steps manually")
    args = parser.parse_args()

    if not args.confirm:
        print("[DRY] Use installer/uninstaller inside VM snapshots. Validate DNS and ACL recovery.")
        sys.exit(0)

    print("[INFO] Run installer, then uninstaller, and verify system recovery.")
    sys.exit(0)


if __name__ == "__main__":
    main()
