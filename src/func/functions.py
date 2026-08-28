"""
Contains functions that are used in the main bot file.
"""

import asyncio
import re
from datetime import UTC, datetime, timedelta

import discord

from src.core.archiver import archiver
from src.core.cortana import cortana
from src.core.init import Log, bot, cfg
from src.core.tools import daily_report, warning

log = Log.get("func")


class Func:
    @staticmethod
    async def archive_keyword(message):
        """
        Archives the message based on keyword matching.

        Args:
            message (discord.Message): The message to be archived.
        """
        for channel_name, keyword in cfg["archive_keyword"].items():
            if re.search("|".join(keyword), message.content):
                channel = bot.get_channel(cfg["channel"][channel_name])
                if "video" in message.attachments[0].content_type:
                    await channel.send(content=message.attachments[0].url)
                else:
                    embed = discord.Embed(
                        description=message.content, color=message.author.color
                    )
                    embed.set_author(
                        name=message.author.display_name,
                        icon_url=message.author.avatar.url,
                    )
                    embed.set_image(url=message.attachments[0].url)
                    await channel.send(embed=embed)
                await message.add_reaction(cortana.get_emoji())
                return

    @staticmethod
    async def archive_embed(message):
        """
        Archives the embedded message in the appropriate channel based on the content of the message.

        Args:
            message (discord.Message): The message containing the embedded content.
        """
        for k, i in cfg["archive_embed"].items():
            if any(url in message.content for url in i):
                times = 0
                while not message.embeds:
                    times += 1
                    await asyncio.sleep(1)
                    if times == 5:
                        await warning("自动embed失败", message=message)
                        return
                await message.guild.get_channel(cfg["channel"][k]).send(
                    embed=message.embeds[0]
                )
                await message.add_reaction(cortana.get_emoji())
                return

    @staticmethod
    async def daily():
        ch_name = cfg["daily"]["channel"]
        channel = bot.get_channel(cfg["channel"][ch_name])
        # avatars ride along as attachments: the shift below invalidates the
        # old avatar hash while Discord's embed proxy fetches icon URLs at
        # send time, so a URL icon randomly 404s and stays broken forever
        offline_file = discord.File(cortana.avatar_path(), filename="offline.jpg")
        shift_embed = discord.Embed(
            description=cortana.get_lyric("offline"), color=cortana.color
        )
        shift_embed = shift_embed.set_author(
            name=cortana.display_name, icon_url="attachment://offline.jpg"
        )
        await cortana.random_change()
        online_file = discord.File(cortana.avatar_path(), filename="online.jpg")
        online_embed = discord.Embed(
            description=cortana.get_lyric("online"), color=cortana.color
        )
        online_embed = online_embed.set_author(
            name=cortana.display_name, icon_url="attachment://online.jpg"
        )
        daily_embed = await daily_report(
            datetime.now(UTC).date() - timedelta(days=1)
        )
        await channel.send(
            embeds=[shift_embed, online_embed, daily_embed],
            files=[offline_file, online_file],
        )
        try:
            stats = await archiver.sync_all()
            # the sweep is only a safety net behind the real-time listeners, so
            # its success notification can be turned off; failures always warn
            if cfg["daily"].get("archive_notify", True):
                description = (
                    f"归档完成:新消息 {stats['new']},附件下载 {stats['downloaded']}"
                )
                if stats["failed"]:
                    description += f",下载失败 {stats['failed']}"
                await channel.send(embed=discord.Embed(description=description))
        except Exception as e:
            log.exception("daily archive failed")
            await warning(f"每日归档失败: {e}", channel=channel)
