# bot.py - Enhanced Main Bot File
import discord
from discord.ext import commands, tasks
from discord import app_commands
import os
from datetime import datetime, timezone
from database import Database
from typing import Optional

# Import config if you have one, otherwise define here
try:
    from config import *
except ImportError:
    # Default config values
    GUILD_ID = 1457746056749125644  # Replace with your server ID
    MOD_LOG_CHANNEL_ID = 1462001894934315009  # Replace with mod log channel
    SUGGESTION_CHANNEL_ID = 1458733613142114418  # Replace with suggestion channel
    WELCOME_CHANNEL_ID = 1467132930609381441  # Replace with welcome channel

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
        
        # Try to import Roblox API if available
        try:
            from roblox_api import RobloxAPI
            self.roblox = RobloxAPI()
        except ImportError:
            self.roblox = None
            print("⚠️ RobloxAPI not found, Roblox features disabled")

    async def setup_hook(self):
        """Load all cogs with error handling"""
        
        # Original cogs (if they exist)
        original_cogs = [
            "cogs.moderation",
            "cogs.roblox_integration", 
            "cogs.tickets",
            "cogs.loa",
            "cogs.staff_management",
            "cogs.appeals"
        ]
        
        # New feature cogs
        new_cogs = [
            "cogs.fun",
            "cogs.economy",
            "cogs.advanced_features"
        ]
        
        all_cogs = original_cogs + new_cogs
        
        for cog in all_cogs:
            try:
                await self.load_extension(cog)
                print(f"✅ Loaded {cog}")
            except Exception as e:
                print(f"⚠️ Skipped {cog}: {e}")
        
        # Sync commands
        try:
            guild = discord.Object(id=GUILD_ID)
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
            print("✅ Commands synced to guild")
        except Exception as e:
            print(f"⚠️ Command sync warning: {e}")

    async def on_ready(self):
        """Bot startup event"""
        print("=" * 50)
        print("☕ KRONOZ CAFE BOT - ENHANCED VERSION")
        print("=" * 50)
        print(f"   Logged in as: {self.user}")
        print(f"   User ID: {self.user.id}")
        print(f"   Servers: {len(self.guilds)}")
        print(f"   Python Discord Version: {discord.__version__}")
        print("=" * 50)
        print("📊 Database initialized with all tables")
        print("🎮 All feature cogs loaded")
        print("=" * 50)
        
        # Set bot activity
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name="Kronoz Cafe | /help"
            )
        )
    
    async def on_member_join(self, member: discord.Member):
        """Welcome new members"""
        try:
            # Log to database
            self.db.execute(
                "INSERT INTO message_stats (user_id, join_date) VALUES (?, ?)",
                (member.id, datetime.utcnow().isoformat())
            )
            
            # Send welcome message
            welcome_channel = self.get_channel(WELCOME_CHANNEL_ID)
            if welcome_channel:
                embed = discord.Embed(
                    title="☕ Welcome to Kronoz Cafe!",
                    description=f"Welcome {member.mention}! We're glad to have you here!",
                    color=discord.Color.green()
                )
                embed.set_thumbnail(url=member.display_avatar.url)
                embed.add_field(
                    name="Get Started",
                    value="• Read the rules\n• Verify yourself\n• Check out our channels!",
                    inline=False
                )
                embed.set_footer(text=f"Member #{member.guild.member_count}")
                
                await welcome_channel.send(embed=embed)
            
            # Auto-role (if configured)
            auto_role = self.db.fetchone(
                "SELECT role_id FROM auto_roles WHERE guild_id = ? AND enabled = 1",
                (member.guild.id,)
            )
            
            if auto_role:
                role = member.guild.get_role(auto_role[0])
                if role:
                    await member.add_roles(role)
                    
        except Exception as e:
            print(f"Error in on_member_join: {e}")
    
    async def on_member_remove(self, member: discord.Member):
        """Log member leaves"""
        try:
            welcome_channel = self.get_channel(WELCOME_CHANNEL_ID)
            if welcome_channel:
                embed = discord.Embed(
                    description=f"👋 {member.mention} has left the cafe.",
                    color=discord.Color.red()
                )
                embed.set_footer(text=f"Member count: {member.guild.member_count}")
                
                await welcome_channel.send(embed=embed)
        except Exception as e:
            print(f"Error in on_member_remove: {e}")
    
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

