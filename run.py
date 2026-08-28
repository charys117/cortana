import os
from datetime import UTC
from datetime import time as datetime_time

from discord.ext import tasks

import src.core.listeners  # noqa: F401  registers real-time archive listeners
from src.core.cortana import cortana
from src.core.init import Log, bot, cfg, cfg_change_hooks, update_cfg
from src.core.tools import warning
from src.func.commands import Cmd
from src.func.functions import Func
from src.web.server import start_web

log = Log.get("main")


def _daily_time():
    """The daily task's fire time from cfg, HH:MM in UTC."""
    hour, minute = map(int, cfg["daily"].get("time", "00:00").split(":"))
    return datetime_time(hour, minute, tzinfo=UTC)


@bot.event
async def on_ready():
    log.info(f"We have logged in as {bot.user}")
    update_cfg()
    cortana.init()
    await start_web()


@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    if message.channel.name in ["chat", "night", "test"]:
        if message.attachments and message.content:
            await Func.archive_keyword(message)
        elif "https://" in message.content or "http://" in message.content:
            await Func.archive_embed(message)


@bot.slash_command(description="戳戳", guild_ids=[cfg["guild_id"]])
async def chuo(ctx):
    await Cmd.chuo(ctx)


@bot.slash_command(description="醒来提醒", guild_ids=[cfg["guild_id"]])
async def awake(ctx):
    await Cmd.awake(ctx)


@bot.slash_command(description="发起悬赏", guild_ids=[cfg["guild_id"]])
async def bonus(ctx):
    await Cmd.bonus(ctx)


@bot.slash_command(description="完成悬赏", guild_ids=[cfg["guild_id"]])
async def done(ctx, index: int):
    await Cmd.done(ctx, index)


@bot.slash_command(description="切换形象", guild_ids=[cfg["guild_id"]])
async def shift(ctx):
    await Cmd.shift(ctx)


@bot.slash_command(description="积分变更", guild_ids=[cfg["guild_id"]])
async def record(ctx, description: str, quantity: int):
    await Cmd.record(ctx, description, quantity)


@bot.slash_command(description="转发#night消息", guild_ids=[cfg["guild_id"]])
async def night(ctx):
    await Cmd.night(ctx)


@bot.slash_command(description="摇骰子", guild_ids=[cfg["guild_id"]])
async def roll(ctx, num: int = 6):
    await Cmd.roll(ctx, num)


@bot.command(description="授勋", guild_ids=[cfg["guild_id"]])
async def award(ctx, title: str, description: str):
    await Cmd.award(ctx, title, description)


@bot.command(description="手动归档同步", guild_ids=[cfg["guild_id"]])
async def sync(ctx, full: bool = False):
    await Cmd.sync(ctx, full)


@tasks.loop(time=_daily_time())
async def daily():
    try:
        await Func.daily()
    except Exception as e:
        log.exception("Daily failed")
        await warning(
            f"每日任务失败: {e}",
            channel=bot.get_channel(cfg["channel"][cfg["daily"]["channel"]]),
        )


daily.start()

_daily_scheduled = _daily_time()


def _reschedule_daily():
    """Hot-apply a changed daily.time without restarting the bot."""
    global _daily_scheduled
    new_time = _daily_time()
    if new_time == _daily_scheduled:
        return
    _daily_scheduled = new_time
    daily.change_interval(time=new_time)
    daily.restart()
    log.info(f"daily task rescheduled to {new_time.strftime('%H:%M')} UTC")


cfg_change_hooks.append(_reschedule_daily)

bot.run(os.environ["DISCORD_BOT_TOKEN"])
