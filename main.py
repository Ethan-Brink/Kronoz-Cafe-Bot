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
MAX_WARNINGS = 3

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

# ======================================================
# 📢 ANNOUNCEMENT & CHANNEL MANAGEMENT
# ======================================================
@bot.tree.command(name="announce", description="Send an announcement", guild=GUILD)
@app_commands.checks.has_permissions(manage_messages=True)
async def announce(interaction: discord.Interaction, channel: discord.TextChannel, title: str, message: str):
    embed = discord.Embed(
        title=f"📢 {title}",
        description=message,
        color=discord.Color.blue(),
        timestamp=datetime.now(timezone.utc)
    )
    embed.set_footer(text=f"Announced by {interaction.user.name}", icon_url=interaction.user.display_avatar.url)
    
    await channel.send(embed=embed)
    await interaction.response.send_message(f"✅ Announcement sent to {channel.mention}", ephemeral=True)

@bot.tree.command(name="slowmode", description="Set slowmode for a channel", guild=GUILD)
@app_commands.checks.has_permissions(manage_channels=True)
async def slowmode(interaction: discord.Interaction, seconds: int, channel: discord.TextChannel = None):
    channel = channel or interaction.channel
    
    if seconds < 0 or seconds > 21600:
        await interaction.response.send_message("❌ Slowmode must be between 0 and 21600 seconds (6 hours).", ephemeral=True)
        return
    
    try:
        await channel.edit(slowmode_delay=seconds)
        if seconds == 0:
            await interaction.response.send_message(f"✅ Slowmode disabled in {channel.mention}")
        else:
            await interaction.response.send_message(f"✅ Slowmode set to {seconds} seconds in {channel.mention}")
    except Exception as e:
        await interaction.response.send_message(f"❌ An error occurred: {str(e)}", ephemeral=True)

@bot.tree.command(name="lock", description="Lock a channel", guild=GUILD)
@app_commands.checks.has_permissions(manage_channels=True)
async def lock(interaction: discord.Interaction, channel: discord.TextChannel = None):
    channel = channel or interaction.channel
    
    try:
        await channel.set_permissions(interaction.guild.default_role, send_messages=False)
        await interaction.response.send_message(f"🔒 Locked {channel.mention}")
        
        mod_channel = bot.get_channel(MOD_LOG_CHANNEL_ID)
        if mod_channel:
            log_embed = discord.Embed(
                title="🔒 Channel Locked",
                color=discord.Color.red(),
                timestamp=datetime.now(timezone.utc)
            )
            log_embed.add_field(name="Channel", value=channel.mention, inline=True)
            log_embed.add_field(name="Locked By", value=interaction.user.mention, inline=True)
            await mod_channel.send(embed=log_embed)
    except Exception as e:
        await interaction.response.send_message(f"❌ An error occurred: {str(e)}", ephemeral=True)

@bot.tree.command(name="unlock", description="Unlock a channel", guild=GUILD)
@app_commands.checks.has_permissions(manage_channels=True)
async def unlock(interaction: discord.Interaction, channel: discord.TextChannel = None):
    channel = channel or interaction.channel
    
    try:
        await channel.set_permissions(interaction.guild.default_role, send_messages=None)
        await interaction.response.send_message(f"🔓 Unlocked {channel.mention}")
        
        mod_channel = bot.get_channel(MOD_LOG_CHANNEL_ID)
        if mod_channel:
            log_embed = discord.Embed(
                title="🔓 Channel Unlocked",
                color=discord.Color.green(),
                timestamp=datetime.now(timezone.utc)
            )
            log_embed.add_field(name="Channel", value=channel.mention, inline=True)
            log_embed.add_field(name="Unlocked By", value=interaction.user.mention, inline=True)
            await mod_channel.send(embed=log_embed)
    except Exception as e:
        await interaction.response.send_message(f"❌ An error occurred: {str(e)}", ephemeral=True)

@bot.tree.command(name="clear", description="Clear messages", guild=GUILD)
@app_commands.checks.has_permissions(manage_messages=True)
async def clear(interaction: discord.Interaction, amount: int):
    await interaction.response.send_message(f"🧹 Clearing {amount} messages...", ephemeral=True)
    await interaction.channel.purge(limit=amount)

