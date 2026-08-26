"""
Archives Discord messages, attachments and reactions to PostgreSQL.

Sync strategy: gateway listeners (src/core/listeners.py) write messages in
real time; `Archiver.sync_all()` runs daily as a safety net, scanning each
channel incrementally from its sync_status cursor (minus a small rescan
window to pick up recent edits made while the bot was offline).
"""

import asyncio
import hashlib
import mimetypes
import os
from datetime import UTC, datetime, timedelta
from os.path import join as pj
from urllib.parse import urlparse

import discord
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from src.core.db import get_session
from src.core.init import Log, bot, cfg, httpx_client
from src.core.mediacrypto import StreamEncryptor, load_key
from src.core.models import (
    UNKNOWN_USER_ID,
    Attachment,
    Channel,
    Message,
    MessageVersion,
    Reaction,
    SyncStatus,
    User,
)


def utcnow():
    return datetime.now(UTC)


def get_extension(url, content_type=None):
    """
    Derive a safe file extension from the url or response content type.
    """
    parsed = urlparse(url)
    basename = os.path.basename(parsed.path.rstrip("/"))
    _, ext = os.path.splitext(basename)
    if not ext and content_type:
        guessed = mimetypes.guess_extension(content_type.split(";")[0].strip())
        ext = guessed or ""
    return ext or ".bin"


def _stable_url_id(url):
    """
    Attachment id for embed media: hash of the URL without its query string,
    since Discord CDN signature params change on every fetch.
    """
    parsed = urlparse(url)
    return hashlib.sha1(parsed._replace(query="").geturl().encode()).hexdigest()


async def _upsert(session, model, row, pk_cols):
    stmt = pg_insert(model).values(**row)
    stmt = stmt.on_conflict_do_update(
        index_elements=pk_cols,
        set_={k: stmt.excluded[k] for k in row if k not in pk_cols},
    )
    await session.execute(stmt)


