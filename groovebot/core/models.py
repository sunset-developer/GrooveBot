import asyncio
import uuid

import discord
import youtube_dl as youtube_dl
from tortoise import Model, fields


class BaseModel(Model):
    id = fields.IntField(pk=True)
    uid = fields.UUIDField(default=uuid.uuid1, max_length=36)
    parent_uid = fields.UUIDField(null=True, max_length=36)
    date_created = fields.DatetimeField(auto_now_add=True)
    date_updated = fields.DatetimeField(auto_now=True)

    class Meta:
        abstract = True


class Fact(BaseModel):
    content = fields.CharField(max_length=255)


class Abbreviation(BaseModel):
    acronym = fields.CharField(max_length=12, unique=True)
    description = fields.CharField(max_length=45)


class Album(Abbreviation):
    pass


class Music(Album):
    url = fields.CharField(max_length=45)


class YTDLSource(discord.PCMVolumeTransformer):
    youtube_dl.utils.bug_reports_message = lambda: ''

    ytdl_format_options = {
        'format': 'bestaudio/best',
        'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
        'restrictfilenames': True,
        'noplaylist': True,
        'nocheckcertificate': True,
        'ignoreerrors': False,
        'logtostderr': False,
        'quiet': True,
        'no_warnings': True,
        'default_search': 'auto',
        'source_address': '0.0.0.0'  # bind to ipv4 since ipv6 addresses cause issues sometimes
    }

    ffmpeg_options = {
        'options': '-vn'
    }

    ytdl = youtube_dl.YoutubeDL(ytdl_format_options)

    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)
        self.data = data
        self.title = data.get('title')
        self.url = data.get('url')

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=False):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: cls.ytdl.extract_info(url, download=not stream))
        if 'entries' in data:
            data = data['entries'][0]
        filename = data['url'] if stream else cls.ytdl.prepare_filename(data)
        return filename, cls(discord.FFmpegPCMAudio(filename, **cls.ffmpeg_options), data=data)