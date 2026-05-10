import discord
from discord.ext import commands
import os
from config import TOKEN
from database import init_db

class KronozCafe(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        intents.moderation = True
        super().__init__(command_prefix="!", intents=intents, help_command=None)

    async def setup_hook(self):
        await init_db()
        
        print("🔄 Loading cogs...")
        for filename in os.listdir("./cogs"):
            if filename.endswith(".py") and not filename.startswith("__"):
                try:
                    await self.load_extension(f"cogs.{filename[:-3]}")
                    print(f"✅ Loaded cog: {filename[:-3]}")
                except Exception as e:
                    print(f"❌ Failed to load {filename}: {e}")

        # Aggressive Guild Sync
        print("🔄 Attempting guild command sync...")
        if self.guilds:
            guild = self.guilds[0]
            try:
                await self.tree.sync(guild=guild)
                print(f"✅ Synced {len(self.tree.get_commands(guild=guild))} commands to {guild.name}")
            except Exception as e:
                print(f"Sync error: {e}")
        else:
            await self.tree.sync()

bot = KronozCafe()

@bot.event
async def on_ready():
    print(f"✅ {bot.user} is online!")
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="over the cafe ☕"))

bot.run(TOKEN)