import base64
import hashlib
import hmac
import json
import time
from dataclasses import dataclass

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import (
    ADMIN_PASSWORD_HASH,
    ADMIN_USERNAME,
    REVIEWER_PASSWORD_HASH,
    REVIEWER_USERNAME,
    TOKEN_SECRET,
    TOKEN_TTL_SECONDS,
)

bearer = HTTPBearer(auto_error=False)
@dataclass(frozen=True)
class Principal:
    username: str
    role: str


def _b64encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _b64decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def authenticate(username: str, password: str) -> Principal | None:
    users = (
        (ADMIN_USERNAME, ADMIN_PASSWORD_HASH, "admin"),
        (REVIEWER_USERNAME, REVIEWER_PASSWORD_HASH, "reviewer"),
    )
    matched: Principal | None = None
    for configured_username, encoded_hash, role in users:
        username_matches = hmac.compare_digest(username, configured_username)
        password_matches = _verify_password(password, encoded_hash)
        if username_matches and password_matches:
            matched = Principal(username=configured_username, role=role)
    return matched


def _verify_password(password: str, encoded_hash: str) -> bool:
    try:
        algorithm, iterations_text, salt_text, digest_text = encoded_hash.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        iterations = int(iterations_text)
        if iterations < 100_000 or iterations > 2_000_000:
            return False
        salt = _b64decode(salt_text)
        expected = _b64decode(digest_text)
        actual = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, iterations)
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False


def issue_token(principal: Principal) -> str:
    payload = json.dumps(
        {
            "sub": principal.username,
            "role": principal.role,
            "exp": int(time.time()) + TOKEN_TTL_SECONDS,
        },
        separators=(",", ":"),
    ).encode()
    encoded = _b64encode(payload)
    signature = hmac.new(TOKEN_SECRET.encode(), encoded.encode(), hashlib.sha256).digest()
    return f"{encoded}.{_b64encode(signature)}"


def _decode_token(token: str) -> Principal | None:
    try:
        encoded, signature = token.split(".", 1)
        expected = hmac.new(TOKEN_SECRET.encode(), encoded.encode(), hashlib.sha256).digest()
        if not hmac.compare_digest(_b64decode(signature), expected):
            return None
        payload = json.loads(_b64decode(encoded))
        if int(payload["exp"]) < int(time.time()):
            return None
        role = payload["role"]
        if role not in {"admin", "reviewer"}:
            return None
        return Principal(username=str(payload["sub"]), role=role)
    except (ValueError, KeyError, TypeError, json.JSONDecodeError):
        return None


async def current_principal(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
) -> Principal:
    principal = _decode_token(credentials.credentials) if credentials else None
    if principal is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return principal


def require_roles(*roles: str):
    async def dependency(principal: Principal = Depends(current_principal)) -> Principal:
        if principal.role not in roles:
            raise HTTPException(status_code=403, detail="Insufficient role")
        return principal

    return dependency
