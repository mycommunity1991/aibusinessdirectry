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
    expires_delta: timedelta | None = None,
) -> str:
    """
    Creates a JWT access token.

    Args:
        subject: The subject of the token (e.g., user ID).
        expires_delta: Optional custom expiration timedelta.
            Defaults to the application settings.

    Returns:
        The encoded JWT token.
    """
    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )

    to_encode = {"exp": expire, "sub": str(subject)}
    encoded_jwt = jwt.encode(
        to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM
    )
    return encoded_jwt


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
