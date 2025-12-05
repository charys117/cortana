"""
contains functions for backing up messages
"""
import os
from os.path import join as pj
from datetime import timedelta, datetime
import discord
from src.core.init import cfg, httpx_client, bot, tz, Log


class Backup:
    """
    Local backup utility class.

    This class provides methods for backing up messages from a Discord channel to the local filesystem.
    """
    def __init__(self):
        """
        Initialize the Backup object.
        """
        self.log = Log.get('backup')
        self.backup_root = cfg['backup']['local_folder']
        os.makedirs(self.backup_root, exist_ok=True)
        self.exists = {}

    def _resolve_path(self, *parts):
        """
        Construct an absolute path inside the backup root.
        """
        cleaned_parts = []
        for part in parts:
            if part is None:
                continue
            cleaned = str(part).strip('/')
            if cleaned:
                cleaned_parts.append(cleaned)
        return pj(self.backup_root, *cleaned_parts)

    async def add_attachment(self, url, attname, md_dir, att_dir):
        """
        Add an attachment to the backup.

        Args:
            url (str): The URL of the attachment.
            attname (str): The name of the attachment.
            md_dir (str): The directory where the Markdown files are stored.
            att_dir (str): The directory where the attachments are stored.

        Returns:
            str: The Markdown link to the attachment.
        """
        abs_att_dir = self._resolve_path(md_dir, att_dir)
        if abs_att_dir not in self.exists:
            os.makedirs(abs_att_dir, exist_ok=True)
            self.exists[abs_att_dir] = set(os.listdir(abs_att_dir))
        suffix = url.split('.')[-1]
        suffix = suffix.split('?')[0]
        filename = f'{attname}.{suffix}'
        relpath = pj(att_dir, filename)
        if filename in self.exists[abs_att_dir]:
            return f'[{attname}]({relpath})'
        abspath = pj(abs_att_dir, filename)
        chunk_size = cfg['backup']['chunk_size']
        async with httpx_client.stream('GET', url) as r:
            with open(abspath, 'wb') as f:
                async for chunk in r.aiter_bytes(chunk_size):
                    f.write(chunk)
        self.exists[abs_att_dir].add(filename)
        return f'[{attname}]({relpath})'

    async def get_earliest_date(self, channel_name):
        """
        Get the earliest date of messages in a Discord channel.

        Args:
            channel_name (str): The name of the Discord channel.

        Returns:
            datetime.date: The earliest date of messages in the channel.
        """
        channel = bot.get_channel(cfg['channel'][channel_name])
        first_message = (await channel.history(limit=1, oldest_first=True).flatten())[0]
        return first_message.created_at.astimezone(tz).date()

    async def get_latest_date(self, channel_name):
        """
        Get the latest date of messages in a Discord channel.

        Args:
            channel_name (str): The name of the Discord channel.

        Returns:
            datetime.date: The latest date of messages in the channel.
        """
        channel = bot.get_channel(cfg['channel'][channel_name])
        latest_message = (await channel.history(limit=1).flatten())[0]
        return latest_message.created_at.astimezone(tz).date()

    async def message_to_md(self, m: discord.Message, time_str, md_dir, rel_att_dir):
        """
        Convert a Discord message to Markdown format and download the attachment.

        Args:
            m (discord.Message): The Discord message to convert.
            time_str (str): The formatted timestamp of the message.
            md_dir (str): The directory where the Markdown files are stored.
            rel_att_dir (str): The relative directory where the attachments are stored.

        Returns:
            str: The Markdown representation of the message.
        """
        title = m.author.display_name + '-' + time_str
        message = []
        message.append(f'#### {title}')
        att_count = 1
        if m.content:
            message.append(m.content)
        if m.embeds:
            for embed in m.embeds:
                if embed.type in ['rich', 'link']:
                    if embed.author:
                        message.append(f'{embed.author.name}:')
                    for attr in ['title', 'description']:
                        attr_content = getattr(embed, attr)
                        if isinstance(attr_content, str):
                            message.append(attr_content)
                    if embed.url:
                        message.append(f'<{embed.url}>')
                    if embed.image:
                        filelink = await self.add_attachment(embed.image.url, f'{time_str}-{att_count}', md_dir, rel_att_dir)
                        message.append(f'!{filelink}')
                        att_count += 1
                elif embed.type == 'image':
                    filelink = await self.add_attachment(embed.thumbnail.proxy_url, f'{time_str}-{att_count}', md_dir, rel_att_dir)
                    message.append(f'!{filelink}')
                    att_count += 1
        if m.attachments:
            for att in m.attachments:
                filelink = await self.add_attachment(att.url, f'{time_str}-{att_count}', md_dir, rel_att_dir)
                if att.content_type and 'image' in att.content_type:
                    message.append(f'!{filelink}')
                else:
                    message.append(filelink)
                att_count += 1
        return '\n'.join(message).replace(cfg['emoji']['fate'], '🔮')

    async def snapshot(self, channel_name):
        """
        Take a snapshot of a Discord channel and store it locally.

        Args:
            channel_name (str): The name of the Discord channel.
        """
        filename = f'{datetime.now(tz).strftime("%y%m%d")}.md'
        md_dir = channel_name
        rel_att_dir = pj('attachments', channel_name)
        file_path = self._resolve_path(md_dir, filename)
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        channel = bot.get_channel(cfg['channel'][channel_name])
        content = []
        async for m in channel.history(limit=None, oldest_first=True):
            if m.edited_at:
                dt = m.edited_at.astimezone(tz)
                time_str = dt.strftime('%y%m%d-%H%M%S') + '-EDIT'
            else:
                dt = m.created_at.astimezone(tz)
                time_str = dt.strftime('%y%m%d-%H%M%S')
            content.append(await self.message_to_md(m, time_str, md_dir, rel_att_dir))
        with open(file_path, 'w', encoding='utf8') as f:
            f.write('\n'.join(content))

    async def get_content_by_date(self, channel_name, start_date, end_date, md_dir, rel_att_dir):
        """
        Get the content of messages in a Discord channel within a specified date range.

        Args:
            channel_name (str): The name of the Discord channel.
            start_date (datetime.date): The start date of the range.
            end_date (datetime.date): The end date of the range.
            md_dir (str): The directory where the Markdown files are stored.
            rel_att_dir (str): The relative directory where the attachments are stored.

        Returns:
            str: The content of the messages in Markdown format.
        """
        start_date_min = datetime.combine(start_date, datetime.min.time())
        end_date_min = datetime.combine(end_date, datetime.min.time())
        channel = bot.get_channel(cfg['channel'][channel_name])
        content = []
        async for m in channel.history(limit=None, after=start_date_min, before=end_date_min, oldest_first=True):
            if m.edited_at:
                dt = m.edited_at.astimezone(tz)
                time_str = dt.strftime('%y%m%d-%H%M%S') + '-EDIT'
            else:
                dt = m.created_at.astimezone(tz)
                time_str = dt.strftime('%y%m%d-%H%M%S')
            content.append(await self.message_to_md(m, time_str, md_dir, rel_att_dir))
        return '\n'.join(content)

    async def backup_in_one_file(self, channel_name, start_date, end_date, md_dir, rel_att_dir, verbose=False):
        """
        Backup messages from a Discord channel to a single local Markdown file.

        Args:
            channel_name (str): The name of the Discord channel.
            start_date (datetime.date): The start date of the backup.
            end_date (datetime.date): The end date of the backup.
            md_dir (str): The directory where the Markdown files are stored.
            rel_att_dir (str): The relative directory where the attachments are stored.
            verbose (bool, optional): Whether to print verbose output. Defaults to False.
        """
        if verbose:
            self.log.info(f'Start backing up {channel_name} from {start_date.strftime("%y%m%d")} to {end_date.strftime("%y%m%d")}')
        file_path = self._resolve_path(md_dir, f'{channel_name}.md')
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        needs_newline = os.path.exists(file_path) and os.path.getsize(file_path) > 0
        content = await self.get_content_by_date(channel_name, start_date, end_date, md_dir, rel_att_dir)
        if not content:
            return
        with open(file_path, 'a', encoding='utf8') as f:
            if needs_newline:
                f.write('\n')
            f.write(content)

    async def backup_by_date(self, channel_name, start_date, end_date, md_dir, rel_att_dir, verbose=False):
        """
        Backup messages from a Discord channel to separate local Markdown files by date.

        Args:
            channel_name (str): The name of the Discord channel.
            start_date (datetime.date): The start date of the backup.
            end_date (datetime.date): The end date of the backup.
            md_dir (str): The directory where the Markdown files are stored.
            rel_att_dir (str): The relative directory where the attachments are stored.
            verbose (bool, optional): Whether to print verbose output. Defaults to False.
        """
        if verbose:
            self.log.info(f'start backing up {channel_name} from {start_date.strftime("%y%m%d")} to {end_date.strftime("%y%m%d")}')
        date = start_date
        md_path = self._resolve_path(md_dir)
        os.makedirs(md_path, exist_ok=True)
        while date < end_date:
            if verbose:
                self.log.info(f'backing up {date.strftime("%y%m%d")}')
            file_path = pj(md_path, f'{date.strftime("%y%m%d")}.md')
            content = await self.get_content_by_date(channel_name, date, date+timedelta(days=1), md_dir, rel_att_dir)
            if content:
                with open(file_path, 'w', encoding='utf8') as f:
                    f.write(content)
            date += timedelta(days=1)


