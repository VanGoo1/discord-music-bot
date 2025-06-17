import discord
from discord.ext import commands
import yt_dlp
import asyncio
import os


ytdl_format_options = {
    "format": "bestaudio/best",
    "outtmpl": "%(extractor)s-%(id)s-%(title)s.%(ext)s",
    "restrictfilenames": True,
    "noplaylist": False,
    "nocheckcertificate": True,
    "ignoreerrors": False,
    "logtostderr": False,
    "quiet": True,
    "no_warnings": True,
    "default_search": "auto",
    "source_address": "0.0.0.0",
    "extractor_args": {"soundcloud": {"client_id": None}},
    "http_chunk_size": 10485760,
    "retries": 5,
    "socket_timeout": 60,
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
            return await ctx.send("Ти не в голосовому чаті")
        if not ctx.voice_client:
            await voice_channel.connect()

        loop = asyncio.get_event_loop()
        data = await loop.run_in_executor(
            None, lambda: ytdl.extract_info(url, download=False)
        )
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
