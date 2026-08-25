"""initial archive schema

Revision ID: 001
Revises:
Create Date: 2026-08-25

"""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

from alembic import context, op

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # pg_trgm powers the optional substring-search index on messages.content;
    # skip both when the server was built without contrib extensions
    has_trgm = context.is_offline_mode() or op.get_bind().scalar(
        sa.text("SELECT count(*) FROM pg_available_extensions WHERE name = 'pg_trgm'")
    )
    if has_trgm:
        op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    op.create_table(
        "bot_config",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=False),
        sa.Column("data", JSONB(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    op.create_table(
        "channels",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("type", sa.Text(), nullable=False),
        sa.Column("parent_id", sa.BigInteger()),
        sa.Column("archived", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    op.create_table(
        "users",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=False),
        sa.Column("username", sa.Text(), nullable=False),
        sa.Column("display_name", sa.Text()),
        sa.Column("is_bot", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("avatar_url", sa.Text()),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    op.create_table(
        "messages",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=False),
        sa.Column(
            "channel_id", sa.BigInteger(), sa.ForeignKey("channels.id"), nullable=False
        ),
        sa.Column(
            "author_id", sa.BigInteger(), sa.ForeignKey("users.id"), nullable=False
        ),
        sa.Column("author_name", sa.Text(), nullable=False),
        sa.Column("content", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("edited_at", sa.DateTime(timezone=True)),
        sa.Column("type", sa.Text(), nullable=False, server_default="default"),
        sa.Column("reply_to_id", sa.BigInteger()),
        sa.Column("pinned", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
        sa.Column("embeds", JSONB()),
        sa.Column("stickers", JSONB()),
        sa.Column(
            "synced_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_messages_channel_id_id", "messages", ["channel_id", "id"])
    if has_trgm:
        op.execute(
            "CREATE INDEX ix_messages_content_trgm ON messages USING gin (content gin_trgm_ops)"
        )

    op.create_table(
        "message_versions",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "message_id", sa.BigInteger(), sa.ForeignKey("messages.id"), nullable=False
        ),
        sa.Column("content", sa.Text()),
        sa.Column("embeds", JSONB()),
        sa.Column("edited_at", sa.DateTime(timezone=True)),
        sa.Column(
            "captured_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_message_versions_message_id", "message_versions", ["message_id"]
    )

    op.create_table(
        "attachments",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column(
            "message_id", sa.BigInteger(), sa.ForeignKey("messages.id"), nullable=False
        ),
        sa.Column("kind", sa.Text(), nullable=False),
        sa.Column("filename", sa.Text()),
        sa.Column("content_type", sa.Text()),
        sa.Column("size", sa.BigInteger()),
        sa.Column("width", sa.Integer()),
        sa.Column("height", sa.Integer()),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("content_hash", sa.Text()),
        sa.Column("storage_key", sa.Text()),
        sa.Column("encrypted", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column(
            "downloaded", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
        sa.Column(
            "download_attempts", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column("downloaded_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_attachments_message_id", "attachments", ["message_id"])

    op.create_table(
        "reactions",
        sa.Column(
            "message_id",
            sa.BigInteger(),
            sa.ForeignKey("messages.id"),
            primary_key=True,
        ),
        sa.Column("emoji", sa.Text(), primary_key=True),
        sa.Column("user_id", sa.BigInteger(), primary_key=True),
        sa.Column("count", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("removed_at", sa.DateTime(timezone=True)),
    )

    op.create_table(
        "sync_status",
        sa.Column(
            "channel_id",
            sa.BigInteger(),
            sa.ForeignKey("channels.id"),
            primary_key=True,
        ),
        sa.Column(
            "last_message_id", sa.BigInteger(), nullable=False, server_default="0"
        ),
        sa.Column("last_sync_at", sa.DateTime(timezone=True)),
        sa.Column("message_count", sa.BigInteger(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_table("sync_status")
    op.drop_table("reactions")
    op.drop_table("attachments")
    op.drop_table("message_versions")
    op.drop_table("messages")
    op.drop_table("users")
    op.drop_table("channels")
    op.drop_table("bot_config")
