"""
Read-only API over the PostgreSQL message archive for the web UI.

Snowflake IDs are serialized as strings (they exceed JS Number.MAX_SAFE_INTEGER)
and timestamps as ISO 8601. Message pagination is keyset-based on the message id
(snowflakes are time-ordered), served by the (channel_id, id) composite index;
search relies on the pg_trgm GIN index on messages.content.
"""

import asyncio
import os
from datetime import UTC, datetime

from aiohttp import web
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from discord.utils import time_snowflake
from sqlalchemy import select

from src.core.db import get_session
from src.core.init import cfg
from src.core.mediacrypto import MAGIC, load_key
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

REPLY_EXCERPT_LEN = 200


def _db_missing():
    if os.environ.get("DATABASE_URL"):
        return None
    return web.json_response({"error": "未配置数据库, 归档功能不可用"}, status=503)


def sid(v):
    return str(v) if v is not None else None


def iso(dt):
    return dt.isoformat() if dt is not None else None


def _snowflake_param(request, name):
    """Parse an optional numeric query param; returns (value, error_response)."""
    raw = request.query.get(name)
    if raw is None:
        return None, None
    if not raw.isdigit():
        return None, web.json_response({"error": f"无效的参数: {name}"}, status=400)
    return int(raw), None


def _datetime_param(request, name):
    """Parse an optional ISO 8601 query param; returns (aware value, error)."""
    raw = request.query.get(name)
    if raw is None:
        return None, None
    try:
        dt = datetime.fromisoformat(raw)
    except ValueError:
        return None, web.json_response({"error": f"无效的参数: {name}"}, status=400)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt, None


def _limit_param(request, default, maximum):
    raw = request.query.get("limit")
    if raw is None:
        return default, None
    if not raw.isdigit():
        return None, web.json_response({"error": "无效的参数: limit"}, status=400)
    return max(1, min(int(raw), maximum)), None


def escape_like(s):
    return s.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def aggregate_reactions(rows):
    """
    Collapse reaction rows of one message into [{emoji, count}].

    Bulk-scan rows (user_id=UNKNOWN_USER_ID) carry an aggregate count that may
    overlap with per-user rows for the same emoji, so take the max of the two
    instead of summing.
    """
    bulk = {}
    individual = {}
    for r in rows:
        if r.user_id == UNKNOWN_USER_ID:
            bulk[r.emoji] = r.count
        else:
            individual[r.emoji] = individual.get(r.emoji, 0) + 1
    return [
        {"emoji": e, "count": max(bulk.get(e, 0), individual.get(e, 0))}
        for e in sorted(set(bulk) | set(individual))
    ]


def serialize_attachment(att):
    return {
        "id": att.id,
        "kind": att.kind,
        "filename": att.filename,
        "content_type": att.content_type,
        "size": att.size,
        "width": att.width,
        "height": att.height,
        "downloaded": att.downloaded,
        "url": f"/api/archive/media/{att.id}"
        if att.downloaded and att.storage_key
        else None,
    }


def serialize_message(m, users=None, attachments=None, reactions=None, replies=None):
    user = (users or {}).get(m.author_id)
    out = {
        "id": sid(m.id),
        "channel_id": sid(m.channel_id),
        "author_id": sid(m.author_id),
        "author_name": m.author_name,
        "avatar_url": user.avatar_url if user else None,
        "is_bot": user.is_bot if user else False,
        "content": m.content,
        "created_at": iso(m.created_at),
        "edited_at": iso(m.edited_at),
        "deleted_at": iso(m.deleted_at),
        "type": m.type,
        "pinned": m.pinned,
        "embeds": m.embeds or [],
        "stickers": m.stickers or [],
        "attachments": [serialize_attachment(a) for a in (attachments or [])],
        "reactions": aggregate_reactions(reactions or []),
    }
    if m.reply_to_id is None:
        out["reply_to"] = None
    else:
        ref = (replies or {}).get(m.reply_to_id)
        if ref is None:
            out["reply_to"] = {"id": sid(m.reply_to_id), "missing": True}
        else:
            out["reply_to"] = {
                "id": sid(ref.id),
                "author_name": ref.author_name,
                "content": (ref.content or "")[:REPLY_EXCERPT_LEN],
                "deleted": ref.deleted_at is not None,
            }
    return out