# Help command
@bot.tree.command(name="help", description="View all available commands")
async def help_command(interaction: discord.Interaction):
    """Comprehensive help command"""
    embed = discord.Embed(
        title="☕ Kronoz Cafe Bot - Command List",
        description="Here are all available commands!",
        color=discord.Color.blue()
    )
    
    # Fun Commands
    embed.add_field(
        name="🎮 Fun & Games",
        value=(
            "`/trivia` - Play trivia\n"
            "`/8ball` - Ask the magic 8-ball\n"
            "`/coinflip` - Flip a coin\n"
            "`/roll` - Roll dice\n"
            "`/choose` - Random choice\n"
            "`/poll` - Create a poll"
        ),
        inline=False
    )
    
    # Economy
    embed.add_field(
        name="💰 Economy",
        value=(
            "`/balance` - Check balance\n"
            "`/daily` - Daily reward\n"
            "`/work` - Work for coins\n"
            "`/pay` - Transfer coins\n"
            "`/shop` - View shop\n"
            "`/buy` - Purchase items\n"
            "`/richest` - Leaderboard"
        ),
        inline=False
    )
    
    # Utility
    embed.add_field(
        name="🛠️ Utility",
        value=(
            "`/userinfo` - User information\n"
            "`/serverinfo` - Server info\n"
            "`/avatar` - Get avatar\n"
            "`/remind` - Set reminder\n"
            "`/afk` - Set AFK status\n"
            "`/suggest` - Submit suggestion"
        ),
        inline=False
    )
    
    # Moderation (Staff only)
    embed.add_field(
        name="🛡️ Moderation (Staff)",
        value=(
            "`/warn` - Warn user\n"
            "`/kick` - Kick user\n"
            "`/ban` - Ban user\n"
            "`/timeout` - Timeout user\n"
            "`/purge` - Delete messages\n"
            "`/lock` - Lock channel\n"
            "`/unlock` - Unlock channel\n"
            "`/slowmode` - Set slowmode\n"
            "`/announce` - Create announcement\n"
            "`/giveaway` - Start giveaway"
        ),
        inline=False
    )
    
    # Leaderboards
    embed.add_field(
        name="🏆 Leaderboards",
        value=(
            "`/leaderboard` - Trivia leaders\n"
            "`/richest` - Economy leaders"
        ),
        inline=False
    )
    
    embed.set_footer(text="Use /command to run any command!")
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

# Error handler
@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    """Global error handler for slash commands"""
    
    if isinstance(error, app_commands.errors.MissingPermissions):
        embed = discord.Embed(
            title="❌ Missing Permissions",
            description="You don't have permission to use this command!",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    elif isinstance(error, app_commands.errors.CommandOnCooldown):
        embed = discord.Embed(
            title="⏰ Command on Cooldown",
            description=f"Try again in {error.retry_after:.1f} seconds!",
            color=discord.Color.orange()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    else:
        embed = discord.Embed(
            title="❌ Error",
            description="An error occurred while executing this command!",
            color=discord.Color.red()
        )
        
        if interaction.response.is_done():
            await interaction.followup.send(embed=embed, ephemeral=True)
        else:
            await interaction.response.send_message(embed=embed, ephemeral=True)
        
        print(f"Command error: {error}")

if __name__ == "__main__":
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        print("=" * 50)
        print("❌ ERROR: DISCORD_TOKEN not found!")
        print("=" * 50)
        print("Please set your Discord bot token:")
        print("1. Create a .env file in the same directory")
        print("2. Add: DISCORD_TOKEN=your_token_here")
        print("=" * 50)
        raise ValueError("DISCORD_TOKEN not set in environment variables!")
    
    try:
        bot.run(token)
    except Exception as e:
        print(f"❌ Failed to start bot: {e}")