import discord
from discord import app_commands
from discord.ext import commands
import asyncio
from datetime import datetime, timedelta
from config import EMBED_COLOR, DEFAULT_XP_PER_MSG, XP_COOLDOWN
from database import get_db
from utils.rank_card import create_rank_card  # We'll create this next

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

        # Cooldown check
        if key in self.xp_cooldowns:
            if datetime.now() < self.xp_cooldowns[key]:
                return

        self.xp_cooldowns[key] = datetime.now() + timedelta(seconds=XP_COOLDOWN)

        async with await get_db() as db:
            async with db.execute(
                "SELECT xp, level FROM users WHERE user_id = ? AND guild_id = ?",
                (user_id, guild_id)
            ) as cursor:
                row = await cursor.fetchone()

            if row is None:
                # New user
                await db.execute(
                    "INSERT INTO users (user_id, guild_id, xp, level) VALUES (?, ?, ?, ?)",
                    (user_id, guild_id, DEFAULT_XP_PER_MSG, 1)
                )
                current_xp = DEFAULT_XP_PER_MSG
                current_level = 1
            else:
                current_xp = row[0] + DEFAULT_XP_PER_MSG
                current_level = row[1]

                # Check for level up
                needed_xp = self._xp_for_level(current_level + 1)
                if current_xp >= needed_xp:
                    current_level += 1
                    current_xp = current_xp - needed_xp + 10  # Carry over some XP

                    # Level up announcement
                    embed = discord.Embed(
                        title="🎉 Level Up!",
                        description=f"{message.author.mention} reached **Level {current_level}**!",
                        color=EMBED_COLOR
                    )
                    await message.channel.send(embed=embed)

            # Save progress
            await db.execute(
                "INSERT OR REPLACE INTO users (user_id, guild_id, xp, level) VALUES (?, ?, ?, ?)",
                (user_id, guild_id, current_xp, current_level)
            )
            await db.commit()

    def _xp_for_level(self, level: int) -> int:
        """Simple progressive XP formula"""
        return int(100 * (level ** 1.5))

    @app_commands.command(name="rank", description="Show your current level and XP")
    async def rank(self, interaction: discord.Interaction):
        async with await get_db() as db:
            async with db.execute(
                "SELECT xp, level FROM users WHERE user_id = ? AND guild_id = ?",
                (interaction.user.id, interaction.guild.id)
            ) as cursor:
                row = await cursor.fetchone()

        if not row:
            embed = discord.Embed(description="You have no XP yet. Start chatting!", color=0xED4245)
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        xp, level = row
        next_level_xp = self._xp_for_level(level + 1)
        progress = (xp / next_level_xp) * 100

        # For now, simple embed. We'll improve with image rank card soon.
        embed = discord.Embed(title=f"{interaction.user.display_name}'s Rank", color=EMBED_COLOR)
        embed.add_field(name="Level", value=f"**{level}**", inline=True)
        embed.add_field(name="XP", value=f"{xp}/{next_level_xp}", inline=True)
        embed.add_field(name="Progress", value=f"{progress:.1f}%", inline=True)
        embed.set_thumbnail(url=interaction.user.display_avatar.url)

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="leaderboard", description="View server leaderboard")
    async def leaderboard(self, interaction: discord.Interaction):
        async with await get_db() as db:
            async with db.execute(
                "SELECT user_id, xp, level FROM users WHERE guild_id = ? ORDER BY level DESC, xp DESC LIMIT 10",
                (interaction.guild.id,)
            ) as cursor:
                rows = await cursor.fetchall()

        if not rows:
            return await interaction.response.send_message("No data yet!")

        desc = ""
        for i, (user_id, xp, level) in enumerate(rows, 1):
            member = interaction.guild.get_member(user_id)
            name = member.display_name if member else f"User {user_id}"
            desc += f"`{i:2}.` **{name}** — Level {level} ({xp} XP)\n"

        embed = discord.Embed(title="🏆 Server Leaderboard", description=desc, color=EMBED_COLOR)
        await interaction.response.send_message(embed=embed)


async def setup(bot):
    await bot.add_cog(Levels(bot))