# ======================================================
# 🎉 GIVEAWAY SYSTEM
# ======================================================
@bot.tree.command(name="giveaway", description="Start a giveaway", guild=GUILD)
@app_commands.checks.has_permissions(manage_guild=True)
async def giveaway(interaction: discord.Interaction, duration: int, winners: int, prize: str):
    embed = discord.Embed(
        title="🎉 GIVEAWAY 🎉",
        description=f"**Prize:** {prize}\n**Winners:** {winners}\n**Duration:** {duration} minutes\n\nReact with 🎉 to enter!",
        color=discord.Color.gold(),
        timestamp=datetime.now(timezone.utc) + timedelta(minutes=duration)
    )
    embed.set_footer(text="Ends at")
    
    await interaction.response.send_message("✅ Giveaway started!", ephemeral=True)
    message = await interaction.channel.send(embed=embed)
    await message.add_reaction("🎉")
    
    await asyncio.sleep(duration * 60)
    
    message = await interaction.channel.fetch_message(message.id)
    users = [u async for u in message.reactions[0].users() if not u.bot]
    
    if len(users) < winners:
        await interaction.channel.send(f"❌ Not enough entries! Only {len(users)} user(s) entered.")
        return
    
    winners_list = random.sample(users, winners)
    winner_mentions = ", ".join([w.mention for w in winners_list])
    
    await interaction.channel.send(f"🎊 Congratulations {winner_mentions}! You won **{prize}**!")

@bot.tree.command(name="reroll", description="Reroll a giveaway", guild=GUILD)
@app_commands.checks.has_permissions(manage_guild=True)
async def reroll(interaction: discord.Interaction, message_id: str):
    try:
        message = await interaction.channel.fetch_message(int(message_id))
    except:
        await interaction.response.send_message("❌ Invalid message ID.", ephemeral=True)
        return

    if not message.reactions:
        await interaction.response.send_message("❌ No reactions found.", ephemeral=True)
        return

    users = [u async for u in message.reactions[0].users() if not u.bot]

    if users:
        winner = random.choice(users)
        await interaction.response.send_message(f"🔁 New winner: {winner.mention}")
    else:
        await interaction.response.send_message("❌ No entries.")

# ======================================================
# 📊 POLL SYSTEM
# ======================================================
@bot.tree.command(name="poll", description="Create a poll", guild=GUILD)
async def poll(interaction: discord.Interaction, question: str, option1: str, option2: str, option3: str = None, option4: str = None, option5: str = None):
    options = [option1, option2]
    if option3:
        options.append(option3)
    if option4:
        options.append(option4)
    if option5:
        options.append(option5)
    
    emojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣"]
    
    description = "\n".join([f"{emojis[i]} {opt}" for i, opt in enumerate(options)])
    
    embed = discord.Embed(
        title=f"📊 {question}",
        description=description,
        color=discord.Color.blue(),
        timestamp=datetime.now(timezone.utc)
    )
    embed.set_footer(text=f"Poll by {interaction.user.name}", icon_url=interaction.user.display_avatar.url)
    
    await interaction.response.send_message("✅ Poll created!", ephemeral=True)
    message = await interaction.channel.send(embed=embed)
    
    for i in range(len(options)):
        await message.add_reaction(emojis[i])

# ======================================================
# 🎟 TICKETS
# ======================================================
class TicketCloseView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    
    @discord.ui.button(label="Close Ticket", style=discord.ButtonStyle.red, emoji="🔒")
    async def close_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("🔒 Saving transcript and closing ticket...")
        
        # Create transcript
        messages = []
        async for message in interaction.channel.history(limit=100, oldest_first=True):
            timestamp = message.created_at.strftime("%Y-%m-%d %H:%M:%S")
            messages.append(f"[{timestamp}] {message.author}: {message.content}")
        
        transcript = "\n".join(messages)
        file = discord.File(io.BytesIO(transcript.encode()), filename=f"ticket-{interaction.channel.name}.txt")
        
        # Send transcript to mod log
        mod_channel = interaction.client.get_channel(MOD_LOG_CHANNEL_ID)
        if mod_channel:
            embed = discord.Embed(
                title="🎫 Ticket Closed",
                color=discord.Color.blue(),
                timestamp=datetime.now(timezone.utc)
            )
            embed.add_field(name="Ticket", value=interaction.channel.name, inline=True)
            embed.add_field(name="Closed By", value=interaction.user.mention, inline=True)
            await mod_channel.send(embed=embed, file=file)
        
        await asyncio.sleep(2)
        await interaction.channel.delete()

