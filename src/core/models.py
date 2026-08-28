"""
SQLAlchemy models for the message archive.

Single bot, single guild: Discord snowflakes are globally unique, so they
serve as primary keys directly. All timestamps are stored as UTC (timestamptz).
"""

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# reactions.user_id when the individual reactor is unknown (bulk scan fallback)
UNKNOWN_USER_ID = 0


class Base(DeclarativeBase):
    pass


class BotConfig(Base):
    """Single-row table holding the bot configuration (replaces config.yml)."""

    __tablename__ = "bot_config"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    data: Mapped[dict] = mapped_column(JSONB, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class Channel(Base):
    __tablename__ = "channels"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    type: Mapped[str] = mapped_column(Text, nullable=False)
    parent_id: Mapped[int | None] = mapped_column(BigInteger)
    # Discord sidebar sort position; None for threads and pre-migration rows
    position: Mapped[int | None] = mapped_column(Integer)
    archived: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False)
    username: Mapped[str] = mapped_column(Text, nullable=False)
    display_name: Mapped[str | None] = mapped_column(Text)
    is_bot: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    avatar_url: Mapped[str | None] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False)
    channel_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("channels.id"), nullable=False
    )
    author_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id"), nullable=False
    )
    # display_name at capture time; users.display_name only keeps the latest
    author_name: Mapped[str] = mapped_column(Text, nullable=False)
    content: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    edited_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    type: Mapped[str] = mapped_column(Text, nullable=False, default="default")
    reply_to_id: Mapped[int | None] = mapped_column(BigInteger)
    pinned: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # set when the message is deleted on Discord; the row is kept
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    embeds: Mapped[list | None] = mapped_column(JSONB)
    stickers: Mapped[list | None] = mapped_column(JSONB)
    synced_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (Index("ix_messages_channel_id_id", "channel_id", "id"),)


class MessageVersion(Base):
    """Pre-edit snapshot of a message, copied from the DB row before updating."""

    __tablename__ = "message_versions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    message_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("messages.id"), nullable=False
    )
    content: Mapped[str | None] = mapped_column(Text)
    embeds: Mapped[list | None] = mapped_column(JSONB)
    edited_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    captured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (Index("ix_message_versions_message_id", "message_id"),)


class Attachment(Base):
    __tablename__ = "attachments"

    # Discord attachments: snowflake as str; embed images: sha1 of the URL
    id: Mapped[str] = mapped_column(Text, primary_key=True)
    message_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("messages.id"), nullable=False
    )
    kind: Mapped[str] = mapped_column(Text, nullable=False)
    filename: Mapped[str | None] = mapped_column(Text)
    content_type: Mapped[str | None] = mapped_column(Text)
    size: Mapped[int | None] = mapped_column(BigInteger)
    width: Mapped[int | None] = mapped_column(Integer)
    height: Mapped[int | None] = mapped_column(Integer)
    # original CDN URL; Discord signs these with an expiry, kept for reference only
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    content_hash: Mapped[str | None] = mapped_column(Text)
    # path relative to media_root: {sha256[:2]}/{sha256}{ext}[.enc]
    storage_key: Mapped[str | None] = mapped_column(Text)
    # file is AES-GCM encrypted (see src/core/mediacrypto.py)
    encrypted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    downloaded: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    download_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    downloaded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (Index("ix_attachments_message_id", "message_id"),)


class Reaction(Base):
    __tablename__ = "reactions"

    message_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("messages.id"), primary_key=True
    )
    emoji: Mapped[str] = mapped_column(Text, primary_key=True)
    # UNKNOWN_USER_ID when individual reactors could not be resolved
    user_id: Mapped[int] = mapped_column(
        BigInteger, primary_key=True, default=UNKNOWN_USER_ID
    )
    count: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    removed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class SyncStatus(Base):
    __tablename__ = "sync_status"

    channel_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("channels.id"), primary_key=True
    )
    last_message_id: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    message_count: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
