import base64
import getpass
import hashlib
import secrets


def main() -> None:
    password = getpass.getpass("Password to hash (input hidden): ")
    if len(password) < 12:
        raise SystemExit("Use at least 12 characters for a configured password.")
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 260_000)
    encode = lambda value: base64.urlsafe_b64encode(value).decode().rstrip("=")
    print(f"pbkdf2_sha256$260000${encode(salt)}${encode(digest)}")


if __name__ == "__main__":
    main()
