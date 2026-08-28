"""Pure-logic tests for the archiver (no database, no Discord connection)."""

from types import SimpleNamespace

import discord

from src.core.archiver import Archiver, _stable_url_id, get_extension


class TestGetExtension:
    def test_from_url_path(self):
        assert get_extension("https://cdn.example.com/a/photo.PNG?x=1") == ".PNG"

    def test_from_content_type_when_url_has_none(self):
        assert get_extension("https://x.test/file", "image/png") == ".png"

    def test_content_type_charset_suffix_is_ignored(self):
        assert (
            get_extension("https://x.test/file", "text/plain; charset=utf-8") == ".txt"
        )

    def test_fallback_is_bin(self):
        assert get_extension("https://x.test/file") == ".bin"
        assert (
            get_extension("https://x.test/file", "application/x-unknown-zzz") == ".bin"
        )


class TestStableUrlId:
    def test_ignores_query_string(self):
        # Discord CDN signature params change on every fetch
        a = _stable_url_id("https://cdn.discordapp.com/a/1/x.png?ex=1&sig=aaa")
        b = _stable_url_id("https://cdn.discordapp.com/a/1/x.png?ex=2&sig=bbb")
        assert a == b

    def test_distinct_paths_differ(self):
        assert _stable_url_id("https://x.test/a.png") != _stable_url_id(
            "https://x.test/b.png"
        )


def make_message(**overrides):
    m = SimpleNamespace(
        id=111222333,
        channel=SimpleNamespace(id=555),
        author=SimpleNamespace(
            id=1,
            name="alice",
            display_name="Alice",
            bot=False,
            display_avatar=SimpleNamespace(url="https://cdn.test/a.png"),
        ),
        content="hello",
        created_at=None,
        edited_at=None,
        type=SimpleNamespace(name="default"),
        reference=None,
        pinned=False,
        embeds=[],
        stickers=[],
        attachments=[],
        reactions=[],
    )
    m.is_system = lambda: False
    for k, v in overrides.items():
        setattr(m, k, v)
    return m


class TestRowBuilders:
    def test_message_row_basics(self):
        row = Archiver._message_row(make_message())
        assert row["id"] == 111222333
        assert row["channel_id"] == 555
        assert row["author_name"] == "Alice"
        assert row["content"] == "hello"
        assert row["type"] == "default"
        assert row["embeds"] is None and row["stickers"] is None

    def test_reply_reference_is_captured(self):
        m = make_message(reference=SimpleNamespace(message_id=999))
        assert Archiver._message_row(m)["reply_to_id"] == 999

    def test_attachment_rows(self):
        att = SimpleNamespace(
            id=777,
            filename="pic.png",
            content_type="image/png",
            size=123,
            width=10,
            height=20,
            url="https://cdn.discordapp.com/attachments/1/777/pic.png?ex=abc",
        )
        embed = discord.Embed(title="t")
        embed.set_image(url="https://img.example/foo.png")
        rows = Archiver._attachment_rows(
            make_message(attachments=[att], embeds=[embed])
        )
        kinds = {r["kind"] for r in rows}
        assert kinds == {"attachment", "embed_image"}
        att_row = next(r for r in rows if r["kind"] == "attachment")
        assert att_row["id"] == "777"
        assert att_row["filename"] == "pic.png"

    def test_channel_row_thread_fields(self):
        thread = SimpleNamespace(
            id=9, name="t", type="public_thread", parent_id=5, archived=True
        )
        row = Archiver._channel_row(thread)
        assert row["parent_id"] == 5 and row["archived"] is True
        assert row["position"] is None  # threads carry no sidebar position

    def test_channel_row_text_channel_defaults(self):
        ch = SimpleNamespace(id=5, name="chat", type="text")
        row = Archiver._channel_row(ch)
        assert row["parent_id"] is None and row["archived"] is False

    def test_channel_row_captures_position(self):
        ch = SimpleNamespace(id=5, name="chat", type="text", parent_id=3, position=2)
        row = Archiver._channel_row(ch)
        assert row["position"] == 2