class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="General Support", style=discord.ButtonStyle.green, emoji="💬")
    async def general(self, interaction: discord.Interaction, _):
        await create_ticket(interaction, "General Support")

    @discord.ui.button(label="Player Report", style=discord.ButtonStyle.red, emoji="📝")
    async def report(self, interaction: discord.Interaction, _):
        await create_ticket(interaction, "Player Report")

    @discord.ui.button(label="Appeal Support", style=discord.ButtonStyle.blurple, emoji="⚖️")
    async def appeal(self, interaction: discord.Interaction, _):
        await create_ticket(interaction, "Appeal Support")

    @discord.ui.button(label="Development Support", style=discord.ButtonStyle.gray, emoji="🛠️")
    async def dev(self, interaction: discord.Interaction, _):
        await create_ticket(interaction, "Development Support")

async def create_ticket(interaction, ticket_type):
    guild = interaction.guild
    category = discord.utils.get(guild.categories, name="Tickets")
    if not category:
        category = await guild.create_category("Tickets")

    # Check if user already has a ticket
    existing_ticket = discord.utils.get(guild.text_channels, name=f"ticket-{interaction.user.id}")
    if existing_ticket:
        await interaction.response.send_message(
            f"❌ You already have an open ticket: {existing_ticket.mention}",
            ephemeral=True
        )
        return

    channel = await guild.create_text_channel(
        f"ticket-{interaction.user.id}",
        category=category,
        overwrites={
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }
    )

    embed = discord.Embed(
        title=f"🎫 {ticket_type}",
        description=f"{interaction.user.mention}\n\nStaff will assist you shortly.\n\nClick the button below to close this ticket.",
        color=discord.Color.green()
    )
    
    await channel.send(embed=embed, view=TicketCloseView())
    await interaction.response.send_message(f"✅ Ticket created: {channel.mention}", ephemeral=True)

@bot.tree.command(name="ticket", description="Open a ticket", guild=GUILD)
async def ticket(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🎫 Kronoz Cafe Support",
        description=(
            "**General Support** – Questions & help\n"
            "**Player Report** – Report rule breakers\n"
            "**Appeal Support** – Ban or timeout appeals\n"
            "**Development Support** – Bugs & suggestions"
        ),
        color=discord.Color.green()
    )
    await interaction.response.send_message(embed=embed, view=TicketView())

@bot.tree.command(name="closeticket", description="Close a ticket (Admin)", guild=GUILD)
@app_commands.checks.has_permissions(manage_channels=True)
async def closeticket(interaction: discord.Interaction):
    if not interaction.channel.name.startswith("ticket-"):
        await interaction.response.send_message("❌ This is not a ticket.", ephemeral=True)
        return
    
    await interaction.response.send_message("🔒 Saving transcript and closing ticket...")
    
    # Create transcript
    messages = []
    async for message in interaction.channel.history(limit=100, oldest_first=True):
        timestamp = message.created_at.strftime("%Y-%m-%d %H:%M:%S")
        messages.append(f"[{timestamp}] {message.author}: {message.content}")
    
    transcript = "\n".join(messages)
    file = discord.File(io.BytesIO(transcript.encode()), filename=f"ticket-{interaction.channel.name}.txt")
    
    # Send transcript to mod log
    mod_channel = bot.get_channel(MOD_LOG_CHANNEL_ID)
    if mod_channel:
        embed = discord.Embed(
            title="🎫 Ticket Closed",
            color=discord.Color.blue(),
            timestamp=datetime.now(timezone.utc)
        )
        embed.add_field(name="Ticket", value=interaction.channel.name, inline=True)
        embed.add_field(name="Closed By", value=interaction.user.mention, inline=True)
        await mod_channel.send(embed=embed, file=file)
    
    await asyncio.sleep(2)
    await interaction.channel.delete()

# ======================================================
# 🧑‍💼 STAFF / UTILITIES
# ======================================================
@bot.tree.command(name="startshift", description="Start a shift", guild=GUILD)
async def startshift(interaction: discord.Interaction):
    await interaction.response.send_message("🟢 Shift started! (logging coming soon)")

@bot.tree.command(name="endshift", description="End a shift", guild=GUILD)
async def endshift(interaction: discord.Interaction):
    await interaction.response.send_message("🔴 Shift ended!")