async def _load_message_extras(session, msgs):
    """Batch-load users, attachments, reactions and reply excerpts for a page."""
    ids = [m.id for m in msgs]
    if not ids:
        return {}, {}, {}, {}
    users = {
        u.id: u
        for u in (
            await session.execute(
                select(User).where(User.id.in_({m.author_id for m in msgs}))
            )
        ).scalars()
    }
    atts_by_msg = {}
    for a in (
        await session.execute(
            select(Attachment)
            .where(Attachment.message_id.in_(ids))
            .order_by(Attachment.id)
        )
    ).scalars():
        atts_by_msg.setdefault(a.message_id, []).append(a)
    reacts_by_msg = {}
    for r in (
        await session.execute(
            select(Reaction).where(
                Reaction.message_id.in_(ids), Reaction.removed_at.is_(None)
            )
        )
    ).scalars():
        reacts_by_msg.setdefault(r.message_id, []).append(r)
    replies = {}
    reply_ids = {m.reply_to_id for m in msgs if m.reply_to_id is not None}
    if reply_ids:
        replies = {
            row.id: row
            for row in (
                await session.execute(
                    select(
                        Message.id,
                        Message.author_name,
                        Message.content,
                        Message.deleted_at,
                    ).where(Message.id.in_(reply_ids))
                )
            ).all()
        }
    return users, atts_by_msg, reacts_by_msg, replies


async def get_channels(_request):
    if err := _db_missing():
        return err
    async with get_session() as session:
        rows = (
            await session.execute(
                select(Channel, SyncStatus.message_count, SyncStatus.last_sync_at)
                .join(SyncStatus, SyncStatus.channel_id == Channel.id, isouter=True)
                .order_by(Channel.name)
            )
        ).all()
    return web.json_response(
        {
            "channels": [
                {
                    "id": sid(c.id),
                    "name": c.name,
                    "type": c.type,
                    "parent_id": sid(c.parent_id),
                    "archived": c.archived,
                    "message_count": count or 0,
                    "last_sync_at": iso(last_sync),
                }
                for c, count, last_sync in rows
            ]
        }
    )


