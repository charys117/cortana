import os
from types import SimpleNamespace

import pytest

from src.core.backup import Backup


@pytest.fixture
def backup(cfg, tmp_path):
    cfg["backup"]["local_folder"] = str(tmp_path / "backup")
    return Backup()


class TestGetExtension:
    def test_from_url_path(self, backup):
        assert (
            backup._get_extension("https://cdn.example.com/a/photo.PNG?x=1") == ".PNG"
        )

    def test_from_content_type_when_url_has_none(self, backup):
        assert backup._get_extension("https://x.test/file", "image/png") == ".png"

    def test_content_type_charset_suffix_is_ignored(self, backup):
        ext = backup._get_extension("https://x.test/file", "text/plain; charset=utf-8")
        assert ext == ".txt"

    def test_fallback_is_bin(self, backup):
        assert backup._get_extension("https://x.test/file") == ".bin"
        assert (
            backup._get_extension("https://x.test/file", "application/x-unknown-zzz")
            == ".bin"
        )


class TestResolvePath:
    def test_joins_under_backup_root(self, backup):
        path = backup._resolve_path("chat", "240101.md")
        assert path == os.path.join(backup.backup_root, "chat", "240101.md")

    def test_skips_none_and_empty_and_strips_slashes(self, backup):
        assert backup._resolve_path(None, "", "/chat/") == os.path.join(
            backup.backup_root, "chat"
        )

    def test_no_parts_resolves_to_root(self, backup):
        assert backup._resolve_path() == backup.backup_root


class TestMessageToMd:
    @staticmethod
    def make_message(content):
        return SimpleNamespace(
            author=SimpleNamespace(display_name="alice"),
            content=content,
            embeds=[],
            attachments=[],
        )

    async def test_plain_message(self, backup):
        md = await backup.message_to_md(
            self.make_message("hello"), "240101-120000", "chat", "attachments"
        )
        assert md == "#### alice-240101-120000\nhello"

    async def test_fate_emoji_is_replaced(self, backup, cfg):
        md = await backup.message_to_md(
            self.make_message(f"cast {cfg['emoji']['fate']}!"),
            "240101-120000",
            "chat",
            "attachments",
        )
        assert md.endswith("cast 🔮!")
        assert cfg["emoji"]["fate"] not in md

    async def test_rich_embed_without_images(self, backup):
        embed = SimpleNamespace(
            type="rich",
            author=SimpleNamespace(name="somebody"),
            title="A title",
            description="A description",
            url="https://example.com/post",
            image=None,
        )
        message = self.make_message("")
        message.embeds = [embed]
        md = await backup.message_to_md(message, "240101-120000", "chat", "attachments")
        assert md.split("\n") == [
            "#### alice-240101-120000",
            "somebody:",
            "A title",
            "A description",
            "<https://example.com/post>",
        ]
