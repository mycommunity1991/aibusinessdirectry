"""
Integration tests for `SystemSettingService`/`SystemSettingRepository`
(ADM-002, Decision 1/3/8, `Plan_S11_ADM-002.md`), exercised against a
real Postgres database -- mirrors `test_feature_flag_service.py`'s
identical pattern.
"""

import uuid

from sqlalchemy import select

from app.core.exceptions import SystemSettingNotFoundError
from app.modules.administration.models import AdminActionLog
from app.modules.administration.repositories.admin_action_log_repository import (
    AdminActionLogRepository,
)
from app.modules.administration.repositories.system_setting_repository import (
    SystemSettingRepository,
)
from app.modules.administration.services.admin_action_log_service import (
    AdminActionLogService,
)
from app.modules.administration.services.system_setting_service import (
    SystemSettingService,
)
from app.modules.identity.models import AuthProvider, User

_SETTING_KEY = "support_contact_email"


async def _make_user(db_session, phone_number: str) -> User:
    user = User(
        phone_country_code="+971",
        phone_number=phone_number,
        auth_provider=AuthProvider.MOBILE_OTP,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


def _service(db_session) -> SystemSettingService:
    return SystemSettingService(
        SystemSettingRepository(db_session),
        AdminActionLogService(AdminActionLogRepository(db_session)),
    )


async def _seed_setting(
    db_session, *, key: str = _SETTING_KEY, value: dict | None = None
) -> None:
    """Mirrors Decision 1's literal migration-seed row -- built directly
    through the repository, since this test's schema is created from
    models, not the real migration."""
    await SystemSettingRepository(db_session).create(
        {
            "key": key,
            "value": value or {"email": "support@aimarketplace.example"},
            "description": None,
        }
    )
    await db_session.commit()


class TestListAll:
    async def test_lists_every_row_ordered_by_key(self, db_session) -> None:
        await _seed_setting(db_session, key="b_setting", value={"x": 1})
        await _seed_setting(db_session, key="a_setting", value={"y": 2})
        service = _service(db_session)

        settings = await service.list_all()

        assert [setting.key for setting in settings] == ["a_setting", "b_setting"]


class TestUpdateValue:
    async def test_update_value_persists_the_new_jsonb_value(self, db_session) -> None:
        admin = await _make_user(db_session, "970000001")
        await _seed_setting(db_session)
        service = _service(db_session)

        new_value = {"email": "new-support@aimarketplace.example"}
        updated = await service.update_value(
            _SETTING_KEY, value=new_value, admin_user_id=admin.id
        )
        await db_session.commit()

        assert updated.value == new_value

        settings = await service.list_all()
        assert settings[0].value == new_value

    async def test_update_value_writes_exactly_one_admin_action_log_row(
        self, db_session
    ) -> None:
        admin = await _make_user(db_session, "970000002")
        await _seed_setting(db_session)
        service = _service(db_session)

        new_value = {"email": "new-support@aimarketplace.example"}
        updated = await service.update_value(
            _SETTING_KEY, value=new_value, admin_user_id=admin.id
        )
        await db_session.commit()

        result = await db_session.execute(select(AdminActionLog))
        logs = result.scalars().all()
        assert len(logs) == 1
        assert logs[0].admin_user_id == admin.id
        assert logs[0].action_type == "system_setting_updated"
        assert logs[0].target_entity_type == "system_setting"
        assert logs[0].target_entity_id == updated.id
        assert logs[0].metadata_ == {"key": _SETTING_KEY, "value": new_value}

    async def test_update_value_on_an_unknown_key_raises_not_found(
        self, db_session
    ) -> None:
        service = _service(db_session)

        try:
            await service.update_value(
                "unknown_key", value={"x": 1}, admin_user_id=uuid.uuid4()
            )
            raise AssertionError("expected SystemSettingNotFoundError")
        except SystemSettingNotFoundError:
            pass
