# bot.py - Main bot file
import discord
from discord.ext import commands, tasks
from discord import app_commands
import os
from datetime import datetime, timezone
from database import Database
from roblox_api import RobloxAPI
from config import *

# Bot Setup
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True
intents.moderation = True

class KronozCafe(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)
        self.db = Database()
        self.roblox = RobloxAPI()

    async def setup_hook(self):
        # Import all cogs
        await self.load_extension("cogs.moderation")
        await self.load_extension("cogs.roblox_integration")
        await self.load_extension("cogs.tickets")
        await self.load_extension("cogs.loa")
        await self.load_extension("cogs.staff_management")
        
        guild = discord.Object(id=GUILD_ID)
        self.tree.copy_global_to(guild=guild)
        await self.tree.sync(guild=guild)
        print("✅ Commands synced")

    async def on_ready(self):
        print(f"☕ Kronoz Cafe Bot Online")
        print(f"   User: {self.user}")
        print(f"   ID: {self.user.id}")
        print(f"📊 Database initialized")
    
    async def send_dm_with_fallback(self, user: discord.User, embed: discord.Embed):
        """Try to DM user, if fails, log to mod channel"""
        try:
            await user.send(embed=embed)
            return True
        except (discord.Forbidden, discord.HTTPException):
            mod_channel = self.get_channel(MOD_LOG_CHANNEL_ID)
            if mod_channel:
                fallback = discord.Embed(
                    title="⚠️ Failed to DM User",
                    description=f"Could not send DM to {user.mention}",
                    color=discord.Color.orange()
                )
                for field in embed.fields:
                    fallback.add_field(name=field.name, value=field.value, inline=field.inline)
                await mod_channel.send(embed=fallback)
            return False

bot = KronozCafe()

if __name__ == "__main__":
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        raise ValueError("❌ DISCORD_TOKEN not set in environment variables!")
    bot.run(token)