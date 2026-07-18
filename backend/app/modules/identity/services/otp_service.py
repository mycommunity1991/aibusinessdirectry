"""
OTP generation, delivery, and verification.

Reused by every OTP use case in the product (mobile registration/login in
this story; arrival-verification and claim-listing in later stories) —
see `docs/AI/04_DATABASE.md` `identity.otp_verifications`.
"""

import secrets
from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import OTP_CODE_LENGTH, OTP_EXPIRY_MINUTES, OTP_MAX_ATTEMPTS
from app.core.exceptions import InvalidOtpError, OtpLockedError
from app.core.security import hash_otp_code, verify_otp_code
from app.modules.identity.models import OtpPurpose, OtpVerification
from app.modules.identity.repositories.otp_verification_repository import (
    OtpVerificationRepository,
)
from app.modules.identity.services.sms_sender import SmsSender


def _generate_code() -> str:
    """Generate a cryptographically-random, zero-padded 6-digit OTP code."""
    return f"{secrets.randbelow(10**OTP_CODE_LENGTH):0{OTP_CODE_LENGTH}d}"


class OtpService:
    """Business logic for requesting and verifying mobile OTP codes."""

    def __init__(
        self,
        repository: OtpVerificationRepository,
        sms_sender: SmsSender,
        session: AsyncSession,
    ) -> None:
        self.repository = repository
        self.sms_sender = sms_sender
        self.session = session

    async def request_otp(
        self,
        phone_country_code: str,
        phone_number: str,
        purpose: OtpPurpose,
    ) -> None:
        """
        Generate a 6-digit OTP code, persist only its Argon2id hash with a
        5-minute expiry, and dispatch it via the injected `SmsSender`
        (AC3/AC4). Never returns or logs the plaintext code.
        """
        code = _generate_code()
        code_hash = hash_otp_code(code)
        expires_at = datetime.now(UTC) + timedelta(minutes=OTP_EXPIRY_MINUTES)

        await self.repository.create(
            {
                "phone_country_code": phone_country_code,
                "phone_number": phone_number,
                "purpose": purpose,
                "code_hash": code_hash,
                "expires_at": expires_at,
            }
        )
        await self.sms_sender.send(phone_country_code, phone_number, code)

    async def verify_otp(
        self,
        phone_country_code: str,
        phone_number: str,
        purpose: OtpPurpose,
        code: str,
    ) -> OtpVerification:
        """
        Verify a submitted OTP code.

        Raises `InvalidOtpError` (generic, non-revealing) if the code is
        missing, expired, already used, or simply wrong (AC5, AC8, AC10).
        Raises `OtpLockedError` once the attempt cap is reached (AC5).
        On success, marks the row as verified and returns it.
        """
        otp = await self.repository.get_active_for_phone(
            phone_country_code, phone_number, purpose
        )
        if otp is None:
            raise InvalidOtpError()

        if otp.attempt_count >= OTP_MAX_ATTEMPTS:
            raise OtpLockedError()

        if not verify_otp_code(code, otp.code_hash):
            new_attempt_count = otp.attempt_count + 1
            await self.repository.update(otp, {"attempt_count": new_attempt_count})
            # Committed immediately (rather than deferred to the caller's
            # request-scoped commit) so the attempt counter durably
            # accumulates across requests even though this call raises —
            # required for the AC5 attempt-cap lockout to actually cap.
            await self.session.commit()
            if new_attempt_count >= OTP_MAX_ATTEMPTS:
                raise OtpLockedError()
            raise InvalidOtpError()

        await self.repository.update(otp, {"verified_at": datetime.now(UTC)})
        return otp
