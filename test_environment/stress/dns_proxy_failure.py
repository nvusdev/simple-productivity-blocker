import argparse
import socket
import sys


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--confirm", action="store_true", help="Bind port 53 to simulate contention")
    args = parser.parse_args()

    if not args.confirm:
        print("[DRY] Would bind UDP port 53 to simulate contention.")
        sys.exit(0)

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.bind(("0.0.0.0", 53))
        print("[OK] Port 53 bound. Start daemon and verify fallback.")
        input("Press Enter to release port 53...")
    except OSError as exc:
        print("[WARN] Port 53 already in use. Skipping contention test:", exc)
        sys.exit(0)
    except Exception as exc:
        print("[FAIL] Could not bind port 53:", exc)
        sys.exit(1)
    finally:
        try:
            sock.close()
        except Exception:
            pass


if __name__ == "__main__":
    main()
