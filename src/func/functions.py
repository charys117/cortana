"""
Contains functions that are used in the main bot file.
"""
import re
import asyncio
from datetime import datetime, timedelta
import discord
from src.core.init import cfg, bot, tz
from src.core.cortana import cortana
from src.core.backup import dbx_backup_by_date
from src.core.tools import warning, daily_report

class Func:
    @staticmethod
    async def archive_keyword(message):
        """
        Archives the message based on keyword matching.

        Args:
            message (discord.Message): The message to be archived.
        """
        for channel_name, keyword in cfg['archive_keyword'].items():
            if re.search('|'.join(keyword), message.content):
                channel = bot.get_channel(cfg['channel'][channel_name])
                if 'video' in message.attachments[0].content_type:
                    await channel.send(content=message.attachments[0].url)
                else:
                    embed = discord.Embed(description=message.content,
                                        color=message.author.color)
                    embed.set_author(name=message.author.display_name,
                                    icon_url=message.author.avatar.url)
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
        for k, i in cfg['archive_embed'].items():
            if any(url in message.content for url in i):
                times = 0
                while not message.embeds:
                    times += 1
                    await asyncio.sleep(1)
                    if times == 5:
                        await warning('自动embed失败', message=message)
                        return
                await message.guild.get_channel(cfg['channel'][k]).send(embed=message.embeds[0])
                await message.add_reaction(cortana.get_emoji())
                return

    @staticmethod
    async def daily():
        ch_name = cfg['daily']['channel']
        channel = bot.get_channel(cfg['channel'][ch_name])
        shift_embed = discord.Embed(description=cortana.get_lyric('offline'), color=cortana.color)
        shift_embed = shift_embed.set_author(name=cortana.member.display_name, icon_url=cortana.member.avatar.url)
        await cortana.random_change()
        online_embed = discord.Embed(description=cortana.get_lyric('online'), color=cortana.color)
        online_embed = online_embed.set_author(name=cortana.member.display_name, icon_url=cortana.member.avatar.url)
        daily_embed = await daily_report(datetime.now(tz).date() - timedelta(days=1))
        await channel.send(embeds=[shift_embed, online_embed, daily_embed])
        today = datetime.now(tz).date()
        try:
            await dbx_backup_by_date(channel=channel, start_date=today - timedelta(days=1), end_date=today)
        except Exception as e:
            await warning(f'每日备份失败: {e}', channel=channel)
