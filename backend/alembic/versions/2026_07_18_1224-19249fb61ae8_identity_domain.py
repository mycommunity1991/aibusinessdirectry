"""identity_domain

Revision ID: 19249fb61ae8
Revises: 101b27d7096b
Create Date: 2026-07-18 12:24:33.372135

Creates the `identity` Postgres schema and its 7 AUTH-001 tables: users,
roles, permissions, role_permissions, user_roles, devices,
otp_verifications. See `docs/AI/04_DATABASE.md` (Identity Domain) and
`docs/implementation/plans/Plan_S02_AUTH-001.md`.

Deliberately does NOT create `sessions`/`refresh_tokens` (AUTH-003) and does
not populate `permissions`/`role_permissions` (AUTH-004, seed data is a
separate script — see `app/database/seed_data.py`).
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "19249fb61ae8"
down_revision: str | Sequence[str] | None = "101b27d7096b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "identity"

user_status_enum = postgresql.ENUM(
    "active", "suspended", "deleted", name="user_status", schema=SCHEMA
)
auth_provider_enum = postgresql.ENUM(
    "google",
    "apple",
    "mobile_otp",
    "email_password",
    name="auth_provider",
    schema=SCHEMA,
)
device_platform_enum = postgresql.ENUM(
    "ios", "android", name="device_platform", schema=SCHEMA
)
language_code_enum = postgresql.ENUM("en", "ar", name="language_code", schema=SCHEMA)
otp_purpose_enum = postgresql.ENUM(
    "registration",
    "login",
    "arrival_verification",
    "claim_listing",
    name="otp_purpose",
    schema=SCHEMA,
)

ALL_ENUMS = (
    user_status_enum,
    auth_provider_enum,
    device_platform_enum,
    language_code_enum,
    otp_purpose_enum,
)


def _common_columns() -> list[sa.Column]:
    """Common Columns per `04_DATABASE.md` — id, audit, soft-delete,
    optimistic-locking columns shared by every business table."""
    return [
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")
        ),
        sa.Column(
            "version", sa.Integer(), nullable=False, server_default=sa.text("1")
        ),
    ]


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()

    op.execute(f"CREATE SCHEMA IF NOT EXISTS {SCHEMA}")

    for enum_type in ALL_ENUMS:
        enum_type.create(bind, checkfirst=True)

    # --- users -----------------------------------------------------------
    op.create_table(
        "users",
        *_common_columns(),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("email_verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("phone_country_code", sa.String(length=5), nullable=True),
        sa.Column("phone_number", sa.String(length=20), nullable=True),
        sa.Column("phone_verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("password_hash", sa.String(length=255), nullable=True),
        sa.Column(
            "auth_provider",
            postgresql.ENUM(
                "google",
                "apple",
                "mobile_otp",
                "email_password",
                name="auth_provider",
                schema=SCHEMA,
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("external_auth_subject", sa.String(length=255), nullable=True),
        sa.Column(
            "status",
            postgresql.ENUM(
                "active",
                "suspended",
                "deleted",
                name="user_status",
                schema=SCHEMA,
                create_type=False,
            ),
            nullable=False,
            server_default="active",
        ),
        sa.Column(
            "preferred_language",
            postgresql.ENUM(
                "en", "ar", name="language_code", schema=SCHEMA, create_type=False
            ),
            nullable=False,
            server_default="en",
        ),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "email IS NOT NULL OR phone_number IS NOT NULL "
            "OR external_auth_subject IS NOT NULL",
            name="chk_users_has_identifier",
        ),
        sa.ForeignKeyConstraint(
            ["created_by"], [f"{SCHEMA}.users.id"], name="fk_users_created_by"
        ),
        sa.ForeignKeyConstraint(
            ["updated_by"], [f"{SCHEMA}.users.id"], name="fk_users_updated_by"
        ),
        schema=SCHEMA,
    )
    op.create_index(
        "uq_users_email",
        "users",
        ["email"],
        unique=True,
        schema=SCHEMA,
        postgresql_where=sa.text("email IS NOT NULL"),
    )
    op.create_index(
        "uq_users_phone",
        "users",
        ["phone_country_code", "phone_number"],
        unique=True,
        schema=SCHEMA,
        postgresql_where=sa.text("phone_number IS NOT NULL"),
    )
    op.create_index(
        "uq_users_external_auth",
        "users",
        ["auth_provider", "external_auth_subject"],
        unique=True,
        schema=SCHEMA,
        postgresql_where=sa.text("external_auth_subject IS NOT NULL"),
    )
    op.create_index("idx_users_email", "users", ["email"], schema=SCHEMA)
    op.create_index(
        "idx_users_phone_number", "users", ["phone_number"], schema=SCHEMA
    )
    op.create_index("idx_users_status", "users", ["status"], schema=SCHEMA)

    # --- roles -------------------------------------------------------------
    op.create_table(
        "roles",
        *_common_columns(),
        sa.Column("name", sa.String(length=50), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.UniqueConstraint("name", name="uq_roles_name"),
        sa.ForeignKeyConstraint(
            ["created_by"], [f"{SCHEMA}.users.id"], name="fk_roles_created_by"
        ),
        sa.ForeignKeyConstraint(
            ["updated_by"], [f"{SCHEMA}.users.id"], name="fk_roles_updated_by"
        ),
        schema=SCHEMA,
    )

    # --- permissions ---------------------------------------------------
    op.create_table(
        "permissions",
        *_common_columns(),
        sa.Column("code", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.UniqueConstraint("code", name="uq_permissions_code"),
        sa.ForeignKeyConstraint(
            ["created_by"], [f"{SCHEMA}.users.id"], name="fk_permissions_created_by"
        ),
        sa.ForeignKeyConstraint(
            ["updated_by"], [f"{SCHEMA}.users.id"], name="fk_permissions_updated_by"
        ),
        schema=SCHEMA,
    )

    # --- role_permissions (join table) --------------------------------
    op.create_table(
        "role_permissions",
        sa.Column("role_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("permission_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint(
            "role_id", "permission_id", name="pk_role_permissions"
        ),
        sa.ForeignKeyConstraint(
            ["role_id"],
            [f"{SCHEMA}.roles.id"],
            name="fk_role_permissions_role_id",
        ),
        sa.ForeignKeyConstraint(
            ["permission_id"],
            [f"{SCHEMA}.permissions.id"],
            name="fk_role_permissions_permission_id",
        ),
        schema=SCHEMA,
    )

    # --- user_roles (join table) ----------------------------------------
    op.create_table(
        "user_roles",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("user_id", "role_id", name="pk_user_roles"),
        sa.ForeignKeyConstraint(
            ["user_id"], [f"{SCHEMA}.users.id"], name="fk_user_roles_user_id"
        ),
        sa.ForeignKeyConstraint(
            ["role_id"], [f"{SCHEMA}.roles.id"], name="fk_user_roles_role_id"
        ),
        schema=SCHEMA,
    )

    # --- devices -----------------------------------------------------------
    op.create_table(
        "devices",
        *_common_columns(),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "platform",
            postgresql.ENUM(
                "ios",
                "android",
                name="device_platform",
                schema=SCHEMA,
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("device_name", sa.String(length=255), nullable=True),
        sa.Column("push_token", sa.String(length=255), nullable=True),
        sa.Column(
            "is_trusted", sa.Boolean(), nullable=False, server_default=sa.text("false")
        ),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["user_id"], [f"{SCHEMA}.users.id"], name="fk_devices_user_id"
        ),
        sa.ForeignKeyConstraint(
            ["created_by"], [f"{SCHEMA}.users.id"], name="fk_devices_created_by"
        ),
        sa.ForeignKeyConstraint(
            ["updated_by"], [f"{SCHEMA}.users.id"], name="fk_devices_updated_by"
        ),
        schema=SCHEMA,
    )
    op.create_index("idx_devices_user_id", "devices", ["user_id"], schema=SCHEMA)

    # --- otp_verifications ---------------------------------------------
    op.create_table(
        "otp_verifications",
        *_common_columns(),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("phone_country_code", sa.String(length=5), nullable=False),
        sa.Column("phone_number", sa.String(length=20), nullable=False),
        sa.Column(
            "purpose",
            postgresql.ENUM(
                "registration",
                "login",
                "arrival_verification",
                "claim_listing",
                name="otp_purpose",
                schema=SCHEMA,
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("code_hash", sa.String(length=255), nullable=False),
        sa.Column(
            "attempt_count",
            sa.SmallInteger(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["user_id"],
            [f"{SCHEMA}.users.id"],
            name="fk_otp_verifications_user_id",
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            [f"{SCHEMA}.users.id"],
            name="fk_otp_verifications_created_by",
        ),
        sa.ForeignKeyConstraint(
            ["updated_by"],
            [f"{SCHEMA}.users.id"],
            name="fk_otp_verifications_updated_by",
        ),
        schema=SCHEMA,
    )
    op.create_index(
        "idx_otp_verifications_phone",
        "otp_verifications",
        ["phone_country_code", "phone_number"],
        schema=SCHEMA,
    )
    op.create_index(
        "idx_otp_verifications_user_id",
        "otp_verifications",
        ["user_id"],
        schema=SCHEMA,
    )


def downgrade() -> None:
    """Downgrade schema."""
    bind = op.get_bind()

    op.drop_table("otp_verifications", schema=SCHEMA)
    op.drop_table("devices", schema=SCHEMA)
    op.drop_table("user_roles", schema=SCHEMA)
    op.drop_table("role_permissions", schema=SCHEMA)
    op.drop_table("permissions", schema=SCHEMA)
    op.drop_table("roles", schema=SCHEMA)
    op.drop_table("users", schema=SCHEMA)

    for enum_type in ALL_ENUMS:
        enum_type.drop(bind, checkfirst=True)

    op.execute(f"DROP SCHEMA IF EXISTS {SCHEMA} RESTRICT")
