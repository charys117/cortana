import asyncio
import json
import logging
import os

import asyncpg
import coloredlogs
import discord
import httpx

if os.path.exists(".env"):
    import dotenv

    dotenv.load_dotenv()

# yaml config: seeds the database on first boot; when DATABASE_URL is unset
# (local dev, tests) it is the sole config store instead
CONFIG_PATH = os.environ.get("CORTANA_CONFIG", "./config.yml")


def normalize_cfg(cfg):
    """
    Upgrade legacy config schemas in place so old configs keep working.

    - board.*.unit_1/unit_10 -> board.*.units (list, index i == 10**i place)
    - missing top-level `pair` -> derived from board keys
    - legacy markdown `backup` section -> postgres `archive` section
    - legacy `timezone` -> dropped; everything runs on UTC now and the web UI
      renders times in the browser's timezone
    """
    cfg.pop("timezone", None)
    if "daily" in cfg:
        cfg["daily"].setdefault("time", "00:00")
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


def _load_yaml_cfg():
    import yaml

    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return normalize_cfg(yaml.safe_load(f))


async def _bootstrap_cfg():
    """
    Load the config from Postgres; on first boot, seed it from the yaml file
    at CONFIG_PATH. Without DATABASE_URL, fall back to yaml-only mode.
    """
    if not os.environ.get("DATABASE_URL"):
        logging.getLogger("init").warning(
            "DATABASE_URL not set - config runs in yaml-only mode, archive disabled"
        )
        return _load_yaml_cfg()
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
        seeded = _load_yaml_cfg()
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

# keys injected at runtime by update_cfg(); never persisted
RUNTIME_KEYS = ("channel", "member")

# callables invoked after save_cfg hot-swaps the config (e.g. rescheduling the
# daily task); registered by run.py
cfg_change_hooks = []


def update_cfg():
    guild = bot.get_guild(cfg["guild_id"])
    cfg["channel"] = {ch.name: ch.id for ch in guild.text_channels}
    cfg["member"] = {m.name: m.id for m in guild.members}


async def save_cfg(new_cfg):
    """
    Persist a new config (to the database, or to the yaml file in yaml-only
    mode) and hot-apply it to the in-memory cfg. Runtime keys (channel/member)
    are preserved across the swap.
    """
    new_cfg = normalize_cfg({k: v for k, v in new_cfg.items() if k not in RUNTIME_KEYS})
    if os.environ.get("DATABASE_URL"):
        from sqlalchemy import func
        from sqlalchemy.dialects.postgresql import insert as pg_insert

        from src.core.db import get_session
        from src.core.models import BotConfig

        async with get_session() as session:
            stmt = pg_insert(BotConfig).values(id=1, data=new_cfg)
            stmt = stmt.on_conflict_do_update(
                index_elements=["id"],
                set_={"data": stmt.excluded.data, "updated_at": func.now()},
            )
            await session.execute(stmt)
            await session.commit()
    else:
        import tempfile

        import yaml

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
    for hook in cfg_change_hooks:
        try:
            hook()
        except Exception:
            logging.getLogger("init").exception("cfg change hook failed")


class Log:
    coloredlogs.install(fmt="[%(levelname)s][%(name)s] %(message)s", level="INFO")

    @staticmethod
    def get(name):
        return logging.getLogger(name)

    @staticmethod
    def set_level(level):
        coloredlogs.install(fmt="[%(levelname)s][%(name)s] %(message)s", level=level)
