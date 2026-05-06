import discord
from discord import app_commands
from discord.ext import commands
from config import EMBED_COLOR, ERROR, SUCCESS, OWNER_ID
from database import get_db


class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ====================== WARNING SYSTEM ======================
    @app_commands.command(name="warn", description="Warn a user")
    @app_commands.describe(member="The member to warn", reason="Reason for the warning")
    @app_commands.default_permissions(manage_messages=True)
    async def warn(self, interaction: discord.Interaction, member: discord.Member, reason: str):
        if member.id == interaction.user.id:
            return await interaction.response.send_message("You cannot warn yourself!", ephemeral=True)
        if member.top_role >= interaction.user.top_role and interaction.user.id != OWNER_ID:
            return await interaction.response.send_message("You cannot warn someone with equal or higher role!", ephemeral=True)

        async with await get_db() as db:
            await db.execute(
                "UPDATE users SET warnings = warnings + 1 WHERE user_id = ? AND guild_id = ?",
                (member.id, interaction.guild.id)
            )
            await db.execute(
                "INSERT OR IGNORE INTO users (user_id, guild_id) VALUES (?, ?)",
                (member.id, interaction.guild.id)
            )
            await db.commit()

            async with db.execute(
                "SELECT warnings FROM users WHERE user_id = ? AND guild_id = ?",
                (member.id, interaction.guild.id)
            ) as cursor:
                row = await cursor.fetchone()
                warnings = row[0] if row else 1

        # DM the user
        try:
            embed_dm = discord.Embed(
                title="⚠️ You Received a Warning",
                description=f"You have been warned in **{interaction.guild.name}**",
                color=ERROR
            )
            embed_dm.add_field(name="Reason", value=reason, inline=False)
            embed_dm.add_field(name="Total Warnings", value=f"{warnings}/5", inline=False)
            embed_dm.set_footer(text="Further violations may result in more severe punishment.")
            await member.send(embed=embed_dm)
        except:
            pass  # User has DMs closed

        # Log in channel
        embed = discord.Embed(
            title="⚠️ User Warned",
            color=ERROR
        )
        embed.add_field(name="User", value=f"{member.mention} (`{member.id}`)", inline=False)
        embed.add_field(name="Moderator", value=interaction.user.mention, inline=False)
        embed.add_field(name="Reason", value=reason, inline=False)
        embed.add_field(name="Total Warnings", value=str(warnings), inline=False)

        await interaction.response.send_message(embed=embed)

    # ====================== OTHER MOD COMMANDS ======================
    @app_commands.command(name="kick", description="Kick a member")
    @app_commands.default_permissions(kick_members=True)
    async def kick(self, interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided"):
        await member.kick(reason=reason)
        embed = discord.Embed(title="👢 Member Kicked", description=f"{member.mention} has been kicked.", color=ERROR)
        embed.add_field(name="Reason", value=reason)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="ban", description="Ban a member")
    @app_commands.default_permissions(ban_members=True)
    async def ban(self, interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided"):
        await member.ban(reason=reason)
        embed = discord.Embed(title="🔨 Member Banned", description=f"{member.mention} has been banned.", color=ERROR)
        embed.add_field(name="Reason", value=reason)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="timeout", description="Timeout a member")
    @app_commands.default_permissions(moderate_members=True)
    async def timeout(self, interaction: discord.Interaction, member: discord.Member, minutes: int, reason: str = "No reason provided"):
        delta = discord.utils.utcnow() + timedelta(minutes=minutes)
        await member.timeout(delta, reason=reason)
        embed = discord.Embed(title="⏳ Member Timed Out", color=ERROR)
        embed.add_field(name="User", value=member.mention)
        embed.add_field(name="Duration", value=f"{minutes} minutes")
        embed.add_field(name="Reason", value=reason)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="warnings", description="Check warnings for a user")
    @app_commands.default_permissions(manage_messages=True)
    async def warnings(self, interaction: discord.Interaction, member: discord.Member):
        async with await get_db() as db:
            async with db.execute(
                "SELECT warnings FROM users WHERE user_id = ? AND guild_id = ?",
                (member.id, interaction.guild.id)
            ) as cursor:
                row = await cursor.fetchone()
                warnings = row[0] if row else 0

        embed = discord.Embed(
            title=f"Warnings for {member.display_name}",
            description=f"**{warnings}** warning(s)",
            color=EMBED_COLOR if warnings < 3 else ERROR
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="clearwarnings", description="Clear warnings for a user")
    @app_commands.default_permissions(manage_messages=True)
    async def clearwarnings(self, interaction: discord.Interaction, member: discord.Member):
        async with await get_db() as db:
            await db.execute(
                "UPDATE users SET warnings = 0 WHERE user_id = ? AND guild_id = ?",
                (member.id, interaction.guild.id)
            )
            await db.commit()

        await interaction.response.send_message(f"✅ Cleared all warnings for {member.mention}", ephemeral=True)


async def setup(bot):
    await bot.add_cog(Moderation(bot))