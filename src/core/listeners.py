"""
Gateway listeners for real-time archiving.

Registered with @bot.listen so they coexist with the @bot.event handlers in
run.py. The daily Archiver.sync_all() sweep backfills anything missed while
the bot was offline.
"""

import discord
from sqlalchemy import update

from src.core.archiver import _upsert, archiver, utcnow
from src.core.db import get_session
from src.core.init import Log, bot, cfg
from src.core.models import Message, Reaction

log = Log.get("archive")


def _archivable(channel) -> bool:
    guild = getattr(channel, "guild", None)
    return (
        guild is not None
        and guild.id == cfg["guild_id"]
        and getattr(channel, "name", None) not in archiver.exclude
    )


async def _archive_full_message(m: discord.Message):
    async with get_session() as session:
        await archiver.upsert_channel(session, m.channel)
        await archiver.archive_message(session, m)
        await session.commit()
    if m.attachments or m.embeds:
        await archiver.download_pending()


async def _ensure_message(session, channel_id, message_id) -> bool:
    """
    Make sure a message row exists (FK target); fetch and archive it if not.
    """
    if await session.get(Message, message_id) is not None:
        return True
    channel = bot.get_channel(channel_id)
    if channel is None or not _archivable(channel):
        return False
    try:
        m = await channel.fetch_message(message_id)
    except discord.HTTPException:
        return False
    await archiver.upsert_channel(session, channel)
    await archiver.archive_message(session, m)
    return True


@bot.listen("on_message")
async def archive_on_message(message: discord.Message):
    if not _archivable(message.channel):
        return
    try:
        await _archive_full_message(message)
    except Exception as e:
        log.error(f"archive on_message {message.id} failed: {e}")


@bot.listen("on_raw_message_edit")
async def archive_on_edit(payload: discord.RawMessageUpdateEvent):
    channel = bot.get_channel(payload.channel_id)
    if channel is None or not _archivable(channel):
        return
    try:
        m = await channel.fetch_message(payload.message_id)
        await _archive_full_message(m)
    except discord.NotFound:
        pass
    except Exception as e:
        log.error(f"archive on_edit {payload.message_id} failed: {e}")


@bot.listen("on_raw_message_delete")
async def archive_on_delete(payload: discord.RawMessageDeleteEvent):
    await _mark_deleted([payload.message_id])


@bot.listen("on_raw_bulk_message_delete")
async def archive_on_bulk_delete(payload: discord.RawBulkMessageDeleteEvent):
    await _mark_deleted(list(payload.message_ids))


async def _mark_deleted(message_ids):
    try:
        async with get_session() as session:
            await session.execute(
                update(Message)
                .where(Message.id.in_(message_ids), Message.deleted_at.is_(None))
                .values(deleted_at=utcnow())
            )
            await session.commit()
    except Exception as e:
        log.error(f"archive mark deleted {message_ids} failed: {e}")


@bot.listen("on_raw_reaction_add")
async def archive_on_reaction_add(payload: discord.RawReactionActionEvent):
    try:
        async with get_session() as session:
            if not await _ensure_message(session, payload.channel_id, payload.message_id):
                return
            await _upsert(
                session,
                Reaction,
                {
                    "message_id": payload.message_id,
                    "emoji": str(payload.emoji),
                    "user_id": payload.user_id,
                    "count": 1,
                    "removed_at": None,
                },
                ["message_id", "emoji", "user_id"],
            )
            await session.commit()
    except Exception as e:
        log.error(f"archive reaction add {payload.message_id} failed: {e}")


@bot.listen("on_raw_reaction_remove")
async def archive_on_reaction_remove(payload: discord.RawReactionActionEvent):
    try:
        async with get_session() as session:
            await session.execute(
                update(Reaction)
                .where(
                    Reaction.message_id == payload.message_id,
                    Reaction.emoji == str(payload.emoji),
                    Reaction.user_id == payload.user_id,
                )
                .values(removed_at=utcnow())
            )
            await session.commit()
    except Exception as e:
        log.error(f"archive reaction remove {payload.message_id} failed: {e}")


@bot.listen("on_guild_channel_pins_update")
async def archive_on_pins_update(channel, last_pin):
    if not _archivable(channel):
        return
    try:
        pins = await channel.pins()
        async with get_session() as session:
            for m in pins:
                await _ensure_message(session, channel.id, m.id)
            pinned_ids = [m.id for m in pins]
            await session.execute(
                update(Message)
                .where(Message.channel_id == channel.id)
                .values(pinned=Message.id.in_(pinned_ids) if pinned_ids else False)
            )
            await session.commit()
    except Exception as e:
        log.error(f"archive pins update #{channel} failed: {e}")