async def get_messages(request):
    if err := _db_missing():
        return err
    channel_id, err = _snowflake_param(request, "channel_id")
    if err:
        return err
    if channel_id is None:
        return web.json_response({"error": "缺少参数: channel_id"}, status=400)
    cursors = {}
    for name in ("before", "after", "around"):
        cursors[name], err = _snowflake_param(request, name)
        if err:
            return err
    if sum(v is not None for v in cursors.values()) > 1:
        return web.json_response(
            {"error": "before/after/around 只能指定一个"}, status=400
        )
    limit, err = _limit_param(request, default=50, maximum=100)
    if err:
        return err
    before, after, around = cursors["before"], cursors["after"], cursors["around"]

    base = select(Message).where(Message.channel_id == channel_id)
    async with get_session() as session:
        # has_more_* via the limit+1 trick; COUNT(*) is never issued
        if around is not None:
            half = limit // 2
            older = (
                (
                    await session.execute(
                        base.where(Message.id < around)
                        .order_by(Message.id.desc())
                        .limit(half + 1)
                    )
                )
                .scalars()
                .all()
            )
            has_more_before = len(older) > half
            older = older[:half]
            rest = limit - len(older)
            newer = (
                (
                    await session.execute(
                        base.where(Message.id >= around)
                        .order_by(Message.id.asc())
                        .limit(rest + 1)
                    )
                )
                .scalars()
                .all()
            )
            has_more_after = len(newer) > rest
            msgs = list(reversed(older)) + newer[:rest]
        elif after is not None:
            rows = (
                (
                    await session.execute(
                        base.where(Message.id > after)
                        .order_by(Message.id.asc())
                        .limit(limit + 1)
                    )
                )
                .scalars()
                .all()
            )
            has_more_after = len(rows) > limit
            has_more_before = True  # the cursor message itself is older
            msgs = rows[:limit]
        elif before is not None:
            rows = (
                (
                    await session.execute(
                        base.where(Message.id < before)
                        .order_by(Message.id.desc())
                        .limit(limit + 1)
                    )
                )
                .scalars()
                .all()
            )
            has_more_before = len(rows) > limit
            has_more_after = True  # the cursor message itself is newer
            msgs = list(reversed(rows[:limit]))
        else:
            rows = (
                (
                    await session.execute(
                        base.order_by(Message.id.desc()).limit(limit + 1)
                    )
                )
                .scalars()
                .all()
            )
            has_more_before = len(rows) > limit
            has_more_after = False
            msgs = list(reversed(rows[:limit]))

        users, atts, reacts, replies = await _load_message_extras(session, msgs)

    return web.json_response(
        {
            "messages": [
                serialize_message(m, users, atts.get(m.id), reacts.get(m.id), replies)
                for m in msgs
            ],
            "has_more_before": has_more_before,
            "has_more_after": has_more_after,
        }
    )


async def get_versions(request):
    if err := _db_missing():
        return err
    raw = request.match_info["id"]
    if not raw.isdigit():
        return web.json_response({"error": "无效的消息id"}, status=400)
    async with get_session() as session:
        rows = (
            (
                await session.execute(
                    select(MessageVersion)
                    .where(MessageVersion.message_id == int(raw))
                    .order_by(MessageVersion.captured_at.asc())
                )
            )
            .scalars()
            .all()
        )
    return web.json_response(
        {
            "versions": [
                {
                    "content": v.content,
                    "embeds": v.embeds or [],
                    "edited_at": iso(v.edited_at),
                    "captured_at": iso(v.captured_at),
                }
                for v in rows
            ]
        }
    )


async def search_messages(request):
    if err := _db_missing():
        return err
    q = (request.query.get("q") or "").strip()
    if len(q) < 2:
        return web.json_response({"error": "搜索词至少2个字符"}, status=400)
    limit, err = _limit_param(request, default=25, maximum=50)
    if err:
        return err
    channel_id, err = _snowflake_param(request, "channel_id")
    if err:
        return err
    author_id, err = _snowflake_param(request, "author_id")
    if err:
        return err
    before, err = _snowflake_param(request, "before")
    if err:
        return err
    since, err = _datetime_param(request, "since")
    if err:
        return err
    until, err = _datetime_param(request, "until")
    if err:
        return err

    # ILIKE '%…%' is served by the GIN gin_trgm_ops index on content
    stmt = (
        select(Message, Channel.name)
        .join(Channel, Channel.id == Message.channel_id)
        .where(Message.content.ilike(f"%{escape_like(q)}%", escape="\\"))
    )
    if channel_id is not None:
        stmt = stmt.where(Message.channel_id == channel_id)
    if author_id is not None:
        stmt = stmt.where(Message.author_id == author_id)
    if before is not None:
        stmt = stmt.where(Message.id < before)
    # date bounds become snowflake bounds so they share the id column with
    # ordering and the keyset cursor: since inclusive, until exclusive
    if since is not None:
        stmt = stmt.where(Message.id >= time_snowflake(since))
    if until is not None:
        stmt = stmt.where(Message.id < time_snowflake(until))
    stmt = stmt.order_by(Message.id.desc()).limit(limit + 1)

    async with get_session() as session:
        rows = (await session.execute(stmt)).all()
        has_more = len(rows) > limit
        rows = rows[:limit]
        msgs = [m for m, _ in rows]
        users = {}
        if msgs:
            users = {
                u.id: u
                for u in (
                    await session.execute(
                        select(User).where(User.id.in_({m.author_id for m in msgs}))
                    )
                ).scalars()
            }

    results = []
    for m, channel_name in rows:
        item = serialize_message(m, users)
        item["channel_name"] = channel_name
        results.append(item)
    return web.json_response({"results": results, "has_more": has_more})


