import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime, timedelta
from config import EMBED_COLOR, DEFAULT_XP_PER_MSG, XP_COOLDOWN
from database import get_db


class Levels(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.xp_cooldowns = {}

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return

        user_id = message.author.id
        guild_id = message.guild.id
        key = f"{user_id}-{guild_id}"

        # Cooldown
        if key in self.xp_cooldowns and datetime.now() < self.xp_cooldowns[key]:
            return
        self.xp_cooldowns[key] = datetime.now() + timedelta(seconds=XP_COOLDOWN)

        async with await get_db() as db:
            async with db.execute(
                "SELECT xp, level FROM users WHERE user_id = ? AND guild_id = ?",
                (user_id, guild_id)
            ) as cursor:
                row = await cursor.fetchone()

            if row is None:
                current_xp = DEFAULT_XP_PER_MSG
                current_level = 1
            else:
                current_xp = row[0] + DEFAULT_XP_PER_MSG
                current_level = row[1]

            # Level up check
            needed = self._xp_for_level(current_level + 1)
            if current_xp >= needed:
                current_level += 1
                current_xp = current_xp - needed + 10
                embed = discord.Embed(title="🎉 Level Up!", 
                                    description=f"{message.author.mention} is now **Level {current_level}**!", 
                                    color=EMBED_COLOR)
                await message.channel.send(embed=embed)

            await db.execute(
                "INSERT OR REPLACE INTO users (user_id, guild_id, xp, level) VALUES (?, ?, ?, ?)",
                (user_id, guild_id, current_xp, current_level)
            )
            await db.commit()

    def _xp_for_level(self, level: int) -> int:
        return int(100 * (level ** 1.5))

    @app_commands.command(name="rank", description="Show your rank card")
    async def rank(self, interaction: discord.Interaction):
        async with await get_db() as db:
            async with db.execute(
                "SELECT xp, level FROM users WHERE user_id = ? AND guild_id = ?",
                (interaction.user.id, interaction.guild.id)
            ) as cursor:
                row = await cursor.fetchone()

        if not row:
            return await interaction.response.send_message("You haven't earned any XP yet. Chat more!", ephemeral=True)

        xp, level = row
        next_xp = self._xp_for_level(level + 1)

        embed = discord.Embed(title=f"{interaction.user.display_name}'s Rank", color=EMBED_COLOR)
        embed.add_field(name="Level", value=level, inline=True)
        embed.add_field(name="XP", value=f"{xp}/{next_xp}", inline=True)
        embed.set_thumbnail(url=interaction.user.display_avatar.url)

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="leaderboard", description="Server leaderboard")
    async def leaderboard(self, interaction: discord.Interaction):
        async with await get_db() as db:
            async with db.execute(
                """SELECT user_id, xp, level 
                   FROM users 
                   WHERE guild_id = ? 
                   ORDER BY level DESC, xp DESC LIMIT 10""",
                (interaction.guild.id,)
            ) as cursor:
                rows = await cursor.fetchall()

        if not rows:
            return await interaction.response.send_message("No data yet!")

        desc = "\n".join([f"`{i:2}.` **{interaction.guild.get_member(uid).display_name if interaction.guild.get_member(uid) else 'Unknown'}** — Lv.{lvl} ({xp}xp)" 
                         for i, (uid, xp, lvl) in enumerate(rows, 1)])

        embed = discord.Embed(title="🏆 Leaderboard", description=desc, color=EMBED_COLOR)
        await interaction.response.send_message(embed=embed)


async def setup(bot):
    await bot.add_cog(Levels(bot))