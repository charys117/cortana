import os
import logging
from datetime import timezone, timedelta
import httpx
import discord
import yaml

import coloredlogs

# load cfg
with open('data/config.yml', 'r', encoding='utf-8') as f:
    cfg = yaml.safe_load(f)
if os.path.exists('.env'):
    import dotenv
    dotenv.load_dotenv()
# set up httpx client and discord bot
httpx_client = httpx.AsyncClient(proxy=os.getenv('PROXY'))
bot = discord.Bot(intents=discord.Intents.all(), proxy=os.getenv('PROXY'))
# set timezone
tz = timezone(timedelta(hours=cfg['timezone']))

def update_cfg():
    guild = bot.get_guild(cfg['guild_id'])
    cfg['channel'] = {ch.name: ch.id for ch in guild.text_channels}
    cfg['member'] = {m.name: m.id for m in guild.members}

class Log:
    coloredlogs.install(fmt='[%(levelname)s][%(name)s] %(message)s', level='INFO')

    @staticmethod
    def get(name):
        return logging.getLogger(name)

    @staticmethod
    def set_level(level):
        coloredlogs.install(fmt='[%(levelname)s][%(name)s] %(message)s', level=level)
