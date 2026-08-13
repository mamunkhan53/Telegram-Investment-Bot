from getpass import getpass

from app.admin.auth.security import hash_password


def main() -> None:
    first = getpass("Admin password: ")
    second = getpass("Repeat admin password: ")
    if first != second:
        raise SystemExit("Passwords do not match.")
    print(hash_password(first))


if __name__ == "__main__":
    main()
