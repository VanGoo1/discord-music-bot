import logging
import discord
from discord.ext import commands
from dotenv import load_dotenv
import os
from MusicCog import MusicCog

load_dotenv()
token = str(os.getenv("DISCORD_TOKEN"))
ffmpeg_path = str(os.getenv("FFMPEG_PATH"))
handler = logging.FileHandler(filename="discord.log", encoding="utf-8", mode="w")


class MusicBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.voice_states = True
        super().__init__(command_prefix="+", intents=intents)

    async def setup_hook(self):
        await self.add_cog(MusicCog(self, ffmpeg_path=ffmpeg_path))


if __name__ == "__main__":
    bot = MusicBot()
    bot.run(token, log_handler=handler, log_level=logging.DEBUG)
