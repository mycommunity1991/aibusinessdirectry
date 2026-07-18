from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.identity.models import OtpPurpose, OtpVerification
from app.repositories.base_repository import BaseRepository


class OtpVerificationRepository(BaseRepository[OtpVerification]):
    """Repository for the `identity.otp_verifications` table."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(model=OtpVerification, session=session)

    async def get_active_for_phone(
        self,
        phone_country_code: str,
        phone_number: str,
        purpose: OtpPurpose,
    ) -> OtpVerification | None:
        """
        Retrieve the latest active (unverified, unexpired) OTP row for a
        phone number and purpose.

        A row that is already verified, expired, or absent is not
        considered active — the caller (service layer) treats all of
        these identically (a generic, non-revealing failure), per AC5/AC8.
        """
        stmt = (
            select(OtpVerification)
            .where(
                OtpVerification.phone_country_code == phone_country_code,
                OtpVerification.phone_number == phone_number,
                OtpVerification.purpose == purpose,
                OtpVerification.verified_at.is_(None),
                OtpVerification.expires_at > func.now(),
            )
            .order_by(OtpVerification.created_at.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
