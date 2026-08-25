from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from src.core.cortana import cortana
from src.func import functions
from src.func.functions import Func


@pytest.fixture
def archive_env(cfg, monkeypatch):
    """Fake bot + persona so archive handlers run without a Discord connection."""
    monkeypatch.setattr(cortana, "name", "cortana")
    cfg["channel"] = {"food": 10, "meme": 11, "video": 12, "music": 13}
    channel = SimpleNamespace(send=AsyncMock())
    fake_bot = SimpleNamespace(get_channel=Mock(return_value=channel))
    monkeypatch.setattr(functions, "bot", fake_bot)
    return SimpleNamespace(channel=channel, bot=fake_bot)


def make_message(content, attachments=()):
    return SimpleNamespace(
        content=content,
        attachments=list(attachments),
        author=SimpleNamespace(
            display_name="alice",
            color=0x123456,
            avatar=SimpleNamespace(url="https://cdn.test/alice.png"),
        ),
        add_reaction=AsyncMock(),
        guild=None,
        embeds=[],
    )


class TestArchiveKeyword:
    async def test_image_is_archived_as_embed(self, archive_env, cfg):
        att = SimpleNamespace(content_type="image/png", url="https://cdn.test/a.png")
        message = make_message("late night food", [att])

        await Func.archive_keyword(message)

        archive_env.bot.get_channel.assert_called_once_with(cfg["channel"]["food"])
        embed = archive_env.channel.send.call_args.kwargs["embed"]
        assert embed.description == "late night food"
        assert embed.image.url == att.url
        message.add_reaction.assert_awaited_once_with(cfg["emoji"]["cortana"])

    async def test_video_is_forwarded_as_plain_url(self, archive_env):
        att = SimpleNamespace(content_type="video/mp4", url="https://cdn.test/a.mp4")
        message = make_message("meme video", [att])

        await Func.archive_keyword(message)

        assert archive_env.channel.send.call_args.kwargs["content"] == att.url

    async def test_no_keyword_no_archive(self, archive_env):
        att = SimpleNamespace(content_type="image/png", url="https://cdn.test/a.png")
        message = make_message("just chatting", [att])

        await Func.archive_keyword(message)

        archive_env.channel.send.assert_not_awaited()
        message.add_reaction.assert_not_awaited()


class TestArchiveEmbed:
    async def test_embed_is_forwarded_to_matching_channel(self, archive_env, cfg):
        message = make_message("check https://open.spotify.com/track/xyz")
        embed = object()
        message.embeds = [embed]
        guild_channel = SimpleNamespace(send=AsyncMock())
        message.guild = SimpleNamespace(get_channel=Mock(return_value=guild_channel))

        await Func.archive_embed(message)

        message.guild.get_channel.assert_called_once_with(cfg["channel"]["music"])
        assert guild_channel.send.call_args.kwargs["embed"] is embed
        message.add_reaction.assert_awaited_once()

    async def test_warns_when_embed_never_appears(self, archive_env, monkeypatch):
        monkeypatch.setattr(functions.asyncio, "sleep", AsyncMock())
        message = make_message("check https://b23.tv/xyz")
        message.respond = AsyncMock()

        await Func.archive_embed(message)

        embed = message.respond.call_args.kwargs["embed"]
        assert "自动embed失败" in embed.description
        message.add_reaction.assert_not_awaited()

    async def test_non_archive_url_is_ignored(self, archive_env):
        message = make_message("see https://example.com/article")

        await Func.archive_embed(message)

        message.add_reaction.assert_not_awaited()
