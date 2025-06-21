import discord
from discord.ext import commands
import yt_dlp
import asyncio

ytdl_format_options = {
    "format": "bestaudio[ext=webm]/bestaudio[ext=m4a]/bestaudio/best",
    "outtmpl": "%(extractor)s-%(id)s-%(title)s.%(ext)s",
    "restrictfilenames": True,
    "noplaylist": False,
    "nocheckcertificate": True,
    "ignoreerrors": True,
    "logtostderr": False,
    "quiet": True,
    "no_warnings": True,
    "default_search": "auto",
    "source_address": "0.0.0.0",
    "http_chunk_size": 10485760,
    "retries": 5,
    "socket_timeout": 60,
    "extract_flat": False,
    "writethumbnail": False,
    "writeinfojson": False,
    "writesubtitles": False,
    "http_headers": {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-us,en;q=0.5",
        "Accept-Encoding": "gzip,deflate",
        "Accept-Charset": "ISO-8859-1,utf-8;q=0.7,*;q=0.7",
        "Keep-Alive": "300",
        "Connection": "keep-alive",
    },
    "age_limit": 99,
}

ffmpeg_options = {
    "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5 -rw_timeout 30000000 -timeout 30000000",
    "options": "-vn -filter:a volume=0.5 -ar 48000 -ac 2",
}
ytdl = yt_dlp.YoutubeDL(ytdl_format_options)


class MusicCog(commands.Cog):
    def __init__(self, bot, ffmpeg_path="ffmpeg"):
        self.bot = bot
        self.queue = []
        self.play_lock = asyncio.Lock()
        self.ffmpeg_path = ffmpeg_path

    @commands.Cog.listener()
    async def on_ready(self):
        print(f"Logged in as {self.bot.user.name}")

    @commands.command()
    async def play(self, ctx, *, url):
        voice_channel = ctx.author.voice.channel if ctx.author.voice else None
        if not voice_channel:
            return await ctx.send("Ти не у войсі")
        if not ctx.voice_client:
            await voice_channel.connect()

        loop = asyncio.get_event_loop()
        try:
            data = await loop.run_in_executor(
                None, lambda: ytdl.extract_info(url, download=False)
            )
        except yt_dlp.utils.DownloadError as e:
            return await ctx.send(f"Помилка завантаження: {e}")
        except Exception as e:
            return await ctx.send(f"Неочікувана помилка: {e}")
        if data is None:
            return await ctx.send("не вдалося отримати інфу про трек.")

        if "entries" in data and len(data.get("entries", [])) > 1:
            title = data.get("title", "Невідомий плейлист")
            entries = data.get("entries", [])
            added_count = 0
            for entry in entries:
                if entry is not None:
                    entry_url = entry.get("url")
                    entry_title = entry.get("title", "Unknown Title")
                    if entry_url:
                        self.queue.append((entry_url, entry_title))
                        added_count += 1

            await ctx.send(
                f"Додано плейлист **{title}** до черги ({added_count} треків)"
            )
        else:
            if "entries" in data:
                data = data["entries"][0] if data["entries"] else None
            if data is None:
                return await ctx.send("не вдалося отримати інфу про трек.")
            url = data["url"]
            title = data.get("title", "Unknown Title")
            if not url:
                return await ctx.send("не вдалося отримати URL треку.")
            self.queue.append((url, title))
            await ctx.send(f"Додано до черги: **{title}**")
        if not ctx.voice_client.is_playing():
            await self.play_next(ctx)

    async def play_next(self, ctx):
        async with self.play_lock:
            if ctx.voice_client.is_playing():
                return
            if not self.queue:
                return await ctx.send("Черга порожня.")
            url, title = self.queue.pop(0)
            source = discord.FFmpegOpusAudio(
                url,
                executable=self.ffmpeg_path,
                before_options=ffmpeg_options["before_options"],
                options=ffmpeg_options["options"],
            )
            ctx.voice_client.play(
                source, after=lambda _: self.bot.loop.create_task(self.play_next(ctx))
            )

    @commands.command()
    async def stop(self, ctx):
        if ctx.voice_client and ctx.voice_client.is_playing():
            await ctx.voice_client.disconnect()
            self.queue.clear()

    @commands.command()
    async def skip(self, ctx):
        if ctx.voice_client and ctx.voice_client.is_playing():
            ctx.voice_client.stop()
            await self.play_next(ctx)
        else:
            await ctx.send("اخرج من هنا")


async def setup(bot):
    await bot.add_cog(MusicCog(bot))
