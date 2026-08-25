"""
This module contains functions that handle various commands in a Discord bot.
"""

import random
import re
from datetime import datetime, timedelta

import discord
from discord.ui import Button, Select, View

from src.core.backup import backup_by_date
from src.core.cortana import cortana
from src.core.init import bot, cfg, httpx_client, tz
from src.core.tools import format_units, identify, modify_board, warning


class Cmd:
    @staticmethod
    async def awake(message):
        """
        Sends a notification to the receiver indicating that the user is awake.

        Args:
            message: The message with command
        """
        _, receiver = identify(message)
        post = cfg["bark"]["post"].copy()
        post["body"] = cfg["awake_notify"][receiver]
        await httpx_client.post(url=cfg["bark"][receiver], data=post)
        await message.respond(
            embed=discord.Embed(description=f"已通知{receiver}您醒了")
        )

    @staticmethod
    async def bonus(message):
        """
        This function handles the process of creating a bonus reward in a Discord channel.

        Parameters:
        - message: The message object that triggered the command.
        """
        bonus_ch = bot.get_channel(cfg["channel"]["bonus"])
        attr = {"number": 1, "type": "", "content": "", "reward": 0, "time": ""}
        async for m in bonus_ch.history(limit=1):
            attr["number"] = int(re.search(r"#(\d+)", m.embeds[0].title).group(1)) + 1

        type1 = Button(label="普通悬赏", style=discord.ButtonStyle.green)
        type2 = Button(label="限时悬赏", style=discord.ButtonStyle.primary)
        type3 = Button(label="紧急悬赏", style=discord.ButtonStyle.red)

        async def type1_callback(interaction):
            attr["type"] = "普通悬赏"
            await rest_part(interaction)

        async def type2_callback(interaction):
            attr["type"] = "限时悬赏"
            await rest_part(interaction)

        async def type3_callback(interaction):
            attr["type"] = "紧急悬赏"
            await rest_part(interaction)

        async def rest_part(interaction):
            await interaction.response.defer()
            await interaction.message.edit(content="请输入内容", view=None)

            def check_func(m):
                return m.author != bot.user and m.channel == message.channel

            content = await bot.wait_for("message", check=check_func)
            if content:
                if content.content == "cancel":
                    await interaction.message.edit(content="已取消")
                    return
                attr["content"] = content.content
                await content.delete()
                await interaction.message.edit(content="请输入奖励")
                reward = await bot.wait_for("message", check=check_func)
                try:
                    attr["reward"] = int(reward.content)
                except ValueError:
                    await message.channel.send("奖励必须为整数")
                    return
            else:
                return
            if reward and attr["type"] in ["限时悬赏", "紧急悬赏"]:
                await reward.delete()
                await interaction.message.edit(content="请输入时间")
                time = await bot.wait_for("message", check=check_func)
                attr["time"] = time.content
                await time.delete()
            else:
                await reward.delete()
            sender, _ = identify(message)
            # build embed
            reward_text = format_units(
                cfg["board"][sender]["units"][:1], attr["reward"]
            )
            title_text = f"**悬赏#{attr['number']}**"
            description = f"类型: {attr['type']}\n内容: {attr['content']}\n"
            description += f"有效时间: {attr['time']}\n" if attr["time"] else ""
            description += f"奖励:\n{reward_text}状态: 待完成"
            embed = discord.Embed(
                title=title_text, description=description, color=message.author.color
            )
            embed.set_author(
                name=message.author.display_name, icon_url=message.author.avatar.url
            )
            bonus_message = await bonus_ch.send(embed=embed)
            # pin the bonus
            await bonus_message.pin()
            # delete the notification of pinning
            async for m in bonus_ch.history(limit=1):
                await m.delete()
            # modify embed for response
            embed.title = "**Bonus Released**"
            embed.description = f"{title_text}\n{description}"
            await interaction.message.edit(content="", embed=embed)
            return

        view = View()
        view.add_item(type1)
        view.add_item(type2)
        view.add_item(type3)
        type1.callback = type1_callback
        type2.callback = type2_callback
        type3.callback = type3_callback
        await message.respond("选择悬赏类型", view=view)

    @staticmethod
    async def chuo(message):
        """
        Sends a chuochuo to the receiver.

        Args:
            message: The message with command
        """
        _, receiver = identify(message)
        post = cfg["bark"]["post"].copy()
        post["body"] = "⚠️检测到戳戳⚠️检测到戳戳⚠️"
        await httpx_client.post(url=cfg["bark"][receiver], data=post)
        await warning(f"⚠️戳戳警报已抵达{receiver}⚠️", message=message)

    @staticmethod
    async def record(message, description, quantity):
        """
        Records a change in credits with a description and quantity, modifies the board, and sends a response.

        Args:
            message (discord.Message): The message object.
            description (str): The description of the record.
            quantity (int): The quantity to be recorded.
        """
        # modify the board
        sender, _ = identify(message)
        amount = await modify_board(sender, quantity)
        response = cfg["board"][sender]["response"]
        record_channel = bot.get_channel(cfg["channel"]["record"])
        # response
        embed = discord.Embed(
            description=f"{description}{quantity:+d}\n{response}: {amount}",
            color=message.author.color,
        )
        embed.set_author(
            name=message.author.display_name, icon_url=message.author.avatar.url
        )
        await record_channel.send(embed=embed)
        await message.respond(embed=embed)

    @staticmethod
    async def night(message):
        """
        Forwards messages from the 'night' channel to the current channel.

        Args:
            message (discord.Message): The message triggering the forward.
        """
        night_ch = bot.get_channel(cfg["channel"]["night"])
        await message.respond(embed=discord.Embed(description="开始转发"))
        start = None
        async for m in night_ch.history(limit=None):
            if (
                m.author == bot.user
                and m.embeds
                and str(m.embeds[0].description).startswith("已转发")
            ):
                start = m
                break
        bundle = []
        async for m in night_ch.history(after=start, oldest_first=True):
            if m.author == bot.user:
                bundle += m.embeds
                if len(bundle) >= 8:
                    await message.channel.send(embeds=bundle)
                    bundle = []
            else:
                if m.content:
                    embed = discord.Embed(
                        description=m.content,
                        color=m.author.color,
                        timestamp=m.created_at,
                    )
                    embed.set_author(
                        name=m.author.display_name, icon_url=m.author.avatar.url
                    )
                    bundle.append(embed)
                for att in m.attachments:
                    if att.content_type.startswith("image"):
                        embed = discord.Embed(
                            color=m.author.color, timestamp=m.created_at
                        )
                        embed.set_author(
                            name=m.author.display_name, icon_url=m.author.avatar.url
                        )
                        embed.set_image(url=att.url)
                        bundle.append(embed)
                    elif att.content_type.startswith("video"):
                        if bundle:
                            await message.channel.send(embeds=bundle)
                            bundle = []
                        await message.channel.send(att.url)
                    if len(bundle) >= 8:
                        await message.channel.send(embeds=bundle)
                        bundle = []
                if len(bundle) >= 8:
                    await message.channel.send(embeds=bundle)
                    bundle = []
        if bundle:
            await message.channel.send(embeds=bundle)
        await night_ch.send(
            embed=discord.Embed(description=f"已转发到<#{message.channel.id}>")
        )
        await message.channel.send(embed=discord.Embed(description="转发结束"))

    @staticmethod
    async def done(message, index):
        """
        Marks a reward as completed and updates the corresponding embed.

        Args:
            message (discord.Message): The message triggering the command.
            index (int): The index of the reward to mark as completed.
        """
        await message.defer()
        sender, receiver = identify(message)
        giver = receiver
        bonus_ch = bot.get_channel(cfg["channel"]["bonus"])
        succuess_emoji = ["🎉", "🎊", "🥳", "🍾", "💐"]
        succuess_emoji = random.choice(succuess_emoji)
        async for m in bonus_ch.history(limit=None):
            if not m.embeds:
                await warning("该悬赏不支持", message=message)
                return
            embed = m.embeds[0]
            number = int(re.search(r"#(\d+)", embed.title).group(1))
            content = embed.description
            if number == index:
                if content.startswith("~"):
                    await warning("该悬赏之前已完成, 请重新确认", message=message)
                    return
                await m.unpin()
                reward_emoji = cfg["board"][giver]["units"][0]
                reward = len(re.findall(re.escape(reward_emoji), content))
                new_content = (
                    f"~~{content.split('状态')[0]}~~状态: 已完成{succuess_emoji}"
                )
                # modify embed
                embed.description = new_content
                await m.edit(embed=embed)
                amount = await modify_board(giver, reward)
                response = cfg["board"][giver]["response"]
                congrat_embed = discord.Embed(
                    title="**CONGRATULATIONS!!**",
                    description=f"悬赏{index}已完成{succuess_emoji}\n恭喜<@{cfg['member'][sender]}>获得{reward_emoji}x{reward}\n{response}: {amount}",
                )
                await message.respond(embed=congrat_embed)
                # response
                await bot.get_channel(cfg["channel"]["record"]).send(embed=embed)
                return

    @staticmethod
    async def shift(message):
        """
        Function to handle character change command.
        """
        options = [
            discord.SelectOption(
                label=cfg["cortana"][name]["display_name"], emoji=cfg["emoji"][name]
            )
            for name in cfg["cortana"]
        ]
        select = Select(options=options, placeholder="选择你的BOT")

        async def callback(interaction):
            new_disname = select.values[0]
            for name in cfg["cortana"]:
                if new_disname == cfg["cortana"][name]["display_name"]:
                    new_name = name
                    break
            await cortana.shift(new_name)
            await interaction.response.defer()
            embed = discord.Embed(
                description=cortana.get_lyric("online"), color=cortana.color
            )
            embed.set_author(
                name=cortana.member.display_name, icon_url=cortana.member.avatar.url
            )
            await interaction.channel.send(embed=embed)

        view = View()
        view.add_item(select)
        select.callback = callback
        embed = discord.Embed(
            description=cortana.get_lyric("offline"), color=cortana.color
        )
        embed.set_author(
            name=cortana.member.display_name, icon_url=cortana.member.avatar.url
        )
        await message.respond(embed=embed, view=view)

    @staticmethod
    async def roll(message, num):
        """
        Rolls a dice and returns the result.

        Args:
            message (discord.Message): The message triggering the command.
            num (int, optional): The number of sides of the dice. Defaults to 6.
        """
        await message.respond(
            embed=discord.Embed(
                description=f"1-{num}之间随机数: {random.randint(1, num)}"
            )
        )

    @staticmethod
    async def award(message, field, description):
        """
        Award a badge to a user.

        Args:
            message (discord.Message): The message triggering the award command.
            field (str): The field to be displayed in the badge.
            description (str): The description of the badge.
        """

        # interactions to define badge
        badge = {}
        badge_channel = bot.get_channel(cfg["channel"]["badge"])
        sender, receiver = identify(message)
        badge["owner"] = bot.get_user(cfg["member"][receiver])
        func_cfg = cfg["award"][sender]
        titles = list(func_cfg)
        title1 = Button(label=titles[0], style=discord.ButtonStyle.green)
        title2 = Button(label=titles[1], style=discord.ButtonStyle.secondary)
        title3 = Button(label=titles[2], style=discord.ButtonStyle.primary)

        async def title1_callback(interaction):
            title = titles[0]
            badge["title"] = title
            badge["emoji"] = cfg["emoji"][func_cfg[title][0]]
            badge["color"] = func_cfg[title][1]
            await rest_part(interaction)

        async def title2_callback(interaction):
            title = titles[1]
            badge["title"] = title
            badge["emoji"] = cfg["emoji"][func_cfg[title][0]]
            badge["color"] = func_cfg[title][1]
            await rest_part(interaction)

        async def title3_callback(interaction):
            title = titles[2]
            badge["title"] = title
            badge["emoji"] = cfg["emoji"][func_cfg[title][0]]
            badge["color"] = func_cfg[title][1]
            await rest_part(interaction)

        view = View()
        view.add_item(title1)
        view.add_item(title2)
        view.add_item(title3)
        title1.callback = title1_callback
        title2.callback = title2_callback
        title3.callback = title3_callback
        await message.respond("请选择称号", view=view)

        async def rest_part(interaction):
            await interaction.response.defer()
            # build embed
            embed = discord.Embed(
                title=f"{badge['emoji']} **{field}{badge['title']}**",
                color=badge["color"],
            )
            embed.set_footer(text=description, icon_url=badge["owner"].avatar.url)
            embed.timestamp = datetime.now(tz)
            # reply
            await interaction.channel.send(content="已授予", embed=embed)
            await interaction.message.edit(content="已完成", view=None)
            # find the message
            aim_message = None
            async for i in badge_channel.history(limit=None):
                if str(badge["owner"].id) in i.embeds[0].footer.icon_url:
                    aim_message = i
                    break
            if not aim_message:
                await badge_channel.send(embed=embed)
            else:
                embeds = aim_message.embeds
                embeds.append(embed)
                await aim_message.edit(embeds=embeds)

    @staticmethod
    async def backup_daily(message):
        """
        Manually backup the Dropbox folder for the previous day.

        Args:
            message (discord.Message): The message triggering the command.
        """
        today = datetime.now(tz).date()
        await backup_by_date(
            message=message, start_date=today - timedelta(days=1), end_date=today
        )

    @staticmethod
    async def backup_all(message, start_date_str, end_date_str):
        """
        Manually backup the Dropbox folder for the specified period.

        Args:
            message (discord.Message): The message triggering the command.
            start_date_str (str): The start date of the period.
            end_date_str (str): The end date of the period.
        """
        start_date = (
            datetime.strptime(start_date_str, "%y%m%d").date()
            if start_date_str
            else None
        )
        end_date = (
            datetime.strptime(end_date_str, "%y%m%d").date() if end_date_str else None
        )
        await backup_by_date(message=message, start_date=start_date, end_date=end_date)
