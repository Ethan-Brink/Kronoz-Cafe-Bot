import discord
from discord.ext import commands, tasks
from discord import app_commands
import asyncio
import random
import os
from datetime import datetime, timedelta, timezone
import json

# ======================================================
# ⚙️ CONFIG
# ======================================================
GUILD_ID = 1441171105397346508
COUNTING_CHANNEL_ID = 1441204274964201664
MOD_LOG_CHANNEL_ID = 1455167564534513836
ANNOUNCEMENTS_CHANNEL_ID = 1441171167263068301
MAX_WARNINGS = 3

# ======================================================
# 🔧 INTENTS
# ======================================================
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True

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
        self.last_countdown_message = None

    async def setup_hook(self):
        guild = discord.Object(id=GUILD_ID)
        await self.tree.sync(guild=guild)
        print("✅ Commands synced")
        new_year_countdown.start()

    async def on_ready(self):
        print(f"☕ Kronoz Cafe online as {self.user}")

    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return

        if message.channel.id == COUNTING_CHANNEL_ID:
            await handle_counting(message)

        await self.process_commands(message)

bot = KronozCafe()
GUILD = discord.Object(id=GUILD_ID)

# ======================================================
# 🎆 NEW YEAR COUNTDOWN
# ======================================================
@tasks.loop(minutes=1)
async def new_year_countdown():
    channel = bot.get_channel(ANNOUNCEMENTS_CHANNEL_ID)
    if not channel:
        return

    now = datetime.now(timezone.utc)
    new_year = datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    
    if now >= new_year:
        await channel.send("🎊 **HAPPY NEW YEAR 2026!** 🎉")
        new_year_countdown.stop()
        return
    
    time_left = new_year - now
    hours_left = int(time_left.total_seconds() / 3600)
    major_hours = [24, 12, 6, 3, 2, 1]
    minutes_left = int(time_left.total_seconds() / 60)
    
    if hours_left in major_hours and minutes_left % 60 == 0:
        if bot.last_countdown_message:
            try:
                await bot.last_countdown_message.delete()
            except:
                pass
        
        timestamp = f"<t:{int(new_year.timestamp())}:R>"
        embed = discord.Embed(
            title="🎆 New Year Countdown",
            description=f"**{hours_left} hours** until 2026!\n\nNew Year arrives {timestamp}",
            color=discord.Color.gold()
        )
        embed.set_footer(text="The timestamp shows in your local timezone!")
        bot.last_countdown_message = await channel.send(embed=embed)

@new_year_countdown.before_loop
async def before_countdown():
    await bot.wait_until_ready()

# ======================================================
# ❌ ERROR HANDLING
# ======================================================
@bot.tree.error
async def on_app_command_error(interaction, error):
    if interaction.response.is_done():
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
    
    # Initialize member's warning list if not exists
    if member_id not in warnings_data:
        warnings_data[member_id] = []
    
    # Check if member already has 3 warnings
    if len(warnings_data[member_id]) >= MAX_WARNINGS:
        await interaction.response.send_message(
            f"❌ **Cannot issue warning!**\n"
            f"{member.mention} already has **{MAX_WARNINGS} warnings** (maximum reached).\n"
            f"Consider taking further action instead of issuing more warnings.",
            ephemeral=True
        )
        return
    
    # Add the warning
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
    
    # Create response embed
    embed = discord.Embed(
        title="⚠️ Warning Issued",
        color=discord.Color.orange() if warning_count < MAX_WARNINGS else discord.Color.red()
    )
    embed.add_field(name="Member", value=member.mention, inline=True)
    embed.add_field(name="Warning #", value=f"{warning_count}/{MAX_WARNINGS}", inline=True)
    embed.add_field(name="Reason", value=reason, inline=False)
    embed.set_footer(text=f"Issued by {interaction.user}")
    
    # Add warning level message
    if warning_count == MAX_WARNINGS:
        embed.add_field(
            name="⚠️ MAXIMUM WARNINGS REACHED",
            value=f"{member.mention} has reached the maximum of {MAX_WARNINGS} warnings!",
            inline=False
        )
    
    await interaction.response.send_message(embed=embed)
    
    # Log to mod channel
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
    
    # Log to mod channel
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

@bot.tree.command(name="clear", description="Clear messages", guild=GUILD)
@app_commands.checks.has_permissions(manage_messages=True)
async def clear(interaction: discord.Interaction, amount: int):
    await interaction.channel.purge(limit=amount)
    await interaction.response.send_message(f"🧹 Cleared {amount} messages.", ephemeral=True)

# ======================================================
# 🎟 TICKETS
# ======================================================
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

    channel = await guild.create_text_channel(
        f"ticket-{interaction.user.id}",
        category=category,
        overwrites={
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True),
            guild.me: discord.PermissionOverwrite(read_messages=True)
        }
    )

    await channel.send(
        f"🎫 {interaction.user.mention}\n"
        f"**Ticket Type:** {ticket_type}\n"
        f"Staff will assist you shortly."
    )

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

@bot.tree.command(name="closeticket", description="Close a ticket", guild=GUILD)
async def closeticket(interaction: discord.Interaction):
    if not interaction.channel.name.startswith("ticket-"):
        await interaction.response.send_message("❌ This is not a ticket.", ephemeral=True)
        return
    await interaction.response.send_message("🔒 Closing ticket...")
    await asyncio.sleep(2)
    await interaction.channel.delete()

# ======================================================
# 🎉 GIVEAWAYS
# ======================================================
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
    await interaction.response.send_message(f"🏠 **{guild.name}**\nMembers: {guild.member_count}")

@bot.tree.command(name="botstatus", description="Bot status", guild=GUILD)
async def botstatus(interaction: discord.Interaction):
    await interaction.response.send_message("🤖 KronozCafeBot is fully operational.")

# ======================================================
# 🧑‍💼 SIMULATION COMMANDS
# ======================================================
@bot.tree.command(name="warninglogs", description="Simulate warnings for a player", guild=GUILD)
@app_commands.checks.has_permissions(administrator=True)
async def warninglogs(interaction: discord.Interaction, member: discord.Member, amount: int):
    warnings = "\n".join([f"⚠️ Warning {i+1}" for i in range(amount)])
    await interaction.response.send_message(f"📄 **Warnings for {member.mention}:**\n{warnings}")

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