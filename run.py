import os
from datetime import time as datetime_time
from discord.ext import tasks
from src.core.init import bot, cfg, update_cfg, Log, tz
from src.core.cortana import cortana
from src.core.tools import warning
from src.func.commands import Cmd
from src.func.functions import Func

log = Log.get("main")


@bot.event
async def on_ready():
    log.info(f"We have logged in as {bot.user}")
    update_cfg()
    cortana.init()


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


@bot.command(description="手动每日Dropbox备份", guild_ids=[cfg["guild_id"]])
async def backup_daily(ctx):
    await Cmd.backup_daily(ctx)


@bot.command(description="手动全部Dropbox备份", guild_ids=[cfg["guild_id"]])
async def backup_all(ctx, start_date_str: str = None, end_date_str: str = None):
    await Cmd.backup_all(ctx, start_date_str, end_date_str)


@tasks.loop(time=datetime_time(0, 0, tzinfo=tz))
async def daily():
    try:
        await Func.daily()
    except Exception as e:
        log.error(f"Daily failed: {e}")
        await warning(
            f"每日备份失败: {e}",
            channel=bot.get_channel(cfg["channel"][cfg["daily"]["channel"]]),
        )


daily.start()

bot.run(os.environ["CORTANA_TOKEN"])
