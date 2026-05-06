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
            if filename.endswith(".py"):
                try:
                    await self.load_extension(f"cogs.{filename[:-3]}")
                    print(f"✅ Loaded cog: {filename[:-3]}")
                except Exception as e:
                    print(f"❌ Failed to load {filename}: {e}")

        # Fast guild sync for testing
        if self.guilds:
            test_guild = self.guilds[0]
            await self.tree.sync(guild=test_guild)
            print(f"✅ Commands synced to guild: {test_guild.name} (Fast!)")
        else:
            await self.tree.sync()
            print("✅ Global sync started (may take up to 1 hour)")

bot = KronozCafe()

@bot.event
async def on_ready():
    print(f"✅ {bot.user} is now online!")
    await bot.change_presence(activity=discord.Activity(
        type=discord.ActivityType.watching, 
        name="Looking over the cafe ☕"
    ))
    print("🌟 Bot is ready!")

bot.run(TOKEN)