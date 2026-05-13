import argparse
import sys


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--confirm", action="store_true", help="Proceed with manual power loss test")
    args = parser.parse_args()

    if not args.confirm:
        print("[DRY] Manually terminate daemon and reboot the VM.")
        sys.exit(0)

    print("[INFO] Use Hyper-V manager to power off the VM, then boot and validate recovery.")
    sys.exit(0)


if __name__ == "__main__":
    main()
