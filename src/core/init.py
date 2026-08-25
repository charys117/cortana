import logging
import os
import tempfile
from datetime import timedelta, timezone

import coloredlogs
import discord
import httpx
import yaml

CONFIG_PATH = os.environ.get("CORTANA_CONFIG", "./config.yml")


def normalize_cfg(cfg):
    """
    Upgrade legacy config schemas in place so old config files keep working.

    - board.*.unit_1/unit_10 -> board.*.units (list, index i == 10**i place)
    - missing top-level `pair` -> derived from board keys
    """
    for board in cfg.get("board", {}).values():
        if "units" not in board:
            units = [board.pop("unit_1", None), board.pop("unit_10", None)]
            board["units"] = [u for u in units if u]
    if "pair" not in cfg and cfg.get("board"):
        cfg["pair"] = list(cfg["board"])
    return cfg


# load cfg
with open(CONFIG_PATH, "r", encoding="utf-8") as f:
    cfg = normalize_cfg(yaml.safe_load(f))
if os.path.exists(".env"):
    import dotenv

    dotenv.load_dotenv()
# set up httpx client and discord bot
httpx_client = httpx.AsyncClient(proxy=os.getenv("PROXY"))
bot = discord.Bot(intents=discord.Intents.all(), proxy=os.getenv("PROXY"))
# set timezone
tz = timezone(timedelta(hours=cfg["timezone"]))

# keys injected at runtime by update_cfg(); never persisted to config.yml
RUNTIME_KEYS = ("channel", "member")


def update_cfg():
    guild = bot.get_guild(cfg["guild_id"])
    cfg["channel"] = {ch.name: ch.id for ch in guild.text_channels}
    cfg["member"] = {m.name: m.id for m in guild.members}


def save_cfg(new_cfg):
    """
    Persist a new config atomically and hot-apply it to the in-memory cfg.
    Runtime keys (channel/member) are preserved across the swap.
    """
    new_cfg = normalize_cfg({k: v for k, v in new_cfg.items() if k not in RUNTIME_KEYS})
    text = yaml.safe_dump(new_cfg, allow_unicode=True, sort_keys=False)
    directory = os.path.dirname(os.path.abspath(CONFIG_PATH)) or "."
    fd, tmp_path = tempfile.mkstemp(dir=directory, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
        os.replace(tmp_path, CONFIG_PATH)
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
    runtime = {k: cfg[k] for k in RUNTIME_KEYS if k in cfg}
    cfg.clear()
    cfg.update(new_cfg)
    cfg.update(runtime)


class Log:
    coloredlogs.install(fmt="[%(levelname)s][%(name)s] %(message)s", level="INFO")

    @staticmethod
    def get(name):
        return logging.getLogger(name)

    @staticmethod
    def set_level(level):
        coloredlogs.install(fmt="[%(levelname)s][%(name)s] %(message)s", level=level)
