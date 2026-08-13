from __future__ import annotations

from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from passlib.context import CryptContext

from app.config.settings import Settings

_password_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    if len(password) < 12:
        raise ValueError("Admin password must be at least 12 characters.")
    return _password_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return _password_context.verify(password, password_hash)


def _serializer(settings: Settings) -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(
        settings.admin_session_secret.get_secret_value(), salt="admin-session"
    )


def create_session_cookie(settings: Settings, username: str) -> str:
    return _serializer(settings).dumps({"username": username})


def read_session_cookie(
    settings: Settings, value: str | None, max_age: int = 8 * 60 * 60
) -> str | None:
    if not value:
        return None
    try:
        payload = _serializer(settings).loads(value, max_age=max_age)
    except (BadSignature, SignatureExpired):
        return None
    username = payload.get("username")
    return username if isinstance(username, str) else None
