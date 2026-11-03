import secrets

from cryptography.fernet import Fernet, InvalidToken

from app.config import get_settings


def encrypt_token(value: str) -> str:
    key = get_settings().encryption_key
    if not key:
        raise RuntimeError("ENCRYPTION_KEY must be configured before connecting Google accounts.")
    try:
        return Fernet(key.encode()).encrypt(value.encode()).decode()
    except (ValueError, TypeError) as exc:
        raise RuntimeError("ENCRYPTION_KEY must be a valid Fernet key.") from exc


def decrypt_token(value: str) -> str:
    try:
        return Fernet(get_settings().encryption_key.encode()).decrypt(value.encode()).decode()
    except (InvalidToken, ValueError, TypeError) as exc:
        raise RuntimeError("Stored Google credentials cannot be decrypted; verify ENCRYPTION_KEY.") from exc


def new_csrf_token() -> str:
    return secrets.token_urlsafe(32)
