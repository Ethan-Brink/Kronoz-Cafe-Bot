# cogs/advanced_features.py - Advanced Moderation & Utility
import discord
from discord.ext import commands, tasks
from discord import app_commands
import asyncio
from datetime import datetime, timedelta
from typing import Optional
import re

class AdvancedFeatures(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.suggestion_channel = None  # Set in config
        self.giveaway_active = {}
        self.auto_role_enabled = True
    
    # 18. SUGGESTION SYSTEM
    @app_commands.command(name="suggest", description="Submit a suggestion for the cafe")
    @app_commands.describe(suggestion="Your suggestion")
    async def suggest(self, interaction: discord.Interaction, suggestion: str):
        if len(suggestion) < 10:
            await interaction.response.send_message("❌ Suggestion must be at least 10 characters!", ephemeral=True)
            return
        
        # Store suggestion
        self.bot.db.execute(
            "INSERT INTO suggestions (user_id, suggestion, created_at, status) VALUES (?, ?, ?, ?)",
            (interaction.user.id, suggestion, datetime.utcnow().isoformat(), "pending")
        )
        suggestion_id = self.bot.db.execute("SELECT last_insert_rowid()").fetchone()[0]
        
        # Create suggestion embed
        embed = discord.Embed(
            title="💡 New Suggestion",
            description=suggestion,
            color=discord.Color.blue()
        )
        embed.set_author(name=interaction.user.display_name, icon_url=interaction.user.display_avatar.url)
        embed.set_footer(text=f"Suggestion ID: {suggestion_id}")
        embed.timestamp = datetime.utcnow()
        
        # Try to send to suggestion channel
        try:
            if self.suggestion_channel:
                channel = self.bot.get_channel(self.suggestion_channel)
                if channel:
                    msg = await channel.send(embed=embed)
                    await msg.add_reaction("👍")
                    await msg.add_reaction("👎")
            else:
                # Send in current channel if no suggestion channel set
                msg = await interaction.channel.send(embed=embed)
                await msg.add_reaction("👍")
                await msg.add_reaction("👎")
        except:
            pass
        
        await interaction.response.send_message("✅ Your suggestion has been submitted!", ephemeral=True)
    
    # 19. GIVEAWAY SYSTEM
    @app_commands.command(name="giveaway", description="Start a giveaway (Staff only)")
    @app_commands.describe(
        duration="Duration in minutes",
        winners="Number of winners",
        prize="What you're giving away"
    )
    @app_commands.checks.has_permissions(manage_guild=True)
    async def giveaway(self, interaction: discord.Interaction, duration: int, winners: int, prize: str):
        if duration < 1 or duration > 10080:  # Max 1 week
            await interaction.response.send_message("❌ Duration must be between 1 minute and 1 week!", ephemeral=True)
            return
        
        if winners < 1 or winners > 20:
            await interaction.response.send_message("❌ Number of winners must be between 1 and 20!", ephemeral=True)
            return
        
        end_time = datetime.utcnow() + timedelta(minutes=duration)
        
        embed = discord.Embed(
            title="🎉 GIVEAWAY!",
            description=f"**Prize:** {prize}\n**Winners:** {winners}\n**Ends:** <t:{int(end_time.timestamp())}:R>",
            color=discord.Color.green()
        )
        embed.set_footer(text="React with 🎉 to enter!")
        
        await interaction.response.send_message(embed=embed)
        msg = await interaction.original_response()
        await msg.add_reaction("🎉")
        
        # Store giveaway
        self.giveaway_active[msg.id] = {
            "prize": prize,
            "winners": winners,
            "end_time": end_time,
            "channel_id": interaction.channel.id
        }
        
        # Wait for giveaway to end
        await asyncio.sleep(duration * 60)
        await self.end_giveaway(msg.id)
    
    async def end_giveaway(self, message_id: int):
        if message_id not in self.giveaway_active:
            return
        
        giveaway = self.giveaway_active[message_id]
        channel = self.bot.get_channel(giveaway["channel_id"])
        
        try:
            message = await channel.fetch_message(message_id)
            reaction = discord.utils.get(message.reactions, emoji="🎉")
            
            if not reaction or reaction.count <= 1:  # Only bot reacted
                embed = discord.Embed(
                    title="🎉 Giveaway Ended",
                    description=f"**Prize:** {giveaway['prize']}\n\n❌ Not enough participants!",
                    color=discord.Color.red()
                )
                await channel.send(embed=embed)
            else:
                # Get users who reacted
                users = [user async for user in reaction.users() if not user.bot]
                
                if len(users) < giveaway["winners"]:
                    winners = users
                else:
                    import random
                    winners = random.sample(users, giveaway["winners"])
                
                winner_mentions = ", ".join([user.mention for user in winners])
                
                embed = discord.Embed(
                    title="🎉 Giveaway Ended!",
                    description=f"**Prize:** {giveaway['prize']}\n\n**Winner(s):** {winner_mentions}",
                    color=discord.Color.gold()
                )
                
                await channel.send(embed=embed)
                
                # DM winners
                for winner in winners:
                    try:
                        dm_embed = discord.Embed(
                            title="🎉 Congratulations!",
                            description=f"You won the giveaway for **{giveaway['prize']}**!",
                            color=discord.Color.gold()
                        )
                        await winner.send(embed=dm_embed)
                    except:
                        pass
        
        except Exception as e:
            print(f"Error ending giveaway: {e}")
        
        finally:
            del self.giveaway_active[message_id]
    
    # 20. AFK SYSTEM
    @app_commands.command(name="afk", description="Set yourself as AFK")
    @app_commands.describe(reason="Why you're AFK (optional)")
    async def afk(self, interaction: discord.Interaction, reason: Optional[str] = "AFK"):
        self.bot.db.execute(
            "INSERT INTO afk_users (user_id, reason, since) VALUES (?, ?, ?) ON CONFLICT(user_id) DO UPDATE SET reason = ?, since = ?",
            (interaction.user.id, reason, datetime.utcnow().isoformat(), reason, datetime.utcnow().isoformat())
        )
        
        embed = discord.Embed(
            description=f"💤 {interaction.user.mention} is now AFK: {reason}",
            color=discord.Color.blue()
        )
        
        await interaction.response.send_message(embed=embed)
    
    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return
        
        # Check if user is AFK and mentioned
        for mention in message.mentions:
            afk_data = self.bot.db.execute(
                "SELECT reason, since FROM afk_users WHERE user_id = ?",
                (mention.id,)
            ).fetchone()
            
            if afk_data:
                reason, since = afk_data
                since_dt = datetime.fromisoformat(since)
                time_ago = datetime.utcnow() - since_dt
                
                hours = int(time_ago.total_seconds() // 3600)
                minutes = int((time_ago.total_seconds() % 3600) // 60)
                
                time_str = f"{hours}h {minutes}m ago" if hours > 0 else f"{minutes}m ago"
                
                await message.reply(
                    f"💤 {mention.display_name} is currently AFK: {reason} ({time_str})",
                    mention_author=False
                )
        
        # Remove AFK status if user sends message
        afk_check = self.bot.db.execute(
            "SELECT user_id FROM afk_users WHERE user_id = ?",
            (message.author.id,)
        ).fetchone()
        
        if afk_check:
            self.bot.db.execute("DELETE FROM afk_users WHERE user_id = ?", (message.author.id,))
            
            try:
                await message.reply(
                    f"👋 Welcome back {message.author.mention}! I removed your AFK status.",
                    mention_author=False,
                    delete_after=5
                )
            except:
                pass
    
    # 21. ANNOUNCEMENT COMMAND
    @app_commands.command(name="announce", description="Create a stylish announcement (Staff only)")
    @app_commands.describe(
        title="Announcement title",
        message="Announcement message",
        ping_role="Role to ping (optional)"
    )
    @app_commands.checks.has_permissions(manage_messages=True)
    async def announce(
        self, 
        interaction: discord.Interaction, 
        title: str, 
        message: str,
        ping_role: Optional[discord.Role] = None
    ):
        embed = discord.Embed(
            title=f"📢 {title}",
            description=message,
            color=discord.Color.blue()
        )
        embed.set_footer(text=f"Announced by {interaction.user.display_name}")
        embed.timestamp = datetime.utcnow()
        
        content = ping_role.mention if ping_role else None
        
        await interaction.response.send_message(content, embed=embed)
    
    # 22. CLEAR MESSAGES (Enhanced)
    @app_commands.command(name="purge", description="Delete multiple messages (Staff only)")
    @app_commands.describe(
        amount="Number of messages to delete (1-100)",
        user="Only delete messages from this user (optional)"
    )
    @app_commands.checks.has_permissions(manage_messages=True)
    async def purge(
        self, 
        interaction: discord.Interaction, 
        amount: int,
        user: Optional[discord.Member] = None
    ):
        if amount < 1 or amount > 100:
            await interaction.response.send_message("❌ Amount must be between 1 and 100!", ephemeral=True)
            return
        
        await interaction.response.defer(ephemeral=True)
        
        def check(m):
            if user:
                return m.author == user
            return True
        
        deleted = await interaction.channel.purge(limit=amount, check=check)
        
        embed = discord.Embed(
            title="🗑️ Messages Purged",
            description=f"Deleted {len(deleted)} message(s)" + (f" from {user.mention}" if user else ""),
            color=discord.Color.green()
        )
        
        await interaction.followup.send(embed=embed, ephemeral=True)
    
    # 23. SLOWMODE
    @app_commands.command(name="slowmode", description="Set channel slowmode (Staff only)")
    @app_commands.describe(seconds="Slowmode delay in seconds (0 to disable)")
    @app_commands.checks.has_permissions(manage_channels=True)
    async def slowmode(self, interaction: discord.Interaction, seconds: int):
        if seconds < 0 or seconds > 21600:  # Max 6 hours
            await interaction.response.send_message("❌ Slowmode must be between 0 and 21600 seconds (6 hours)!", ephemeral=True)
            return
        
        await interaction.channel.edit(slowmode_delay=seconds)
        
        if seconds == 0:
            embed = discord.Embed(
                description="✅ Slowmode disabled",
                color=discord.Color.green()
            )
        else:
            embed = discord.Embed(
                description=f"✅ Slowmode set to {seconds} second(s)",
                color=discord.Color.green()
            )
        
        await interaction.response.send_message(embed=embed)
    
    # 24. LOCKDOWN CHANNEL
    @app_commands.command(name="lock", description="Lock a channel (Staff only)")
    @app_commands.describe(reason="Reason for locking")
    @app_commands.checks.has_permissions(manage_channels=True)
    async def lock(self, interaction: discord.Interaction, reason: str = "No reason provided"):
        overwrite = interaction.channel.overwrites_for(interaction.guild.default_role)
        overwrite.send_messages = False
        await interaction.channel.set_permissions(interaction.guild.default_role, overwrite=overwrite)
        
        embed = discord.Embed(
            title="🔒 Channel Locked",
            description=f"This channel has been locked.\n**Reason:** {reason}",
            color=discord.Color.red()
        )
        embed.set_footer(text=f"Locked by {interaction.user.display_name}")
        
        await interaction.response.send_message(embed=embed)
    
    # 25. UNLOCK CHANNEL
    @app_commands.command(name="unlock", description="Unlock a channel (Staff only)")
    @app_commands.checks.has_permissions(manage_channels=True)
    async def unlock(self, interaction: discord.Interaction):
        overwrite = interaction.channel.overwrites_for(interaction.guild.default_role)
        overwrite.send_messages = None
        await interaction.channel.set_permissions(interaction.guild.default_role, overwrite=overwrite)
        
        embed = discord.Embed(
            title="🔓 Channel Unlocked",
            description="This channel has been unlocked.",
            color=discord.Color.green()
        )
        embed.set_footer(text=f"Unlocked by {interaction.user.display_name}")
        
        await interaction.response.send_message(embed=embed)
    
    # 26. EMBED CREATOR
    @app_commands.command(name="embed", description="Create a custom embed (Staff only)")
    @app_commands.describe(
        title="Embed title",
        description="Embed description",
        color="Color (hex code like #FF0000)"
    )
    @app_commands.checks.has_permissions(manage_messages=True)
    async def create_embed(
        self, 
        interaction: discord.Interaction, 
        title: str,
        description: str,
        color: Optional[str] = None
    ):
        # Parse color
        embed_color = discord.Color.blue()
        if color:
            try:
                color = color.replace("#", "")
                embed_color = discord.Color(int(color, 16))
            except:
                pass
        
        embed = discord.Embed(
            title=title,
            description=description,
            color=embed_color
        )
        
        await interaction.response.send_message(embed=embed)
    
    # 27. AVATAR COMMAND
    @app_commands.command(name="avatar", description="Get a user's avatar")
    @app_commands.describe(user="User to get avatar from (optional)")
    async def avatar(self, interaction: discord.Interaction, user: Optional[discord.Member] = None):
        target = user or interaction.user
        
        embed = discord.Embed(
            title=f"{target.display_name}'s Avatar",
            color=discord.Color.blue()
        )
        embed.set_image(url=target.display_avatar.url)
        
        # Add download link
        embed.add_field(
            name="Links",
            value=f"[PNG]({target.display_avatar.replace(format='png', size=1024).url}) | "
                  f"[JPG]({target.display_avatar.replace(format='jpg', size=1024).url}) | "
                  f"[WEBP]({target.display_avatar.replace(format='webp', size=1024).url})",
            inline=False
        )
        
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(AdvancedFeatures(bot))