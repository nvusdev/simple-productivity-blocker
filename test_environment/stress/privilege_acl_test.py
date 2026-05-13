import argparse
import os
import sys
import ctypes


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--path", default=os.path.join(os.environ.get("PROGRAMDATA", "C:\\ProgramData"), "SimpleProductivityBlocker"))
    args = parser.parse_args()

    try:
        if ctypes.windll.shell32.IsUserAnAdmin():
            print("[WARN] Running as admin; ACL write probe is not meaningful. Run as standard user.")
            sys.exit(0)
    except Exception:
        pass

    test_file = os.path.join(args.path, "acl_probe.tmp")
    try:
        with open(test_file, "w", encoding="utf-8") as handle:
            handle.write("probe")
        os.remove(test_file)
        print("[FAIL] Write succeeded. ACL hardening not enforced for this user.")
        sys.exit(1)
    except Exception:
        print("[OK] Write blocked. ACL hardening enforced.")
        sys.exit(0)


if __name__ == "__main__":
    main()
