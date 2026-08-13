import secrets
import sys


def main() -> None:
    length = int(sys.argv[1]) if len(sys.argv) > 1 else 48
    if length < 32:
        raise SystemExit("Secret length must be at least 32 characters.")
    print(secrets.token_urlsafe(length))


if __name__ == "__main__":
    main()