async def get_users(_request):
    if err := _db_missing():
        return err
    async with get_session() as session:
        rows = (
            (await session.execute(select(User).order_by(User.username)))
            .scalars()
            .all()
        )
    return web.json_response(
        {
            "users": [
                {
                    "id": sid(u.id),
                    "username": u.username,
                    "display_name": u.display_name,
                    "avatar_url": u.avatar_url,
                    "is_bot": u.is_bot,
                }
                for u in rows
            ]
        }
    )


async def _iter_decrypt(path, key):
    """Yield plaintext chunks of a CAG1 file, one chunk in memory at a time."""
    aes = AESGCM(key)
    f = await asyncio.to_thread(open, path, "rb")
    try:
        header = await asyncio.to_thread(f.read, 12)
        if header[:4] != MAGIC:
            raise ValueError(f"{path} is not a CAG1 encrypted file")
        file_id = header[4:12]
        counter = 0
        while True:
            length = await asyncio.to_thread(f.read, 4)
            if not length:
                break
            ct = await asyncio.to_thread(f.read, int.from_bytes(length, "big"))
            nonce = file_id + counter.to_bytes(4, "big")
            yield aes.decrypt(nonce, ct, None)
            counter += 1
    finally:
        f.close()


async def get_media(request):
    if err := _db_missing():
        return err
    att_id = request.match_info["id"]
    async with get_session() as session:
        att = await session.get(Attachment, att_id)
    if (
        att is None
        or not att.downloaded
        or not att.storage_key
        or ".." in att.storage_key  # server-generated, but defense in depth
    ):
        return web.json_response({"error": "附件不存在或未下载"}, status=404)
    media_root = (cfg.get("archive") or {}).get("media_root")
    if not media_root:
        return web.json_response({"error": "archive.media_root未配置"}, status=503)
    path = os.path.join(media_root, att.storage_key)
    if not os.path.isfile(path):
        return web.json_response({"error": "归档文件缺失"}, status=404)

    content_type = att.content_type or "application/octet-stream"
    # content-addressed storage: the bytes behind an id never change
    cache = {"Cache-Control": "private, max-age=31536000, immutable"}
    if not att.encrypted:
        # FileResponse handles ETag/Range/conditional requests itself
        return web.FileResponse(path, headers={**cache, "Content-Type": content_type})

    key = load_key()
    if key is None:
        return web.json_response(
            {"error": "ARCHIVE_MEDIA_KEY未配置, 无法解密媒体"}, status=503
        )
    etag = f'"{att.content_hash}"' if att.content_hash else None
    if etag and request.headers.get("If-None-Match") == etag:
        return web.Response(status=304, headers=cache)
    resp = web.StreamResponse(status=200, headers=cache)
    resp.content_type = content_type
    if etag:
        resp.headers["ETag"] = etag
    if att.size:
        resp.content_length = att.size  # archiver records the plaintext size
    await resp.prepare(request)
    async for chunk in _iter_decrypt(path, key):
        await resp.write(chunk)
    await resp.write_eof()
    return resp


def register_archive_routes(app):
    app.router.add_get("/api/archive/channels", get_channels)
    app.router.add_get("/api/archive/messages", get_messages)
    app.router.add_get("/api/archive/messages/{id}/versions", get_versions)
    app.router.add_get("/api/archive/search", search_messages)
    app.router.add_get("/api/archive/users", get_users)
    app.router.add_get("/api/archive/media/{id}", get_media)