class Archiver:
    def __init__(self):
        self.log = Log.get("archive")
        acfg = cfg["archive"]
        self.media_root = acfg["media_root"]
        self.exclude = set(acfg.get("exclude_channels") or [])
        self.concurrency = acfg.get("download_concurrency", 6)
        self.max_attempts = acfg.get("max_download_attempts", 3)
        self.chunk_size = acfg.get("chunk_size", 4 * 1024 * 1024)
        self.rescan_days = acfg.get("rescan_days", 7)
        self.media_key = load_key()
        if self.media_key is None:
            self.log.warning("ARCHIVE_MEDIA_KEY not set - media stored unencrypted")

    # -- row builders ------------------------------------------------------

    @staticmethod
    def _channel_row(channel):
        return {
            "id": channel.id,
            "name": channel.name,
            "type": str(channel.type),
            "parent_id": getattr(channel, "parent_id", None),
            "archived": bool(getattr(channel, "archived", False)),
            "updated_at": utcnow(),
        }

    @staticmethod
    def _user_row(user):
        return {
            "id": user.id,
            "username": user.name,
            "display_name": user.display_name,
            "is_bot": user.bot,
            "avatar_url": user.display_avatar.url if user.display_avatar else None,
            "updated_at": utcnow(),
        }

    @staticmethod
    def _message_row(m: discord.Message):
        return {
            "id": m.id,
            "channel_id": m.channel.id,
            "author_id": m.author.id,
            "author_name": m.author.display_name,
            "content": m.system_content if m.is_system() else m.content,
            "created_at": m.created_at,
            "edited_at": m.edited_at,
            "type": m.type.name,
            "reply_to_id": m.reference.message_id if m.reference else None,
            "pinned": m.pinned,
            "embeds": [e.to_dict() for e in m.embeds] or None,
            "stickers": [{"id": s.id, "name": s.name, "url": s.url} for s in m.stickers]
            or None,
            "synced_at": utcnow(),
        }

    @staticmethod
    def _attachment_rows(m: discord.Message):
        rows = []
        for att in m.attachments:
            rows.append(
                {
                    "id": str(att.id),
                    "message_id": m.id,
                    "kind": "attachment",
                    "filename": att.filename,
                    "content_type": att.content_type,
                    "size": att.size,
                    "width": att.width,
                    "height": att.height,
                    "source_url": att.url,
                }
            )
        for embed in m.embeds:
            for kind, proxy in [
                ("embed_image", embed.image),
                ("embed_thumbnail", embed.thumbnail),
            ]:
                url = proxy and (proxy.proxy_url or proxy.url)
                if not url:
                    continue
                rows.append(
                    {
                        "id": _stable_url_id(url),
                        "message_id": m.id,
                        "kind": kind,
                        "filename": None,
                        "content_type": None,
                        "size": None,
                        "width": getattr(proxy, "width", None),
                        "height": getattr(proxy, "height", None),
                        "source_url": url,
                    }
                )
        return rows

    # -- message archiving -------------------------------------------------

    async def archive_message(self, session, m: discord.Message, with_reactions=True):
        """
        Upsert one message with its author, attachments and reactions.
        Returns "new", "updated" or "unchanged".
        """
        await _upsert(session, User, self._user_row(m.author), ["id"])
        row = self._message_row(m)
        existing = await session.get(Message, m.id)
        if existing is None:
            session.add(Message(**row))
            result = "new"
        elif existing.content != row["content"] or existing.embeds != row["embeds"]:
            session.add(
                MessageVersion(
                    message_id=existing.id,
                    content=existing.content,
                    embeds=existing.embeds,
                    edited_at=existing.edited_at,
                )
            )
            for k, v in row.items():
                setattr(existing, k, v)
            result = "updated"
        else:
            existing.pinned = row["pinned"]
            existing.edited_at = row["edited_at"]
            result = "unchanged"
        await session.flush()
        for att_row in self._attachment_rows(m):
            # refresh the (expiring) CDN URL and retry counter until downloaded
            stmt = pg_insert(Attachment).values(**att_row)
            stmt = stmt.on_conflict_do_update(
                index_elements=["id"],
                set_={
                    "source_url": stmt.excluded.source_url,
                    "download_attempts": 0,
                },
                where=~Attachment.downloaded,
            )
            await session.execute(stmt)
        if with_reactions and m.reactions:
            await self._archive_reactions(session, m)
        return result

    async def _archive_reactions(self, session, m: discord.Message):
        for reaction in m.reactions:
            emoji = str(reaction.emoji)
            users = []
            try:
                users = await reaction.users().flatten()
            except Exception as e:
                self.log.warning(f"fetch reactors failed for {m.id} {emoji}: {e}")
            rows = (
                [
                    {"message_id": m.id, "emoji": emoji, "user_id": u.id, "count": 1}
                    for u in users
                ]
                if users
                else [
                    {
                        "message_id": m.id,
                        "emoji": emoji,
                        "user_id": UNKNOWN_USER_ID,
                        "count": reaction.count,
                    }
                ]
            )
            for row in rows:
                row["removed_at"] = None
                await _upsert(
                    session, Reaction, row, ["message_id", "emoji", "user_id"]
                )

    async def upsert_channel(self, session, channel):
        await _upsert(session, Channel, self._channel_row(channel), ["id"])

    # -- channel sync ------------------------------------------------------

    async def sync_channel(self, channel, full=False):
        """
        Incrementally archive a channel (or thread) from its cursor, rescanning
        the last `rescan_days` to catch edits made while the bot was offline.
        With full=True, rescan the entire history regardless of the cursor.
        """
        stats = {"new": 0, "updated": 0}
        async with get_session() as session:
            await self.upsert_channel(session, channel)
            status = await session.get(SyncStatus, channel.id)
            last_id = status.last_message_id if status else 0
            rescan_from = discord.utils.time_snowflake(
                utcnow() - timedelta(days=self.rescan_days)
            )
            after_id = 0 if full else min(last_id, rescan_from)
            after = discord.Object(id=after_id) if after_id > 0 else None
            processed = 0
            async for m in channel.history(limit=None, after=after, oldest_first=True):
                result = await self.archive_message(session, m)
                if result in stats:
                    stats[result] += 1
                last_id = max(last_id, m.id)
                processed += 1
                if processed % 500 == 0:
                    await session.commit()
                    self.log.info(
                        f"syncing #{channel.name}: {processed} processed "
                        f"({stats['new']} new)"
                    )
            await _upsert(
                session,
                SyncStatus,
                {
                    "channel_id": channel.id,
                    "last_message_id": last_id,
                    "last_sync_at": utcnow(),
                    "message_count": (status.message_count if status else 0)
                    + stats["new"],
                },
                ["channel_id"],
            )
            await session.commit()
        if stats["new"] or stats["updated"]:
            self.log.info(
                f"synced #{channel.name}: {stats['new']} new, {stats['updated']} updated"
            )
        return stats

    async def sync_all(self, full=False):
        """
        Sync every text channel (and its threads) in the guild, then download
        pending media. Returns aggregate stats.
        """
        guild = bot.get_guild(cfg["guild_id"])
        totals = {"new": 0, "updated": 0}
        for channel in guild.text_channels:
            if channel.name in self.exclude:
                continue
            targets = [channel] + list(channel.threads)
            try:
                async for thread in channel.archived_threads(limit=None):
                    targets.append(thread)
            except discord.HTTPException as e:
                self.log.warning(f"listing archived threads of #{channel.name}: {e}")
            for target in targets:
                stats = await self.sync_channel(target, full=full)
                for k in totals:
                    totals[k] += stats[k]
        downloaded, failed = await self.download_pending()
        totals["downloaded"] = downloaded
        totals["failed"] = failed
        return totals

    # -- media download ----------------------------------------------------

    async def download_pending(self):
        """
        Concurrently download attachments not yet stored. Returns (ok, failed).
        """
        async with get_session() as session:
            rows = (
                (
                    await session.execute(
                        select(Attachment).where(
                            ~Attachment.downloaded,
                            Attachment.download_attempts < self.max_attempts,
                        )
                    )
                )
                .scalars()
                .all()
            )
        if not rows:
            return 0, 0
        os.makedirs(self.media_root, exist_ok=True)
        sem = asyncio.Semaphore(self.concurrency)
        results = await asyncio.gather(*(self._download_one(sem, att) for att in rows))
        async with get_session() as session:
            for att_id, update_values in results:
                obj = await session.get(Attachment, att_id)
                for k, v in update_values.items():
                    setattr(obj, k, v)
            await session.commit()
        ok = sum(1 for _, u in results if u.get("downloaded"))
        return ok, len(results) - ok

    async def _download_one(self, sem, att: Attachment):
        async with sem:
            tmp = pj(self.media_root, f".tmp-{att.id}")
            try:
                digest = hashlib.sha256()
                size = 0
                async with httpx_client.stream("GET", att.source_url) as r:
                    r.raise_for_status()
                    ext = get_extension(att.source_url, r.headers.get("content-type"))
                    content_type = r.headers.get("content-type")
                    with open(tmp, "wb") as f:
                        # encrypt at rest; hash and size refer to the plaintext
                        writer = (
                            StreamEncryptor(f, self.media_key) if self.media_key else f
                        )
                        async for chunk in r.aiter_bytes(self.chunk_size):
                            digest.update(chunk)
                            size += len(chunk)
                            writer.write(chunk)
                sha = digest.hexdigest()
                suffix = ".enc" if self.media_key else ""
                key = pj(sha[:2], f"{sha}{ext}{suffix}")
                path = pj(self.media_root, key)
                os.makedirs(os.path.dirname(path), exist_ok=True)
                if os.path.exists(path):
                    os.remove(tmp)  # identical content already stored
                else:
                    os.replace(tmp, path)
                return att.id, {
                    "downloaded": True,
                    "content_hash": sha,
                    "storage_key": key,
                    "encrypted": self.media_key is not None,
                    "size": size,
                    "content_type": att.content_type or content_type,
                    "downloaded_at": utcnow(),
                }
            except Exception as e:
                self.log.warning(f"download failed ({att.kind} {att.id}): {e}")
                if os.path.exists(tmp):
                    os.remove(tmp)
                return att.id, {"download_attempts": att.download_attempts + 1}


archiver = Archiver()
