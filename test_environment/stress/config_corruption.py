import argparse
import os
import sys


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--confirm", action="store_true", help="Corrupt config.json")
    args = parser.parse_args()

    cfg_dir = os.path.join(os.environ.get("PROGRAMDATA", "C:\\ProgramData"), "SimpleProductivityBlocker")
    cfg_path = os.path.join(cfg_dir, "config.json")

    if not args.confirm:
        print("[DRY] Would corrupt", cfg_path)
        sys.exit(0)

    try:
        with open(cfg_path, "w", encoding="utf-8") as handle:
            handle.write("{not-json")
        print("[OK] Corrupted config.json. Restart daemon to verify recovery.")
        sys.exit(0)
    except PermissionError:
        print("[OK] Access Denied. ACL hardening is preventing corruption (Security Success).")
        sys.exit(0)
    except Exception as exc:
        print("[FAIL] Could not corrupt config:", exc)
        sys.exit(1)


if __name__ == "__main__":
    main()
