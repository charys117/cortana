import os
from datetime import UTC, datetime

import pytest
from aiohttp.test_utils import TestClient, TestServer

from src.core.mediacrypto import StreamEncryptor
from src.core.models import (
    UNKNOWN_USER_ID,
    Attachment,
    Message,
    Reaction,
    User,
)
from src.web.archive_api import (
    _iter_decrypt,
    aggregate_reactions,
    escape_like,
    serialize_message,
)
from src.web.server import build_app

ARCHIVE_ENDPOINTS = [
    "/api/archive/channels",
    "/api/archive/messages?channel_id=1",
    "/api/archive/messages/1/versions",
    "/api/archive/search?q=hello",
    "/api/archive/users",
    "/api/archive/media/1",
]


@pytest.fixture
async def client(cfg, monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("CORTANA_WEB_TOKEN", raising=False)
    test_client = TestClient(TestServer(build_app()))
    await test_client.start_server()
    yield test_client
    await test_client.close()


class TestNoDatabase:
    @pytest.mark.parametrize("path", ARCHIVE_ENDPOINTS)
    async def test_503_when_database_unset(self, client, path):
        resp = await client.get(path)
        assert resp.status == 503
        assert "数据库" in (await resp.json())["error"]


class TestAuth:
    @pytest.fixture
    async def secured_client(self, client, monkeypatch):
        monkeypatch.setenv("CORTANA_WEB_TOKEN", "sekrit")
        return client

    async def test_requires_token(self, secured_client):
        resp = await secured_client.get("/api/archive/channels")
        assert resp.status == 401

    async def test_rejects_wrong_query_token(self, secured_client):
        resp = await secured_client.get("/api/archive/media/1?token=wrong")
        assert resp.status == 401

    async def test_accepts_query_token(self, secured_client):
        # 503 (no DATABASE_URL), not 401: the query-param token passed auth
        resp = await secured_client.get("/api/archive/media/1?token=sekrit")
        assert resp.status == 503


class TestParamValidation:
    """DATABASE_URL is set to a dummy: validation must 400 before any DB use."""

    @pytest.fixture
    async def db_client(self, client, monkeypatch):
        monkeypatch.setenv("DATABASE_URL", "postgresql://unused/unused")
        return client

    @pytest.mark.parametrize(
        "query",
        [
            "",  # missing channel_id
            "channel_id=abc",
            "channel_id=1&before=abc",
            "channel_id=1&limit=abc",
            "channel_id=1&before=2&after=3",
            "channel_id=1&before=2&around=3",
        ],
    )
    async def test_messages_rejects_bad_params(self, db_client, query):
        resp = await db_client.get(f"/api/archive/messages?{query}")
        assert resp.status == 400

    async def test_versions_rejects_non_numeric_id(self, db_client):
        resp = await db_client.get("/api/archive/messages/abc/versions")
        assert resp.status == 400

    @pytest.mark.parametrize("query", ["", "q=x", "q=%20%20", "q=ok&channel_id=abc"])
    async def test_search_rejects_bad_params(self, db_client, query):
        resp = await db_client.get(f"/api/archive/search?{query}")
        assert resp.status == 400


class TestEscapeLike:
    def test_escapes_wildcards_and_backslash(self):
        assert escape_like(r"50%_off\now") == r"50\%\_off\\now"

    def test_plain_text_unchanged(self):
        assert escape_like("你好 cortana") == "你好 cortana"


class TestAggregateReactions:
    def test_individual_rows_are_counted(self):
        rows = [
            Reaction(message_id=1, emoji="👍", user_id=10, count=1),
            Reaction(message_id=1, emoji="👍", user_id=11, count=1),
            Reaction(message_id=1, emoji="🎉", user_id=10, count=1),
        ]
        result = {r["emoji"]: r["count"] for r in aggregate_reactions(rows)}
        assert result == {"👍": 2, "🎉": 1}

    def test_bulk_row_does_not_double_count(self):
        # a bulk-scan aggregate and per-user rows can overlap for one emoji
        rows = [
            Reaction(message_id=1, emoji="👍", user_id=UNKNOWN_USER_ID, count=5),
            Reaction(message_id=1, emoji="👍", user_id=10, count=1),
            Reaction(message_id=1, emoji="👍", user_id=11, count=1),
        ]
        assert aggregate_reactions(rows) == [{"emoji": "👍", "count": 5}]

    def test_individual_rows_win_when_more_numerous(self):
        rows = [
            Reaction(message_id=1, emoji="👍", user_id=UNKNOWN_USER_ID, count=1),
            Reaction(message_id=1, emoji="👍", user_id=10, count=1),
            Reaction(message_id=1, emoji="👍", user_id=11, count=1),
        ]
        assert aggregate_reactions(rows) == [{"emoji": "👍", "count": 2}]


def make_message(**overrides):
    values = {
        "id": 111222333444555666,
        "channel_id": 1,
        "author_id": 42,
        "author_name": "小明",
        "content": "hello",
        "created_at": datetime(2026, 8, 26, 12, 0, tzinfo=UTC),
        "edited_at": None,
        "type": "default",
        "reply_to_id": None,
        "pinned": False,
        "deleted_at": None,
        "embeds": None,
        "stickers": None,
    }
    values.update(overrides)
    return Message(**values)


class TestSerializeMessage:
    def test_ids_are_strings_and_dates_iso(self):
        user = User(id=42, username="ming", is_bot=False, avatar_url="http://a/x")
        out = serialize_message(make_message(), users={42: user})
        assert out["id"] == "111222333444555666"
        assert out["channel_id"] == "1"
        assert out["author_id"] == "42"
        assert out["created_at"] == "2026-08-26T12:00:00+00:00"
        assert out["avatar_url"] == "http://a/x"
        assert out["reply_to"] is None
        assert out["embeds"] == []

    def test_missing_reply_reference(self):
        out = serialize_message(make_message(reply_to_id=99))
        assert out["reply_to"] == {"id": "99", "missing": True}

    def test_attachment_url_only_when_downloaded(self):
        atts = [
            Attachment(
                id="a1",
                message_id=1,
                kind="attachment",
                source_url="http://cdn/x",
                downloaded=True,
                storage_key="ab/abc.png",
            ),
            Attachment(
                id="a2",
                message_id=1,
                kind="attachment",
                source_url="http://cdn/y",
                downloaded=False,
                storage_key=None,
            ),
        ]
        out = serialize_message(make_message(), attachments=atts)
        assert out["attachments"][0]["url"] == "/api/archive/media/a1"
        assert out["attachments"][1]["url"] is None


class TestIterDecrypt:
    async def test_roundtrip(self, tmp_path):
        key = os.urandom(32)
        chunks = [b"hello ", b"cortana " * 1000, b"!"]
        path = tmp_path / "f.enc"
        with open(path, "wb") as f:
            enc = StreamEncryptor(f, key)
            for chunk in chunks:
                enc.write(chunk)
        out = b""
        async for plain in _iter_decrypt(str(path), key):
            out += plain
        assert out == b"".join(chunks)

    async def test_rejects_non_cag1(self, tmp_path):
        path = tmp_path / "f.enc"
        path.write_bytes(b"plain old file")
        with pytest.raises(ValueError):
            async for _ in _iter_decrypt(str(path), os.urandom(32)):
                pass