async def dbx_backup_by_date(message=None, channel=None, start_date=None, end_date=None):
    """
    Backs up different channels to local storage.

    Args:
        message: The message to respond.
        start_date_str (str, optional): The start date in the format 'yymmdd'. Defaults to None.
    """
    end_date = datetime.now(tz).date() if end_date is None else end_date
    start_date_str = start_date.strftime('%y%m%d') if start_date else 'beginning'
    if message:
        await message.respond(embed=discord.Embed(description=f'Start backing up from {start_date_str} to {end_date.strftime("%y%m%d")}'))
        channel = message.channel
    dbx_backup = Backup()
    backup_by_date_ch = ['chat', 'night']
    backup_in_one_file_ch = ['record', 'tutorials', 'references', 'gallery', 'food', 'meme', 'game', 'animals', 'video', 'music']
    snapshot_ch = ['badge', 'bonus', 'a-board', 'c-board']
    for ch in backup_by_date_ch:
        start_date = await dbx_backup.get_earliest_date(ch) if start_date is None else start_date
        await dbx_backup.backup_by_date(ch, start_date, end_date, ch, 'attachments', verbose=True)
    for ch in backup_in_one_file_ch:
        start_date = await dbx_backup.get_earliest_date(ch) if start_date is None else start_date
        await dbx_backup.backup_in_one_file(ch, start_date, end_date, '', pj('attachments', ch), verbose=True)
    for ch in snapshot_ch:
        await dbx_backup.snapshot(ch)
    await channel.send(embed=discord.Embed(title=f'Backup from {start_date_str} to {end_date.strftime("%y%m%d")} finished'))
