"""
Embedded web UI for editing the bot config (stored in PostgreSQL) with live
guild data (emojis, channels, members).

Runs on the bot's event loop. Protect it with CORTANA_WEB_TOKEN when the port is
reachable from outside the cluster.
"""

import os
import secrets

from aiohttp import web

from src.core.init import (
    RUNTIME_KEYS,
    Log,
    bot,
    cfg,
    normalize_cfg,
    save_cfg,
    update_cfg,
)

log = Log.get("web")

STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
AVATAR_DIR = os.path.abspath("./src/assets/avatars")

# top-level keys the editor is allowed to persist, with their expected types
CONFIG_SCHEMA = {
    "guild": str,
    "guild_id": int,
    "timezone": (int, float),
    "pair": list,
    "bark": dict,
    "emoji": dict,
    "cortana": dict,
    "awake_notify": dict,
    "archive_keyword": dict,
    "board": dict,
    "award": dict,
    "archive_embed": dict,
    "archive": dict,
    "daily": dict,
}
REQUIRED_KEYS = ("guild_id", "timezone", "emoji", "cortana", "board")


def _validate(config):
    if not isinstance(config, dict):
        return "config必须是对象"
    for key in REQUIRED_KEYS:
        if key not in config:
            return f"缺少必需字段: {key}"
    for key, value in config.items():
        expected = CONFIG_SCHEMA.get(key)
        if expected is None:
            return f"未知字段: {key}"
        if not isinstance(value, expected):
            return f"字段类型错误: {key}"
    for name, board in config["board"].items():
        for field in ("channel", "units", "title", "response"):
            if field not in board:
                return f"board.{name} 缺少 {field}"
        if not board["units"]:
            return f"board.{name}.units 至少需要一个单位"
    for name, persona in config["cortana"].items():
        for field in ("display_name", "color", "online", "offline"):
            if field not in persona:
                return f"cortana.{name} 缺少 {field}"
    return None


@web.middleware
async def auth_middleware(request, handler):
    token = os.environ.get("CORTANA_WEB_TOKEN")
    if token and request.path.startswith("/api/"):
        supplied = request.headers.get("Authorization", "").removeprefix("Bearer ")
        if not secrets.compare_digest(supplied, token):
            return web.json_response({"error": "unauthorized"}, status=401)
    return await handler(request)


async def index(_request):
    return web.FileResponse(os.path.join(STATIC_DIR, "index.html"))


async def get_config(_request):
    config = {k: v for k, v in cfg.items() if k not in RUNTIME_KEYS}
    # guild_id exceeds JS Number.MAX_SAFE_INTEGER; ship it as a string
    config["guild_id"] = str(config["guild_id"])
    return web.json_response({"config": config, "source": "postgresql"})


async def put_config(request):
    try:
        config = await request.json()
    except ValueError:
        return web.json_response({"error": "无效的JSON"}, status=400)
    config = normalize_cfg(config)
    if isinstance(config.get("guild_id"), str):
        if not config["guild_id"].isdigit():
            return web.json_response({"error": "guild_id必须是数字"}, status=400)
        config["guild_id"] = int(config["guild_id"])
    error = _validate(config)
    if error:
        return web.json_response({"error": error}, status=400)
    await save_cfg(config)
    if bot.is_ready():
        update_cfg()
    log.info("config updated via web UI")
    return web.json_response({"ok": True})


async def get_guild(_request):
    guild = bot.get_guild(cfg["guild_id"])
    if guild is None:
        return web.json_response({"error": "bot尚未连接到guild"}, status=503)
    return web.json_response(
        {
            "guild": {
                "name": guild.name,
                "id": str(guild.id),
                "icon": str(guild.icon.url) if guild.icon else None,
            },
            "emojis": [
                {
                    "name": e.name,
                    "id": str(e.id),
                    "animated": e.animated,
                    "url": str(e.url),
                    "code": str(e),
                }
                for e in guild.emojis
            ],
            "channels": [
                {"name": c.name, "id": str(c.id)}
                for c in sorted(guild.text_channels, key=lambda c: c.position)
            ],
            "members": [
                {
                    "name": m.name,
                    "display_name": m.display_name,
                    "id": str(m.id),
                    "avatar": str(m.display_avatar.url),
                    "bot": m.bot,
                }
                for m in guild.members
            ],
        }
    )


async def get_avatar(request):
    name = os.path.basename(request.match_info["name"])
    path = os.path.join(AVATAR_DIR, f"{name}.jpg")
    if not os.path.exists(path):
        raise web.HTTPNotFound()
    return web.FileResponse(path)


def build_app():
    app = web.Application(middlewares=[auth_middleware])
    app.router.add_get("/", index)
    app.router.add_get("/api/config", get_config)
    app.router.add_put("/api/config", put_config)
    app.router.add_get("/api/guild", get_guild)
    app.router.add_get("/avatars/{name}", get_avatar)
    return app


_started = False


async def start_web():
    """Start the config web UI once; safe to call from every on_ready."""
    global _started
    if _started or os.environ.get("CORTANA_WEB_ENABLED", "1") == "0":
        return
    _started = True
    host = os.environ.get("CORTANA_WEB_HOST", "0.0.0.0")
    port = int(os.environ.get("CORTANA_WEB_PORT", "8080"))
    runner = web.AppRunner(build_app())
    await runner.setup()
    await web.TCPSite(runner, host, port).start()
    if not os.environ.get("CORTANA_WEB_TOKEN"):
        log.warning("CORTANA_WEB_TOKEN未设置, 配置页面无鉴权, 请勿暴露到公网")
    log.info(f"Config web UI listening on http://{host}:{port}")
