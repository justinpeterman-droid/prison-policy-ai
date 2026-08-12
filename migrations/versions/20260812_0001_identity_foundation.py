"""Create the Access identity and security foundation.

Revision ID: 20260812_0001
Revises:
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260812_0001"
down_revision = None
branch_labels = None
depends_on = None


UUID = postgresql.UUID(as_uuid=True)
UTC_TIMESTAMP = sa.DateTime(timezone=True)


def uuid_pk():
    return sa.Column("id", UUID, primary_key=True, server_default=sa.text("gen_random_uuid()"))


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")

    op.create_table(
        "staff_members",
        uuid_pk(),
        sa.Column("employee_number", sa.String(64), nullable=False),
        sa.Column("rank", sa.String(64), nullable=False),
        sa.Column("first_name", sa.String(100), nullable=False),
        sa.Column("last_name", sa.String(100), nullable=False),
        sa.Column("shift", sa.String(16), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", UTC_TIMESTAMP, nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", UTC_TIMESTAMP, nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.UniqueConstraint("employee_number", name="uq_staff_members_employee_number"),
    )
    op.create_index("ix_staff_members_employee_number", "staff_members", ["employee_number"])

    op.create_table(
        "accounts",
        uuid_pk(),
        sa.Column("staff_member_id", UUID, nullable=False),
        sa.Column("role", sa.String(16), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="active"),
        sa.Column("pin_hash", sa.Text(), nullable=False),
        sa.Column("must_change_pin", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("temporary_pin_expires_at", UTC_TIMESTAMP),
        sa.Column("failed_attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("lock_cycle", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("locked_until", UTC_TIMESTAMP),
        sa.Column("auth_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("last_login_at", UTC_TIMESTAMP),
        sa.Column("created_at", UTC_TIMESTAMP, nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", UTC_TIMESTAMP, nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("deactivated_at", UTC_TIMESTAMP),
        sa.ForeignKeyConstraint(["staff_member_id"], ["staff_members.id"], ondelete="RESTRICT", name="fk_accounts_staff_member_id_staff_members"),
        sa.UniqueConstraint("staff_member_id", name="uq_accounts_staff_member_id"),
        sa.CheckConstraint("role IN ('user','admin')", name="account_role"),
        sa.CheckConstraint("status IN ('active','locked','deactivated')", name="account_status"),
        sa.CheckConstraint("failed_attempts >= 0", name="account_failed_attempts_nonnegative"),
        sa.CheckConstraint("lock_cycle >= 0", name="account_lock_cycle_nonnegative"),
        sa.CheckConstraint("auth_version >= 1", name="account_auth_version_positive"),
    )
    op.create_index("ix_accounts_role_status", "accounts", ["role", "status"])

    op.create_table(
        "sessions",
        uuid_pk(),
        sa.Column("account_id", UUID, nullable=False),
        sa.Column("auth_version", sa.Integer(), nullable=False),
        sa.Column("access_token_hash", sa.LargeBinary(32), nullable=False),
        sa.Column("access_expires_at", UTC_TIMESTAMP, nullable=False),
        sa.Column("renewal_token_hash", sa.LargeBinary(32), nullable=False),
        sa.Column("renewal_expires_at", UTC_TIMESTAMP, nullable=False),
        sa.Column("renewal_family_id", UUID, nullable=False),
        sa.Column("device_id_hash", sa.LargeBinary(32), nullable=False),
        sa.Column("device_label", sa.String(120), nullable=False, server_default=""),
        sa.Column("persistent", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("last_used_at", UTC_TIMESTAMP, nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("created_at", UTC_TIMESTAMP, nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("revoked_at", UTC_TIMESTAMP),
        sa.Column("revoke_reason", sa.String(64)),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], ondelete="CASCADE", name="fk_sessions_account_id_accounts"),
        sa.UniqueConstraint("access_token_hash", name="uq_sessions_access_token_hash"),
        sa.UniqueConstraint("renewal_token_hash", name="uq_sessions_renewal_token_hash"),
        sa.CheckConstraint("octet_length(access_token_hash) = 32", name="session_access_hash_length"),
        sa.CheckConstraint("octet_length(renewal_token_hash) = 32", name="session_renewal_hash_length"),
        sa.CheckConstraint("octet_length(device_id_hash) = 32", name="session_device_hash_length"),
        sa.CheckConstraint("access_expires_at > created_at", name="session_access_expiry_after_create"),
        sa.CheckConstraint("renewal_expires_at > created_at", name="session_renewal_expiry_after_create"),
    )
    op.create_index("ix_sessions_account_id", "sessions", ["account_id"])
    op.create_index("ix_sessions_renewal_family", "sessions", ["renewal_family_id"])

    op.create_table(
        "renewal_token_history",
        uuid_pk(),
        sa.Column("session_id", UUID, nullable=False),
        sa.Column("renewal_family_id", UUID, nullable=False),
        sa.Column("token_hash", sa.LargeBinary(32), nullable=False),
        sa.Column("rotated_at", UTC_TIMESTAMP, nullable=False),
        sa.Column("expires_at", UTC_TIMESTAMP, nullable=False),
        sa.Column("reuse_detected_at", UTC_TIMESTAMP),
        sa.ForeignKeyConstraint(["session_id"], ["sessions.id"], ondelete="CASCADE", name="fk_renewal_token_history_session_id_sessions"),
        sa.UniqueConstraint("token_hash", name="uq_renewal_token_history_token_hash"),
        sa.CheckConstraint("octet_length(token_hash) = 32", name="renewal_history_hash_length"),
        sa.CheckConstraint("expires_at > rotated_at", name="renewal_history_expiry_after_rotation"),
    )
    op.create_index("ix_renewal_history_family", "renewal_token_history", ["renewal_family_id", "expires_at"])

    op.create_table(
        "admin_elevations",
        sa.Column("session_id", UUID, primary_key=True),
        sa.Column("issued_at", UTC_TIMESTAMP, nullable=False),
        sa.Column("last_used_at", UTC_TIMESTAMP, nullable=False),
        sa.Column("idle_expires_at", UTC_TIMESTAMP, nullable=False),
        sa.Column("revoked_at", UTC_TIMESTAMP),
        sa.ForeignKeyConstraint(["session_id"], ["sessions.id"], ondelete="CASCADE", name="fk_admin_elevations_session_id_sessions"),
        sa.CheckConstraint("idle_expires_at > issued_at", name="admin_elevation_expiry_after_issue"),
    )

    op.create_table(
        "admin_step_up_tokens",
        uuid_pk(),
        sa.Column("session_id", UUID, nullable=False),
        sa.Column("token_hash", sa.LargeBinary(32), nullable=False),
        sa.Column("purpose", sa.String(64), nullable=False),
        sa.Column("issued_at", UTC_TIMESTAMP, nullable=False),
        sa.Column("expires_at", UTC_TIMESTAMP, nullable=False),
        sa.Column("used_at", UTC_TIMESTAMP),
        sa.Column("revoked_at", UTC_TIMESTAMP),
        sa.ForeignKeyConstraint(["session_id"], ["sessions.id"], ondelete="CASCADE", name="fk_admin_step_up_tokens_session_id_sessions"),
        sa.UniqueConstraint("token_hash", name="uq_admin_step_up_token_hash"),
        sa.CheckConstraint("octet_length(token_hash) = 32", name="admin_step_up_hash_length"),
        sa.CheckConstraint("purpose IN ('staff_write','account_create','account_role_status','account_reset_pin','account_unlock','account_revoke_sessions','report_restore','report_transfer','bulk_export','audit_export','review_lab_handoff')", name="admin_step_up_purpose"),
        sa.CheckConstraint("expires_at > issued_at", name="admin_step_up_expiry_after_issue"),
    )
    op.create_index("ix_admin_step_up_tokens_session_id", "admin_step_up_tokens", ["session_id"])

    op.create_table(
        "browser_handoffs",
        uuid_pk(),
        sa.Column("account_id", UUID, nullable=False),
        sa.Column("session_id", UUID, nullable=False),
        sa.Column("token_hash", sa.LargeBinary(32), nullable=False),
        sa.Column("purpose", sa.String(32), nullable=False),
        sa.Column("expires_at", UTC_TIMESTAMP, nullable=False),
        sa.Column("redeemed_at", UTC_TIMESTAMP),
        sa.Column("revoked_at", UTC_TIMESTAMP),
        sa.Column("created_at", UTC_TIMESTAMP, nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], ondelete="CASCADE", name="fk_browser_handoffs_account_id_accounts"),
        sa.ForeignKeyConstraint(["session_id"], ["sessions.id"], ondelete="CASCADE", name="fk_browser_handoffs_session_id_sessions"),
        sa.UniqueConstraint("token_hash", name="uq_browser_handoffs_token_hash"),
        sa.CheckConstraint("purpose = 'review_lab'", name="browser_handoff_purpose"),
        sa.CheckConstraint("octet_length(token_hash) = 32", name="browser_handoff_hash_length"),
        sa.CheckConstraint("expires_at > created_at", name="browser_handoff_expiry_after_create"),
    )

    op.create_table(
        "browser_sessions",
        uuid_pk(),
        sa.Column("account_id", UUID, nullable=False),
        sa.Column("issuing_session_id", UUID, nullable=False),
        sa.Column("token_hash", sa.LargeBinary(32), nullable=False),
        sa.Column("purpose", sa.String(32), nullable=False),
        sa.Column("last_used_at", UTC_TIMESTAMP, nullable=False),
        sa.Column("expires_at", UTC_TIMESTAMP, nullable=False),
        sa.Column("created_at", UTC_TIMESTAMP, nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("revoked_at", UTC_TIMESTAMP),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"], ondelete="CASCADE", name="fk_browser_sessions_account_id_accounts"),
        sa.ForeignKeyConstraint(["issuing_session_id"], ["sessions.id"], ondelete="CASCADE", name="fk_browser_sessions_issuing_session_id_sessions"),
        sa.UniqueConstraint("token_hash", name="uq_browser_sessions_token_hash"),
        sa.CheckConstraint("purpose = 'review_lab'", name="browser_session_purpose"),
        sa.CheckConstraint("octet_length(token_hash) = 32", name="browser_session_hash_length"),
        sa.CheckConstraint("expires_at > created_at", name="browser_session_expiry_after_create"),
    )

    op.create_table(
        "auth_rate_limits",
        uuid_pk(),
        sa.Column("dimension", sa.String(32), nullable=False),
        sa.Column("subject_hash", sa.LargeBinary(32), nullable=False),
        sa.Column("window_started_at", UTC_TIMESTAMP, nullable=False),
        sa.Column("hit_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("blocked_until", UTC_TIMESTAMP),
        sa.Column("updated_at", UTC_TIMESTAMP, nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.UniqueConstraint("dimension", "subject_hash", name="uq_auth_rate_limit_dimension_subject"),
        sa.CheckConstraint("octet_length(subject_hash) = 32", name="auth_rate_limit_subject_hash_length"),
        sa.CheckConstraint("dimension IN ('employee','device','network')", name="auth_rate_limit_dimension"),
        sa.CheckConstraint("hit_count >= 0", name="auth_rate_limit_hit_count_nonnegative"),
    )
    op.create_index("ix_auth_rate_limits_window", "auth_rate_limits", ["dimension", "window_started_at"])

    op.create_table(
        "audit_events",
        uuid_pk(),
        sa.Column("actor_account_id", UUID),
        sa.Column("actor_staff_member_id", UUID),
        sa.Column("action", sa.String(120), nullable=False),
        sa.Column("target_type", sa.String(64), nullable=False),
        sa.Column("target_id", UUID),
        sa.Column("result", sa.String(16), nullable=False),
        sa.Column("request_id", sa.String(64), nullable=False),
        sa.Column("client_version", sa.String(64)),
        sa.Column("device_id_hash", sa.LargeBinary(32)),
        sa.Column("network_hash", sa.LargeBinary(32)),
        sa.Column("details", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("occurred_at", UTC_TIMESTAMP, nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.ForeignKeyConstraint(["actor_account_id"], ["accounts.id"], ondelete="SET NULL", name="fk_audit_events_actor_account_id_accounts"),
        sa.ForeignKeyConstraint(["actor_staff_member_id"], ["staff_members.id"], ondelete="SET NULL", name="fk_audit_events_actor_staff_member_id_staff_members"),
        sa.CheckConstraint("result IN ('success','denied','failed')", name="audit_event_result"),
        sa.CheckConstraint("device_id_hash IS NULL OR octet_length(device_id_hash) = 32", name="audit_event_device_hash_length"),
        sa.CheckConstraint("network_hash IS NULL OR octet_length(network_hash) = 32", name="audit_event_network_hash_length"),
        sa.CheckConstraint("octet_length(details::text) <= 4096", name="audit_event_details_size"),
    )
    op.create_index("ix_audit_events_occurred_action", "audit_events", ["occurred_at", "action"])

    op.execute("""
        CREATE FUNCTION public.reject_audit_mutation() RETURNS trigger
        LANGUAGE plpgsql SET search_path = pg_catalog, public AS $$
        BEGIN
            RAISE EXCEPTION 'audit_events are append-only';
        END;
        $$
    """)
    op.execute("""
        CREATE TRIGGER audit_events_append_only
        BEFORE UPDATE OR DELETE ON public.audit_events
        FOR EACH ROW EXECUTE FUNCTION public.reject_audit_mutation()
    """)
    op.execute("""
        CREATE FUNCTION public.append_audit_event(
            p_actor_account_id uuid, p_actor_staff_member_id uuid, p_action text,
            p_target_type text, p_target_id uuid, p_result text, p_request_id text,
            p_client_version text, p_device_id_hash bytea, p_network_hash bytea, p_details jsonb
        ) RETURNS uuid
        LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog, public AS $$
        DECLARE new_id uuid;
        BEGIN
            IF p_action IS NULL OR length(p_action) NOT BETWEEN 1 AND 120 OR p_action ~ '[[:cntrl:]]' THEN
                RAISE EXCEPTION 'audit action is invalid';
            END IF;
            IF p_result NOT IN ('success', 'denied', 'failed') THEN
                RAISE EXCEPTION 'audit result is invalid';
            END IF;
            IF p_details IS NULL OR jsonb_typeof(p_details) <> 'object' OR octet_length(p_details::text) > 4096 THEN
                RAISE EXCEPTION 'audit details are invalid';
            END IF;
            INSERT INTO public.audit_events (
                actor_account_id, actor_staff_member_id, action, target_type, target_id,
                result, request_id, client_version, device_id_hash, network_hash, details
            ) VALUES (
                p_actor_account_id, p_actor_staff_member_id, p_action, p_target_type, p_target_id,
                p_result, p_request_id, p_client_version, p_device_id_hash, p_network_hash, p_details
            ) RETURNING id INTO new_id;
            RETURN new_id;
        END;
        $$
    """)
    op.execute("REVOKE INSERT, UPDATE, DELETE ON public.audit_events FROM PUBLIC")
    op.execute("REVOKE ALL ON FUNCTION public.append_audit_event(uuid,uuid,text,text,uuid,text,text,text,bytea,bytea,jsonb) FROM PUBLIC")


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS audit_events_append_only ON public.audit_events")
    op.execute("DROP FUNCTION IF EXISTS public.append_audit_event(uuid,uuid,text,text,uuid,text,text,text,bytea,bytea,jsonb)")
    op.execute("DROP FUNCTION IF EXISTS public.reject_audit_mutation()")
    for table in (
        "audit_events",
        "auth_rate_limits",
        "browser_sessions",
        "browser_handoffs",
        "admin_step_up_tokens",
        "admin_elevations",
        "renewal_token_history",
        "sessions",
        "accounts",
        "staff_members",
    ):
        op.drop_table(table)
