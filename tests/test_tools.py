from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from src.core import tools
from src.core.tools import format_units, identify, warning


class TestFormatUnits:
    def test_zero_and_negative_are_empty(self):
        assert format_units([":heart:"], 0) == ""
        assert format_units([":heart:"], -3) == ""

    def test_single_unit_below_row_size(self):
        assert format_units([":heart:"], 3) == ":heart::heart::heart:\n"

    def test_full_rows_and_remainder(self):
        # 7 = one full row of 5 plus a remainder row of 2
        assert format_units(["x"], 7) == "xxxxx\nxx\n"

    def test_exact_multiple_of_row_size_has_no_remainder_row(self):
        assert format_units(["x"], 10) == "xxxxx\nxxxxx\n"

    def test_decimal_split_across_units(self):
        # 23 = 2 tens + 3 ones; bigger units are printed first
        assert format_units(["o", "T"], 23) == "TT\nooo\n"

    def test_custom_row_size(self):
        assert format_units(["x"], 4, row_size=2) == "xx\nxx\n"


class TestIdentify:
    @pytest.fixture(autouse=True)
    def members(self, cfg):
        cfg["member"] = {"alice": 1, "bob": 2}

    @staticmethod
    def message_from(author_id):
        return SimpleNamespace(author=SimpleNamespace(id=author_id))

    def test_first_of_pair(self):
        assert identify(self.message_from(1)) == ("alice", "bob")

    def test_second_of_pair(self):
        assert identify(self.message_from(2)) == ("bob", "alice")

    def test_unknown_author(self):
        assert identify(self.message_from(999)) == (None, None)


class TestWarning:
    async def test_responds_to_message(self):
        message = SimpleNamespace(respond=AsyncMock())
        await warning("careful", message=message)
        embed = message.respond.call_args.kwargs["embed"]
        assert embed.description == "careful"

    async def test_falls_back_to_channel_send_without_respond(self):
        # plain discord.Message has no .respond; warning falls back to channel.send
        message = SimpleNamespace(channel=SimpleNamespace(send=AsyncMock()))
        await warning("careful", message=message)
        message.channel.send.assert_awaited_once()

    async def test_sends_to_channel(self):
        channel = SimpleNamespace(send=AsyncMock())
        await warning("careful", channel=channel)
        channel.send.assert_awaited_once()

    async def test_requires_channel_or_message(self):
        with pytest.raises(ValueError):
            await warning("careful")


class TestModifyBoard:
    @pytest.fixture
    def board_env(self, cfg, monkeypatch):
        cfg["channel"] = {"a-board": 111}
        bot_user = object()

        def make(amount, author):
            board = SimpleNamespace(
                content=f"**CURRENT**:\n:heart:\n{amount}",
                author=author,
                edit=AsyncMock(),
            )
            channel = SimpleNamespace(
                history=Mock(
                    return_value=SimpleNamespace(
                        flatten=AsyncMock(return_value=[board])
                    )
                ),
                send=AsyncMock(),
            )
            fake_bot = SimpleNamespace(
                user=bot_user, get_channel=Mock(return_value=channel)
            )
            monkeypatch.setattr(tools, "bot", fake_bot)
            return board, channel, bot_user

        return make

    async def test_edits_own_board_message(self, board_env):
        board, channel, bot_user = board_env(3, author=None)
        board.author = bot_user
        assert await tools.modify_board("alice", 2) == 5
        new_content = board.edit.call_args.kwargs["content"]
        assert new_content.endswith("5")
        assert "**CURRENT**:" in new_content
        channel.send.assert_not_awaited()

    async def test_sends_new_message_when_board_is_foreign(self, board_env):
        board, channel, _ = board_env(10, author=object())
        assert await tools.modify_board("alice", -4) == 6
        board.edit.assert_not_awaited()
        channel.send.assert_awaited_once()

    async def test_negative_total_keeps_plain_number(self, board_env):
        board, _, bot_user = board_env(1, author=None)
        board.author = bot_user
        assert await tools.modify_board("alice", -3) == -2
        # no units are rendered for a non-positive total
        assert board.edit.call_args.kwargs["content"] == "**CURRENT**:\n-2"
