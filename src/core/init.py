import asyncio
import json
import logging
import os
from datetime import timedelta, timezone

import asyncpg
import coloredlogs
import discord
import httpx

if os.path.exists(".env"):
    import dotenv

    dotenv.load_dotenv()

# legacy yaml config; only used to seed the database on first boot
CONFIG_PATH = os.environ.get("CORTANA_CONFIG", "./config.yml")


def normalize_cfg(cfg):
    """
    Upgrade legacy config schemas in place so old configs keep working.

    - board.*.unit_1/unit_10 -> board.*.units (list, index i == 10**i place)
    - missing top-level `pair` -> derived from board keys
    - legacy markdown `backup` section -> postgres `archive` section
    """
    for board in cfg.get("board", {}).values():
        if "units" not in board:
            units = [board.pop("unit_1", None), board.pop("unit_10", None)]
            board["units"] = [u for u in units if u]
    if "pair" not in cfg and cfg.get("board"):
        cfg["pair"] = list(cfg["board"])
    if "archive" not in cfg:
        backup = cfg.pop("backup", {})
        cfg["archive"] = {
            "media_root": os.path.join(backup.get("local_folder", "./archive"), "media")
        }
    else:
        cfg.pop("backup", None)
    return cfg


async def _bootstrap_cfg():
    """
    Load the config from Postgres; on first boot, seed it from the legacy
    yaml file at CONFIG_PATH.
    """
    conn = await asyncpg.connect(os.environ["DATABASE_URL"])
    try:
        try:
            raw = await conn.fetchval("SELECT data FROM bot_config WHERE id = 1")
        except asyncpg.UndefinedTableError:
            raise RuntimeError(
                "bot_config table missing; run `alembic upgrade head` first"
            ) from None
        if raw is not None:
            return normalize_cfg(json.loads(raw))
        if not os.path.exists(CONFIG_PATH):
            raise RuntimeError(
                f"no config in database and no seed file at {CONFIG_PATH}"
            )
        import yaml

        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            seeded = normalize_cfg(yaml.safe_load(f))
        await conn.execute(
            "INSERT INTO bot_config (id, data) VALUES (1, $1)", json.dumps(seeded)
        )
        return seeded
    finally:
        await conn.close()


# load cfg on the event loop the bot will also run on (asyncio.run would tear
# the loop down again and break discord.Bot's constructor)
_loop = asyncio.new_event_loop()
asyncio.set_event_loop(_loop)
cfg = _loop.run_until_complete(_bootstrap_cfg())
# set up httpx client and discord bot
httpx_client = httpx.AsyncClient(proxy=os.getenv("PROXY"))
bot = discord.Bot(intents=discord.Intents.all(), proxy=os.getenv("PROXY"))
# set timezone
tz = timezone(timedelta(hours=cfg["timezone"]))

# keys injected at runtime by update_cfg(); never persisted
RUNTIME_KEYS = ("channel", "member")


def update_cfg():
    guild = bot.get_guild(cfg["guild_id"])
    cfg["channel"] = {ch.name: ch.id for ch in guild.text_channels}
    cfg["member"] = {m.name: m.id for m in guild.members}


async def save_cfg(new_cfg):
    """
    Persist a new config to the database and hot-apply it to the in-memory cfg.
    Runtime keys (channel/member) are preserved across the swap.
    """
    from sqlalchemy import func
    from sqlalchemy.dialects.postgresql import insert as pg_insert

    from src.core.db import get_session
    from src.core.models import BotConfig

    new_cfg = normalize_cfg({k: v for k, v in new_cfg.items() if k not in RUNTIME_KEYS})
    async with get_session() as session:
        stmt = pg_insert(BotConfig).values(id=1, data=new_cfg)
        stmt = stmt.on_conflict_do_update(
            index_elements=["id"],
            set_={"data": stmt.excluded.data, "updated_at": func.now()},
        )
        await session.execute(stmt)
        await session.commit()
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
