import hashlib
import secrets
from datetime import UTC, datetime, timedelta

from jose import JWTError, jwt
from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher

from app.core.config import settings
from app.core.exceptions import ExpiredTokenError, InvalidTokenError

# Use Argon2id as the default hashing algorithm
password_hash = PasswordHash((Argon2Hasher(),))


def hash_password(password: str) -> str:
    """
    Hashes a password using Argon2id.

    Args:
        password: The plain text password to hash.

    Returns:
        The hashed password string.
    """
    return password_hash.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    """
    Verifies a plain text password against a hashed password.

    Args:
        password: The plain text password to verify.
        hashed_password: The previously hashed password.

    Returns:
        True if the password matches the hash, False otherwise.
    """
    return password_hash.verify(password, hashed_password)


def hash_otp_code(code: str) -> str:
    """
    Hashes a one-time-password code using the same Argon2id primitive as
    `hash_password` (BF-011). A dedicated wrapper is used (rather than
    calling `hash_password` directly) so call sites clearly express intent
    and never persist a plaintext OTP code (`06_SECURITY.md`).

    Args:
        code: The plain text OTP code (e.g. a 6-digit string).

    Returns:
        The hashed OTP code string.
    """
    return password_hash.hash(code)


def verify_otp_code(code: str, code_hash: str) -> bool:
    """
    Verifies a plain text OTP code against its stored hash.

    Args:
        code: The plain text OTP code supplied by the user.
        code_hash: The previously hashed OTP code.

    Returns:
        True if the code matches the hash, False otherwise.
    """
    return password_hash.verify(code, code_hash)


def create_access_token(
    subject: str,
    roles: list[str],
    jti: str,
    expires_delta: timedelta | None = None,
) -> str:
    """
    Creates a JWT access token.

    Payload is exactly `{sub, exp, iat, jti, roles}` -- no email, phone,
    or any other PII (AUTH-003, AC2). `jti` doubles as the session
    identifier (Decision 1, `Plan_S02_AUTH-003.md`): every access token
    minted within the same session's lifetime (across refreshes) shares
    the same `jti`.

    Args:
        subject: The subject of the token (e.g., user ID).
        roles: The user's current role names.
        jti: The session id this token belongs to.
        expires_delta: Optional custom expiration timedelta.
            Defaults to the application settings.

    Returns:
        The encoded JWT token.
    """
    now = datetime.now(UTC)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode = {
        "sub": str(subject),
        "exp": expire,
        "iat": now,
        "jti": str(jti),
        "roles": roles,
    }
    encoded_jwt = jwt.encode(
        to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM
    )
    return encoded_jwt


def generate_refresh_token() -> str:
    """
    Generates a new opaque refresh token: a 256-bit
    (`secrets.token_urlsafe(32)`) cryptographically random value (AUTH-003,
    Decision 5, AC3). The raw value returned here is handed to the client
    exactly once and is never itself persisted -- only `hash_refresh_token`
    of it is.
    """
    return secrets.token_urlsafe(32)


def hash_refresh_token(token: str) -> str:
    """
    Hashes an opaque refresh token with SHA-256 (`04_DATABASE.md`'s
    `refresh_tokens.token_hash` column note) -- deliberately NOT Argon2id.
    Argon2id's slow-KDF property defends against brute-forcing a
    low-entropy, human-chosen secret (a password, a 6-digit OTP); a
    256-bit `secrets.token_urlsafe` value has no meaningful brute-force
    surface, so a fast, collision-resistant hash is the correct choice.

    Args:
        token: The raw opaque refresh token.

    Returns:
        The hex-encoded SHA-256 digest.
    """
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def decode_token(token: str) -> dict:
    """
    Decodes and validates a JWT token.

    Args:
        token: The encoded JWT token.

    Returns:
        The decoded payload dictionary.

    Raises:
        ExpiredTokenError: If the token has expired.
        InvalidTokenError: If the token is invalid or malformed.
    """
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        return payload
    except jwt.ExpiredSignatureError as e:
        raise ExpiredTokenError() from e
    except JWTError as e:
        raise InvalidTokenError() from e


def get_token_expiry() -> datetime:
    """
    Gets the default expiration time for a new token.

    Returns:
        A datetime object representing the expiration time.
    """
    return datetime.now(UTC) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
