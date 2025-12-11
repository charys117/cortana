import re
from datetime import datetime, timedelta
import discord
from src.core.init import cfg, bot


def identify(message):
    """
    Identifies the author of a message and returns the corresponding user IDs.

    Parameters:
        message (object): The message object containing author information.

    Returns:
        tuple: A tuple containing the user IDs of the identified author and the corresponding user.
               If the author is not identified, returns (None, None).
    """
    if message.author.id == cfg["member"]["charys117"]:
        return "charys117", "nouvee"
    elif message.author.id == cfg["member"]["nouvee"]:
        return "nouvee", "charys117"
    else:
        return None, None


def format_units(units, total, row_size=5):
    """
    Formats the given units in decimal system based on the total value and row size.

    Args:
        units (list): List of units to be formatted from smaller to bigger units.
        total (int): Total value to be divided into units.
        row_size (int, optional): Number of units per row. Defaults to 5.

    Returns:
        str: Formatted units.
    """
    if total <= 0:
        return None
    nums = []
    for i, unit in list(enumerate(units))[::-1]:
        nums.append((total // 10**i, unit))
        total %= 10**i
    result = ""
    for num, unit in nums:
        result += f"{unit * row_size}\n" * (num // row_size)
        result += f"{unit * (num % row_size)}\n" if num % row_size else ""
    return result


async def warning(content, channel=None, message=None):
    """
    Sends a warning message with the specified content to a channel or a user.

    Parameters:
    - content (str): The content of the warning message.
    - channel (discord.TextChannel, optional): The channel to send to.
    - message (discord.Message, optional): The message object to respond to.
    Raises:
    - ValueError: If neither channel nor message is provided.
    """
    embed = discord.Embed(title="**Warning**", description=content, color=0xFFC800)
    if message:
        try:
            await message.respond(embed=embed)
        except AttributeError:
            await message.channel.send(embed=embed)
    elif channel:
        await channel.send(embed=embed)
    else:
        raise ValueError("channel or message is required")


async def modify_board(giver, quantity):
    """
    Modifies the board by updating the amount associated with the giver.

    Args:
        giver (str): The name of the giver.
        quantity (int): The quantity to be added to the current amount.

    Returns:
        int: The updated amount after modification.
    """
    channel_name = cfg["board"][giver]["channel"]
    unit_1 = cfg["board"][giver]["unit_1"]
    unit_10 = cfg["board"][giver]["unit_10"]
    title = cfg["board"][giver]["title"]
    board_channel = bot.get_channel(cfg["channel"][channel_name])
    board = (await board_channel.history(limit=1).flatten())[0]
    amount = int(re.search(r"\n[-0-9]+", board.content).group().strip("\n"))
    amount += quantity
    units = format_units([unit_1, unit_10], amount)
    new_board = f"{title}:\n{units}{amount}"
    if board.author == bot.user:
        await board.edit(content=new_board)
    else:
        await board_channel.send(new_board)
    return amount


async def daily_report(date):
    """
    Generate a daily report of message counts.

    Returns:
        discord.Embed: Embed object containing the daily report.
    """
    channel = bot.get_channel(cfg["channel"]["chat"])
    daily_message_count = {}
    date_min = datetime.combine(date, datetime.min.time())
    async for message in channel.history(
        limit=None, after=date_min, before=date_min + timedelta(days=1)
    ):
        if message.author == bot.user:
            continue
        name = message.author.name
        if name not in daily_message_count:
            daily_message_count[name] = 0
        daily_message_count[name] += 1
    lines = ["今日消息数:"]
    for name, count in daily_message_count.items():
        lines.append(f"{name}: {count}")
    lines.append(f"共计{sum(daily_message_count.values())}条消息")
    return discord.Embed(title="**Daily Report**", description="\n".join(lines))