@bot.tree.command(name="loa", description="Request leave of absence", guild=GUILD)
async def loa(interaction: discord.Interaction, reason: str):
    await interaction.response.send_message(f"📆 **LOA Request Submitted**\nReason: {reason}")

@bot.tree.command(name="serverinfo", description="Server info", guild=GUILD)
async def serverinfo(interaction: discord.Interaction):
    guild = interaction.guild
    
    embed = discord.Embed(
        title=f"🏠 {guild.name}",
        color=discord.Color.blue()
    )
    embed.set_thumbnail(url=guild.icon.url if guild.icon else None)
    embed.add_field(name="Members", value=guild.member_count, inline=True)
    embed.add_field(name="Roles", value=len(guild.roles), inline=True)
    embed.add_field(name="Channels", value=len(guild.channels), inline=True)
    embed.add_field(name="Created", value=f"<t:{int(guild.created_at.timestamp())}:R>", inline=True)
    embed.add_field(name="Owner", value=guild.owner.mention if guild.owner else "Unknown", inline=True)
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="botstatus", description="Bot status", guild=GUILD)
async def botstatus(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🤖 Bot Status",
        color=discord.Color.green()
    )
    embed.add_field(name="Status", value="✅ Operational", inline=True)
    embed.add_field(name="Latency", value=f"{round(bot.latency * 1000)}ms", inline=True)
    embed.add_field(name="Servers", value=len(bot.guilds), inline=True)
    
    await interaction.response.send_message(embed=embed)

# ======================================================
# 🧑‍💼 SIMULATION COMMANDS
# ======================================================
@bot.tree.command(name="warninglogs", description="Simulate warnings for a player", guild=GUILD)
@app_commands.checks.has_permissions(administrator=True)
async def warninglogs(interaction: discord.Interaction, member: discord.Member, amount: int):
    warnings_list = "\n".join([f"⚠️ Warning {i+1}" for i in range(amount)])
    await interaction.response.send_message(f"📄 **Warnings for {member.mention}:**\n{warnings_list}")

@bot.tree.command(name="strikelogs", description="Simulate strikes for a player", guild=GUILD)
@app_commands.checks.has_permissions(administrator=True)
async def strikelogs(interaction: discord.Interaction, member: discord.Member, amount: int):
    strikes = "\n".join([f"❌ Strike {i+1}" for i in range(amount)])
    await interaction.response.send_message(f"📄 **Strikes for {member.mention}:**\n{strikes}")

@bot.tree.command(name="promotelogs", description="Simulate promotion of a player", guild=GUILD)
@app_commands.checks.has_permissions(administrator=True)
async def promotelogs(interaction: discord.Interaction, member: discord.Member, new_role: str):
    await interaction.response.send_message(f"⬆️ **Promotion:** {member.mention} promoted to **{new_role}**.")

@bot.tree.command(name="demotelogs", description="Simulate demotion of a player", guild=GUILD)
@app_commands.checks.has_permissions(administrator=True)
async def demotelogs(interaction: discord.Interaction, member: discord.Member, new_role: str):
    await interaction.response.send_message(f"⬇️ **Demotion:** {member.mention} demoted to **{new_role}**.")

@bot.tree.command(name="loalog", description="Simulate LOA approval", guild=GUILD)
@app_commands.checks.has_permissions(administrator=True)
async def loalog(interaction: discord.Interaction, member: discord.Member, reason: str, days: int):
    await interaction.response.send_message(f"📆 **LOA Approved** for {member.mention}\nReason: {reason}\nDuration: {days} days")

@bot.tree.command(name="shiftlog", description="Simulate shift log for a player", guild=GUILD)
@app_commands.checks.has_permissions(administrator=True)
async def shiftlog(interaction: discord.Interaction, member: discord.Member, shift_type: str):
    if shift_type.lower() not in ["start", "end"]:
        await interaction.response.send_message("❌ Shift type must be `start` or `end`.", ephemeral=True)
        return
    emoji = "🟢" if shift_type.lower() == "start" else "🔴"
    await interaction.response.send_message(f"{emoji} **Shift {shift_type.capitalize()}**: {member.mention}")

# ======================================================
# 🔐 LOGIN
# ======================================================
token = os.getenv("DISCORD_TOKEN")
if not token:
    raise ValueError("❌ DISCORD_TOKEN environment variable not set!")

bot.run(token)