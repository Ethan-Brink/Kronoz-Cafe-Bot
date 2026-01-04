import discord
from discord.ext import commands, tasks
from discord import app_commands
import asyncio
import random
import os
from datetime import datetime, timedelta, timezone
import json
import io

# ======================================================
# ⚙️ CONFIG
# ======================================================
GUILD_ID = 1441171105397346508
COUNTING_CHANNEL_ID = 1441204274964201664
MOD_LOG_CHANNEL_ID = 1455167564534513836
ANNOUNCEMENTS_CHANNEL_ID = None  # SET YOUR ANNOUNCEMENTS CHANNEL ID HERE
MAX_WARNINGS = 3

# Grand Opening Event Details
GRAND_OPENING_TIME = datetime(2026, 1, 5, 16, 0, 0, tzinfo=timezone.utc)  # 18:00 GMT+2 = 16:00 UTC
EVENT_LINK = "https://discord.com/events/1441171105397346508/1454456690987634850"
GAME_LINK = "https://www.roblox.com/games/114976671702338/Kronoz-Cafe"

# ======================================================
# 🔧 INTENTS
# ======================================================
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True
intents.moderation = True

# ======================================================
# 📊 WARNING STORAGE
# ======================================================
warnings_file = "warnings.json"

def load_warnings():
    try:
        with open(warnings_file, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_warnings(data):
    with open(warnings_file, 'w') as f:
        json.dump(data, f, indent=4)

warnings_data = load_warnings()

# ======================================================
# 🤖 BOT
# ======================================================
class KronozCafe(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        guild = discord.Object(id=GUILD_ID)
        await self.tree.sync(guild=guild)
        print("✅ Commands synced")
        
        # Start countdown task
        if not self.countdown_task.is_running():
            self.countdown_task.start()

    async def on_ready(self):
        print(f"☕ Kronoz Cafe online as {self.user}")

    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return

        if message.channel.id == COUNTING_CHANNEL_ID:
            await handle_counting(message)

        await self.process_commands(message)
    
    async def on_member_join(self, member: discord.Member):
        mod_channel = self.get_channel(MOD_LOG_CHANNEL_ID)
        if mod_channel:
            embed = discord.Embed(
                title="📥 Member Joined",
                description=f"{member.mention} ({member.name})",
                color=discord.Color.green(),
                timestamp=datetime.now(timezone.utc)
            )
            embed.add_field(name="Account Created", value=f"<t:{int(member.created_at.timestamp())}:R>", inline=True)
            embed.add_field(name="Member ID", value=str(member.id), inline=True)
            embed.set_thumbnail(url=member.display_avatar.url)
            await mod_channel.send(embed=embed)
    
    async def on_member_remove(self, member: discord.Member):
        mod_channel = self.get_channel(MOD_LOG_CHANNEL_ID)
        if mod_channel:
            embed = discord.Embed(
                title="📤 Member Left",
                description=f"{member.mention} ({member.name})",
                color=discord.Color.red(),
                timestamp=datetime.now(timezone.utc)
            )
            embed.add_field(name="Joined Server", value=f"<t:{int(member.joined_at.timestamp())}:R>" if member.joined_at else "Unknown", inline=True)
            embed.add_field(name="Member ID", value=str(member.id), inline=True)
            embed.set_thumbnail(url=member.display_avatar.url)
            await mod_channel.send(embed=embed)
    
    async def on_message_delete(self, message: discord.Message):
        if message.author.bot:
            return
        mod_channel = self.get_channel(MOD_LOG_CHANNEL_ID)
        if mod_channel and message.channel.id != MOD_LOG_CHANNEL_ID:
            embed = discord.Embed(
                title="🗑️ Message Deleted",
                color=discord.Color.red(),
                timestamp=datetime.now(timezone.utc)
            )
            embed.add_field(name="Author", value=message.author.mention, inline=True)
            embed.add_field(name="Channel", value=message.channel.mention, inline=True)
            if message.content:
                embed.add_field(name="Content", value=message.content[:1024], inline=False)
            await mod_channel.send(embed=embed)
    
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        if before.author.bot or before.content == after.content:
            return
        mod_channel = self.get_channel(MOD_LOG_CHANNEL_ID)
        if mod_channel and before.channel.id != MOD_LOG_CHANNEL_ID:
            embed = discord.Embed(
                title="✏️ Message Edited",
                color=discord.Color.orange(),
                timestamp=datetime.now(timezone.utc)
            )
            embed.add_field(name="Author", value=before.author.mention, inline=True)
            embed.add_field(name="Channel", value=before.channel.mention, inline=True)
            embed.add_field(name="Before", value=before.content[:512] if before.content else "No content", inline=False)
            embed.add_field(name="After", value=after.content[:512] if after.content else "No content", inline=False)
            embed.add_field(name="Jump to Message", value=f"[Click Here]({after.jump_url})", inline=False)
            await mod_channel.send(embed=embed)
    
    # ======================================================
    # 🎉 GRAND OPENING COUNTDOWN
    # ======================================================
    @tasks.loop(hours=1)
    async def countdown_task(self):
        if ANNOUNCEMENTS_CHANNEL_ID is None:
            return
        
        now = datetime.now(timezone.utc)
        time_until = GRAND_OPENING_TIME - now
        
        # Stop countdown after event starts
        if time_until.total_seconds() <= 0:
            self.countdown_task.cancel()
            await self.send_event_started()
            return
        
        hours_left = int(time_until.total_seconds() // 3600)
        
        # Send updates at specific milestones
        if hours_left in [24, 12, 6, 3, 1]:
            await self.send_countdown_update(hours_left)
    
    async def send_countdown_update(self, hours_left):
        channel = self.get_channel(ANNOUNCEMENTS_CHANNEL_ID)
        if not channel:
            return
        
        embed = discord.Embed(
            title="🎉 GRAND OPENING COUNTDOWN 🎉",
            description=f"**Kronoz Cafe** is opening soon!",
            color=discord.Color.gold(),
            timestamp=GRAND_OPENING_TIME
        )
        
        if hours_left >= 24:
            emoji = "📅"
            time_text = f"{hours_left // 24} day(s)"
        elif hours_left >= 6:
            emoji = "⏰"
            time_text = f"{hours_left} hours"
        else:
            emoji = "🔥"
            time_text = f"{hours_left} hour(s)"
        
        embed.add_field(
            name=f"{emoji} Time Remaining",
            value=f"**{time_text}** until opening!",
            inline=False
        )
        
        embed.add_field(
            name="🕐 Opening Time",
            value=f"<t:{int(GRAND_OPENING_TIME.timestamp())}:F>\n<t:{int(GRAND_OPENING_TIME.timestamp())}:R>",
            inline=False
        )
        
        embed.add_field(
            name="🎮 Join the Game",
            value=f"[Click here to play!]({GAME_LINK})",
            inline=True
        )
        
        embed.add_field(
            name="📅 Discord Event",
            value=f"[View Event Details]({EVENT_LINK})",
            inline=True
        )
        
        embed.set_footer(text="See you there! ☕")
        
        await channel.send("@everyone", embed=embed)
    
    async def send_event_started(self):
        channel = self.get_channel(ANNOUNCEMENTS_CHANNEL_ID)
        if not channel:
            return
        
        embed = discord.Embed(
            title="🎊 KRONOZ CAFE IS NOW OPEN! 🎊",
            description="The wait is over! Join us now for our **Grand Opening**!",
            color=discord.Color.green(),
            timestamp=datetime.now(timezone.utc)
        )
        
        embed.add_field(
            name="🎮 Play Now",
            value=f"[Join Kronoz Cafe!]({GAME_LINK})",
            inline=False
        )
        
        embed.add_field(
            name="📅 Event Details",
            value=f"[View on Discord]({EVENT_LINK})",
            inline=False
        )
        
        embed.set_footer(text="Welcome to Kronoz Cafe! ☕")
        
        await channel.send("@everyone 🎉", embed=embed)
    
    @countdown_task.before_loop
    async def before_countdown(self):
        await self.wait_until_ready()

bot = KronozCafe()
GUILD = discord.Object(id=GUILD_ID)

# ======================================================
# ❌ ERROR HANDLING
# ======================================================
@bot.tree.error
async def on_app_command_error(interaction, error):
    if isinstance(error, app_commands.errors.MissingPermissions):
        await interaction.response.send_message("❌ You don't have permission to use this command.", ephemeral=True)
    elif interaction.response.is_done():
        await interaction.followup.send("⚠️ Something went wrong.", ephemeral=True)
    else:
        await interaction.response.send_message("⚠️ Something went wrong.", ephemeral=True)
    print(error)

# ======================================================
# 🔢 COUNTING GAME
# ======================================================
current_count = 0

async def handle_counting(message: discord.Message):
    global current_count
    try:
        number = int(message.content)
        if number == current_count + 1:
            current_count += 1
            await message.add_reaction("✅")
        else:
            await message.delete()
            await message.channel.send("❌ Wrong number! Counting reset to **0**.", delete_after=3)
            current_count = 0
    except ValueError:
        await message.delete()

# ======================================================
# 🎉 MANUAL COUNTDOWN COMMAND
# ======================================================
@bot.tree.command(name="countdown", description="Show Grand Opening countdown", guild=GUILD)
async def countdown(interaction: discord.Interaction):
    now = datetime.now(timezone.utc)
    time_until = GRAND_OPENING_TIME - now
    
    if time_until.total_seconds() <= 0:
        await interaction.response.send_message("🎊 **The Grand Opening has started!** Join us now!", ephemeral=True)
        return
    
    days = time_until.days
    hours = int(time_until.seconds // 3600)
    minutes = int((time_until.seconds % 3600) // 60)
    
    embed = discord.Embed(
        title="🎉 Grand Opening Countdown",
        description=f"**{days}** days, **{hours}** hours, **{minutes}** minutes",
        color=discord.Color.gold(),
        timestamp=GRAND_OPENING_TIME
    )
    
    embed.add_field(
        name="🕐 Opens At",
        value=f"<t:{int(GRAND_OPENING_TIME.timestamp())}:F>",
        inline=False
    )
    
    embed.add_field(
        name="🎮 Game Link",
        value=f"[Kronoz Cafe]({GAME_LINK})",
        inline=True
    )
    
    embed.add_field(
        name="📅 Event Link",
        value=f"[Discord Event]({EVENT_LINK})",
        inline=True
    )
    
    embed.set_footer(text="See you there! ☕")
    
    await interaction.response.send_message(embed=embed)

# ======================================================
# 🛡 MODERATION - WARNING SYSTEM
# ======================================================
@bot.tree.command(name="warn", description="Warn a member", guild=GUILD)
@app_commands.checks.has_permissions(moderate_members=True)
async def warn(interaction: discord.Interaction, member: discord.Member, reason: str):
    global warnings_data
    
    member_id = str(member.id)
    
    if member_id not in warnings_data:
        warnings_data[member_id] = []
    
    if len(warnings_data[member_id]) >= MAX_WARNINGS:
        await interaction.response.send_message(
            f"❌ **Cannot issue warning!**\n"
            f"{member.mention} already has **{MAX_WARNINGS} warnings** (maximum reached).\n"
            f"Consider taking further action instead of issuing more warnings.",
            ephemeral=True
        )
        return
    
    warning_entry = {
        "reason": reason,
        "issued_by": interaction.user.id,
        "issued_by_name": str(interaction.user),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "warning_number": len(warnings_data[member_id]) + 1
    }
    
    warnings_data[member_id].append(warning_entry)
    save_warnings(warnings_data)
    
    warning_count = len(warnings_data[member_id])
    
    embed = discord.Embed(
        title="⚠️ Warning Issued",
        color=discord.Color.orange() if warning_count < MAX_WARNINGS else discord.Color.red()
    )
    embed.add_field(name="Member", value=member.mention, inline=True)
    embed.add_field(name="Warning #", value=f"{warning_count}/{MAX_WARNINGS}", inline=True)
    embed.add_field(name="Reason", value=reason, inline=False)
    embed.set_footer(text=f"Issued by {interaction.user}")
    
    if warning_count == MAX_WARNINGS:
        embed.add_field(
            name="⚠️ MAXIMUM WARNINGS REACHED",
            value=f"{member.mention} has reached the maximum of {MAX_WARNINGS} warnings!",
            inline=False
        )
    
    await interaction.response.send_message(embed=embed)
    
    mod_channel = bot.get_channel(MOD_LOG_CHANNEL_ID)
    if mod_channel:
        log_embed = discord.Embed(
            title="📋 Warning Logged",
            color=discord.Color.orange(),
            timestamp=datetime.now(timezone.utc)
        )
        log_embed.add_field(name="Member", value=f"{member.mention} ({member.id})", inline=False)
        log_embed.add_field(name="Warning Count", value=f"{warning_count}/{MAX_WARNINGS}", inline=True)
        log_embed.add_field(name="Issued By", value=interaction.user.mention, inline=True)
        log_embed.add_field(name="Reason", value=reason, inline=False)
        await mod_channel.send(embed=log_embed)

@bot.tree.command(name="warnings", description="View warning history for a member", guild=GUILD)
@app_commands.checks.has_permissions(moderate_members=True)
async def warnings(interaction: discord.Interaction, member: discord.Member):
    member_id = str(member.id)
    
    if member_id not in warnings_data or not warnings_data[member_id]:
        await interaction.response.send_message(
            f"✅ {member.mention} has no warnings.",
            ephemeral=True
        )
        return
    
    user_warnings = warnings_data[member_id]
    
    embed = discord.Embed(
        title=f"⚠️ Warning History for {member.display_name}",
        description=f"Total Warnings: **{len(user_warnings)}/{MAX_WARNINGS}**",
        color=discord.Color.red() if len(user_warnings) >= MAX_WARNINGS else discord.Color.orange()
    )
    
    for i, warning in enumerate(user_warnings, 1):
        issued_date = datetime.fromisoformat(warning['timestamp'])
        timestamp = f"<t:{int(issued_date.timestamp())}:R>"
        
        embed.add_field(
            name=f"Warning #{i}",
            value=(
                f"**Reason:** {warning['reason']}\n"
                f"**Issued by:** {warning['issued_by_name']}\n"
                f"**Date:** {timestamp}"
            ),
            inline=False
        )
    
    if len(user_warnings) >= MAX_WARNINGS:
        embed.set_footer(text="⚠️ This user has reached the maximum warning limit")
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="clearwarnings", description="Clear all warnings for a member", guild=GUILD)
@app_commands.checks.has_permissions(administrator=True)
async def clearwarnings(interaction: discord.Interaction, member: discord.Member):
    global warnings_data
    
    member_id = str(member.id)
    
    if member_id not in warnings_data or not warnings_data[member_id]:
        await interaction.response.send_message(
            f"{member.mention} has no warnings to clear.",
            ephemeral=True
        )
        return
    
    warning_count = len(warnings_data[member_id])
    warnings_data[member_id] = []
    save_warnings(warnings_data)
    
    await interaction.response.send_message(
        f"✅ Cleared **{warning_count}** warning(s) for {member.mention}"
    )
    
    mod_channel = bot.get_channel(MOD_LOG_CHANNEL_ID)
    if mod_channel:
        log_embed = discord.Embed(
            title="🧹 Warnings Cleared",
            color=discord.Color.green(),
            timestamp=datetime.now(timezone.utc)
        )
        log_embed.add_field(name="Member", value=f"{member.mention} ({member.id})", inline=False)
        log_embed.add_field(name="Warnings Cleared", value=str(warning_count), inline=True)
        log_embed.add_field(name="Cleared By", value=interaction.user.mention, inline=True)
        await mod_channel.send(embed=log_embed)

# ======================================================
# 🔨 BAN/KICK/TIMEOUT COMMANDS
# ======================================================
@bot.tree.command(name="ban", description="Ban a member from the server", guild=GUILD)
@app_commands.checks.has_permissions(ban_members=True)
async def ban(interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided"):
    try:
        await member.ban(reason=reason)
        
        embed = discord.Embed(
            title="🔨 Member Banned",
            color=discord.Color.red()
        )
        embed.add_field(name="Member", value=f"{member.mention} ({member.name})", inline=True)
        embed.add_field(name="Moderator", value=interaction.user.mention, inline=True)
        embed.add_field(name="Reason", value=reason, inline=False)
        
        await interaction.response.send_message(embed=embed)
        
        mod_channel = bot.get_channel(MOD_LOG_CHANNEL_ID)
        if mod_channel:
            log_embed = discord.Embed(
                title="🔨 Ban Logged",
                color=discord.Color.red(),
                timestamp=datetime.now(timezone.utc)
            )
            log_embed.add_field(name="Member", value=f"{member.mention} ({member.id})", inline=False)
            log_embed.add_field(name="Moderator", value=interaction.user.mention, inline=True)
            log_embed.add_field(name="Reason", value=reason, inline=False)
            await mod_channel.send(embed=log_embed)
    except discord.Forbidden:
        await interaction.response.send_message("❌ I don't have permission to ban this member.", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ An error occurred: {str(e)}", ephemeral=True)

@bot.tree.command(name="unban", description="Unban a user from the server", guild=GUILD)
@app_commands.checks.has_permissions(ban_members=True)
async def unban(interaction: discord.Interaction, user_id: str, reason: str = "No reason provided"):
    try:
        user = await bot.fetch_user(int(user_id))
        await interaction.guild.unban(user, reason=reason)
        
        embed = discord.Embed(
            title="✅ User Unbanned",
            color=discord.Color.green()
        )
        embed.add_field(name="User", value=f"{user.mention} ({user.name})", inline=True)
        embed.add_field(name="Moderator", value=interaction.user.mention, inline=True)
        embed.add_field(name="Reason", value=reason, inline=False)
        
        await interaction.response.send_message(embed=embed)
        
        mod_channel = bot.get_channel(MOD_LOG_CHANNEL_ID)
        if mod_channel:
            log_embed = discord.Embed(
                title="✅ Unban Logged",
                color=discord.Color.green(),
                timestamp=datetime.now(timezone.utc)
            )
            log_embed.add_field(name="User", value=f"{user.mention} ({user.id})", inline=False)
            log_embed.add_field(name="Moderator", value=interaction.user.mention, inline=True)
            log_embed.add_field(name="Reason", value=reason, inline=False)
            await mod_channel.send(embed=log_embed)
    except ValueError:
        await interaction.response.send_message("❌ Invalid user ID.", ephemeral=True)
    except discord.NotFound:
        await interaction.response.send_message("❌ User not found or not banned.", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ An error occurred: {str(e)}", ephemeral=True)

@bot.tree.command(name="kick", description="Kick a member from the server", guild=GUILD)
@app_commands.checks.has_permissions(kick_members=True)
async def kick(interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided"):
    try:
        await member.kick(reason=reason)
        
        embed = discord.Embed(
            title="👢 Member Kicked",
            color=discord.Color.orange()
        )
        embed.add_field(name="Member", value=f"{member.mention} ({member.name})", inline=True)
        embed.add_field(name="Moderator", value=interaction.user.mention, inline=True)
        embed.add_field(name="Reason", value=reason, inline=False)
        
        await interaction.response.send_message(embed=embed)
        
        mod_channel = bot.get_channel(MOD_LOG_CHANNEL_ID)
        if mod_channel:
            log_embed = discord.Embed(
                title="👢 Kick Logged",
                color=discord.Color.orange(),
                timestamp=datetime.now(timezone.utc)
            )
            log_embed.add_field(name="Member", value=f"{member.mention} ({member.id})", inline=False)
            log_embed.add_field(name="Moderator", value=interaction.user.mention, inline=True)
            log_embed.add_field(name="Reason", value=reason, inline=False)
            await mod_channel.send(embed=log_embed)
    except discord.Forbidden:
        await interaction.response.send_message("❌ I don't have permission to kick this member.", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ An error occurred: {str(e)}", ephemeral=True)

@bot.tree.command(name="timeout", description="Timeout a member", guild=GUILD)
@app_commands.checks.has_permissions(moderate_members=True)
async def timeout(interaction: discord.Interaction, member: discord.Member, duration: int, unit: str, reason: str = "No reason provided"):
    if unit.lower() not in ['minutes', 'hours', 'days']:
        await interaction.response.send_message("❌ Unit must be 'minutes', 'hours', or 'days'.", ephemeral=True)
        return
    
    try:
        if unit.lower() == 'minutes':
            delta = timedelta(minutes=duration)
        elif unit.lower() == 'hours':
            delta = timedelta(hours=duration)
        else:
            delta = timedelta(days=duration)
        
        await member.timeout(delta, reason=reason)
        
        embed = discord.Embed(
            title="⏰ Member Timed Out",
            color=discord.Color.orange()
        )
        embed.add_field(name="Member", value=member.mention, inline=True)
        embed.add_field(name="Duration", value=f"{duration} {unit}", inline=True)
        embed.add_field(name="Moderator", value=interaction.user.mention, inline=True)
        embed.add_field(name="Reason", value=reason, inline=False)
        
        await interaction.response.send_message(embed=embed)
        
        mod_channel = bot.get_channel(MOD_LOG_CHANNEL_ID)
        if mod_channel:
            log_embed = discord.Embed(
                title="⏰ Timeout Logged",
                color=discord.Color.orange(),
                timestamp=datetime.now(timezone.utc)
            )
            log_embed.add_field(name="Member", value=f"{member.mention} ({member.id})", inline=False)
            log_embed.add_field(name="Duration", value=f"{duration} {unit}", inline=True)
            log_embed.add_field(name="Moderator", value=interaction.user.mention, inline=True)
            log_embed.add_field(name="Reason", value=reason, inline=False)
            await mod_channel.send(embed=log_embed)
    except discord.Forbidden:
        await interaction.response.send_message("❌ I don't have permission to timeout this member.", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ An error occurred: {str(e)}", ephemeral=True)

@bot.tree.command(name="untimeout", description="Remove timeout from a member", guild=GUILD)
@app_commands.checks.has_permissions(moderate_members=True)
async def untimeout(interaction: discord.Interaction, member: discord.Member):
    try:
        await member.timeout(None)
        await interaction.response.send_message(f"✅ Removed timeout from {member.mention}")
        
        mod_channel = bot.get_channel(MOD_LOG_CHANNEL_ID)
        if mod_channel:
            log_embed = discord.Embed(
                title="✅ Timeout Removed",
                color=discord.Color.green(),
                timestamp=datetime.now(timezone.utc)
            )
            log_embed.add_field(name="Member", value=f"{member.mention} ({member.id})", inline=True)
            log_embed.add_field(name="Moderator", value=interaction.user.mention, inline=True)
            await mod_channel.send(embed=log_embed)
    except Exception as e:
        await interaction.response.send_message(f"❌ An error occurred: {str(e)}", ephemeral=True)

# ======================================================
# 👤 USER INFO & ROLE MANAGEMENT
# ======================================================
@bot.tree.command(name="userinfo", description="Get information about a member", guild=GUILD)
async def userinfo(interaction: discord.Interaction, member: discord.Member = None):
    member = member or interaction.user
    
    member_id = str(member.id)
    warning_count = len(warnings_data.get(member_id, []))
    
    embed = discord.Embed(
        title=f"User Info - {member.display_name}",
        color=member.color
    )
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.add_field(name="Username", value=member.name, inline=True)
    embed.add_field(name="ID", value=member.id, inline=True)
    embed.add_field(name="Warnings", value=f"{warning_count}/{MAX_WARNINGS}", inline=True)
    embed.add_field(name="Account Created", value=f"<t:{int(member.created_at.timestamp())}:R>", inline=True)
    embed.add_field(name="Joined Server", value=f"<t:{int(member.joined_at.timestamp())}:R>", inline=True)
    
    roles = [role.mention for role in member.roles if role.name != "@everyone"]
    if roles:
        embed.add_field(name=f"Roles ({len(roles)})", value=", ".join(roles), inline=False)
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="addrole", description="Add a role to a member", guild=GUILD)
@app_commands.checks.has_permissions(manage_roles=True)
async def addrole(interaction: discord.Interaction, member: discord.Member, role: discord.Role):
    try:
        await member.add_roles(role)
        await interaction.response.send_message(f"✅ Added {role.mention} to {member.mention}")
        
        mod_channel = bot.get_channel(MOD_LOG_CHANNEL_ID)
        if mod_channel:
            log_embed = discord.Embed(
                title="➕ Role Added",
                color=discord.Color.green(),
                timestamp=datetime.now(timezone.utc)
            )
            log_embed.add_field(name="Member", value=member.mention, inline=True)
            log_embed.add_field(name="Role", value=role.mention, inline=True)
            log_embed.add_field(name="Added By", value=interaction.user.mention, inline=True)
            await mod_channel.send(embed=log_embed)
    except discord.Forbidden:
        await interaction.response.send_message("❌ I don't have permission to manage this role.", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ An error occurred: {str(e)}", ephemeral=True)

@bot.tree.command(name="removerole", description="Remove a role from a member", guild=GUILD)
@app_commands.checks.has_permissions(manage_roles=True)
async def removerole(interaction: discord.Interaction, member: discord.Member, role: discord.Role):
    try:
        await member.remove_roles(role)
        await interaction.response.send_message(f"✅ Removed {role.mention} from {member.mention}")
        
        mod_channel = bot.get_channel(MOD_LOG_CHANNEL_ID)
        if mod_channel:
            log_embed = discord.Embed(
                title="➖ Role Removed",
                color=discord.Color.red(),
                timestamp=datetime.now(timezone.utc)
            )
            log_embed.add_field(name="Member", value=member.mention, inline=True)
            log_embed.add_field(name="Role", value=role.mention, inline=True)
            log_embed.add_field(name="Removed By", value=interaction.user.mention, inline=True)
            await mod_channel.send(embed=log_embed)
    except discord.Forbidden:
        await interaction.response.send_message("❌ I don't have permission to manage this role.", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ An error occurred: {str(e)}", ephemeral=True)

# Rest of commands (announce, slowmode, lock, unlock, clear, giveaway, poll, tickets, etc.) from original code...
# [Copy remaining commands from your original bot code]

# ======================================================
# 🔐 LOGIN
# ======================================================
token = os.getenv("DISCORD_TOKEN")
if not token:
    raise ValueError("❌ DISCORD_TOKEN environment variable not set!")

bot.run(token)