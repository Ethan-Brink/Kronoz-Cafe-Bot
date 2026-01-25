# cogs/moderation.py - Moderation Commands
import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime, timedelta, timezone
from config import *

class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    async def send_punishment_dm(self, user: discord.User, punishment_type: str, 
                               reason: str, moderator: discord.User, 
                               expires_at: datetime = None):
        """Send punishment notification to user via DM"""
        embed = discord.Embed(
            title=f"⚠️ {punishment_type.replace('_', ' ').title()} - Kronoz Cafe",
            description=f"You have received a **{punishment_type.replace('_', ' ')}** in Kronoz Cafe Discord server.",
            color=COLORS["error"],
            timestamp=datetime.now(timezone.utc)
        )
        
        embed.add_field(name="📋 Reason", value=reason, inline=False)
        embed.add_field(name="👮 Moderator", value=f"{moderator.name}", inline=True)
        embed.add_field(name="📅 Date", value=f"<t:{int(datetime.now(timezone.utc).timestamp())}:F>", inline=True)
        
        if expires_at:
            embed.add_field(name="⏰ Expires", value=f"<t:{int(expires_at.timestamp())}:R>", inline=True)
        
        if punishment_type in ["ban", "kick", "warn"]:
            embed.add_field(
                name="📝 Appeal",
                value="You can submit an appeal by opening a ticket in the server using `/ticket` and selecting the 'Appeal' category.",
                inline=False
            )
        
        embed.set_footer(text="Kronoz Cafe Moderation Team | This is an automated message")
        
        await self.bot.send_dm_with_fallback(user, embed)
    
    async def check_auto_punishment(self, user_id: int, moderator: discord.User, 
                                   guild: discord.Guild):
        """Check and apply auto-escalation punishments"""
        verbal_warns = self.bot.db.get_punishment_count(user_id, "verbal_warn")
        warns = self.bot.db.get_punishment_count(user_id, "warn")
        kicks = self.bot.db.get_punishment_count(user_id, "kick")
        
        member = guild.get_member(user_id)
        if not member:
            return
        
        # 3 verbal warns = formal warn
        if verbal_warns >= PUNISHMENT_THRESHOLDS["verbal_warns"]:
            self.bot.db.add_punishment(user_id, "warn", 
                                      f"Auto-escalation: {PUNISHMENT_THRESHOLDS['verbal_warns']} verbal warnings", 
                                      moderator.id)
            await self.send_punishment_dm(
                member, "warn", 
                f"Auto-escalation: You have accumulated {PUNISHMENT_THRESHOLDS['verbal_warns']} verbal warnings", 
                moderator
            )
            
            # Clear verbal warns
            for punishment in self.bot.db.get_active_punishments(user_id, "verbal_warn"):
                self.bot.db.remove_punishment(punishment[0], moderator.id)
            
            # Log to mod channel
            await self.log_auto_escalation(member, "verbal_warn", "warn", moderator)
            
            # Recheck warns
            warns = self.bot.db.get_punishment_count(user_id, "warn")
        
        # 3 warns = kick
        if warns >= PUNISHMENT_THRESHOLDS["warns"]:
            try:
                await member.kick(reason=f"Auto-escalation: {PUNISHMENT_THRESHOLDS['warns']} formal warnings")
                self.bot.db.add_punishment(user_id, "kick", 
                                          f"Auto-escalation: {PUNISHMENT_THRESHOLDS['warns']} formal warnings", 
                                          moderator.id)
                await self.send_punishment_dm(
                    member, "kick", 
                    f"Auto-escalation: You have accumulated {PUNISHMENT_THRESHOLDS['warns']} formal warnings", 
                    moderator
                )
                await self.log_auto_escalation(member, "warn", "kick", moderator)
                
                # Recheck kicks
                kicks = self.bot.db.get_punishment_count(user_id, "kick")
            except discord.Forbidden:
                pass
        
        # 2 kicks = ban
        if kicks >= PUNISHMENT_THRESHOLDS["kicks"]:
            try:
                await member.ban(reason=f"Auto-escalation: {PUNISHMENT_THRESHOLDS['kicks']} kicks")
                self.bot.db.add_punishment(user_id, "ban", 
                                          f"Auto-escalation: {PUNISHMENT_THRESHOLDS['kicks']} kicks", 
                                          moderator.id)
                await self.send_punishment_dm(
                    member, "ban", 
                    f"Auto-escalation: You have been kicked {PUNISHMENT_THRESHOLDS['kicks']} times", 
                    moderator
                )
                await self.log_auto_escalation(member, "kick", "ban", moderator)
            except discord.Forbidden:
                pass
    
    async def log_auto_escalation(self, member: discord.Member, from_type: str, 
                                 to_type: str, moderator: discord.User):
        """Log auto-escalation to mod channel"""
        mod_channel = self.bot.get_channel(MOD_LOG_CHANNEL_ID)
        if mod_channel:
            embed = discord.Embed(
                title="🔄 Auto-Escalation Triggered",
                description=f"{member.mention} has been auto-escalated from **{from_type}** to **{to_type}**",
                color=COLORS["warning"],
                timestamp=datetime.now(timezone.utc)
            )
            embed.add_field(name="User", value=f"{member.mention} ({member.id})", inline=True)
            embed.add_field(name="Threshold Met", value=f"{PUNISHMENT_THRESHOLDS.get(from_type + 's', 'N/A')} {from_type}s", inline=True)
            await mod_channel.send(embed=embed)
    
    # ===== VERBAL WARN =====
    @app_commands.command(name="verbalwarn", description="Issue a verbal warning to a user")
    @app_commands.checks.has_permissions(moderate_members=True)
    @app_commands.describe(
        user="Member to warn OR User ID",
        reason="Reason for warning"
    )
    async def verbalwarn(self, interaction: discord.Interaction, 
                        user: str, reason: str):
        """Issue verbal warning - accepts member mention or user ID"""
        # Try to parse as user ID
        try:
            user_id = int(user.strip('<@!>'))
        except ValueError:
            await interaction.response.send_message("❌ Invalid user format! Use @mention or user ID", ephemeral=True)
            return
        
        # Try to get as member
        member = interaction.guild.get_member(user_id)
        
        # Get user object
        try:
            user_obj = await self.bot.fetch_user(user_id)
        except discord.NotFound:
            await interaction.response.send_message("❌ User not found!", ephemeral=True)
            return
        
        if user_obj.bot:
            await interaction.response.send_message("❌ Cannot warn bots!", ephemeral=True)
            return
        
        if member and member.top_role >= interaction.user.top_role and interaction.user.id != interaction.guild.owner_id:
            await interaction.response.send_message("❌ Cannot warn someone with equal or higher role!", ephemeral=True)
            return
        
        # Add to database
        self.bot.db.add_punishment(member.id, "verbal_warn", reason, interaction.user.id)
        self.bot.db.log_staff_action(interaction.user.id, "verbal_warn", member.id, reason)
        
        # Send DM
        await self.send_punishment_dm(member, "verbal_warn", reason, interaction.user)
        
        # Response embed
        verbal_count = self.bot.db.get_punishment_count(member.id, "verbal_warn")
        
        embed = discord.Embed(
            title="⚠️ Verbal Warning Issued",
            color=COLORS["warning"],
            timestamp=datetime.now(timezone.utc)
        )
        embed.add_field(name="User", value=f"{member.mention} ({member.id})", inline=True)
        embed.add_field(name="Moderator", value=interaction.user.mention, inline=True)
        embed.add_field(name="Count", value=f"{verbal_count}/{PUNISHMENT_THRESHOLDS['verbal_warns']}", inline=True)
        embed.add_field(name="Reason", value=reason, inline=False)
        
        if verbal_count >= PUNISHMENT_THRESHOLDS["verbal_warns"]:
            embed.add_field(
                name="⚠️ Threshold Reached",
                value=f"User will be auto-escalated to formal warning!",
                inline=False
            )
        
        await interaction.response.send_message(embed=embed)
        
        # Log to mod channel
        mod_channel = self.bot.get_channel(MOD_LOG_CHANNEL_ID)
        if mod_channel:
            await mod_channel.send(embed=embed)
        
        # Check auto-escalation
        await self.check_auto_punishment(member.id, interaction.user, interaction.guild)
    
    # ===== FORMAL WARN =====
    @app_commands.command(name="warn", description="Issue a formal warning to a user")
    @app_commands.checks.has_permissions(moderate_members=True)
    @app_commands.describe(
        user="Member to warn OR User ID",
        reason="Reason for warning"
    )
    async def warn(self, interaction: discord.Interaction, 
                   user: str, reason: str):
        """Issue formal warning - accepts member mention or user ID"""
        # Try to parse as user ID
        try:
            user_id = int(user.strip('<@!>'))
        except ValueError:
            await interaction.response.send_message("❌ Invalid user format! Use @mention or user ID", ephemeral=True)
            return
        
        # Try to get as member
        member = interaction.guild.get_member(user_id)
        
        # Get user object
        try:
            user_obj = await self.bot.fetch_user(user_id)
        except discord.NotFound:
            await interaction.response.send_message("❌ User not found!", ephemeral=True)
            return
        
        if user_obj.bot:
            await interaction.response.send_message("❌ Cannot warn bots!", ephemeral=True)
            return
        
        if member and member.top_role >= interaction.user.top_role and interaction.user.id != interaction.guild.owner_id:
            await interaction.response.send_message("❌ Cannot warn someone with equal or higher role!", ephemeral=True)
            return
        
        self.bot.db.add_punishment(user_id, "warn", reason, interaction.user.id)
        self.bot.db.log_staff_action(interaction.user.id, "warn", user_id, reason)
        
        if member:
            await self.send_punishment_dm(user_obj, "warn", reason, interaction.user)
        
        warn_count = self.bot.db.get_punishment_count(user_id, "warn")
        
        embed = discord.Embed(
            title="🚨 Formal Warning Issued",
            color=COLORS["error"],
            timestamp=datetime.now(timezone.utc)
        )
        embed.add_field(name="User", value=f"{user_obj.mention} ({user_id})", inline=True)
        embed.add_field(name="Moderator", value=interaction.user.mention, inline=True)
        embed.add_field(name="Count", value=f"{warn_count}/{PUNISHMENT_THRESHOLDS['warns']}", inline=True)
        embed.add_field(name="Reason", value=reason, inline=False)
        
        if not member:
            embed.add_field(name="ℹ️ Note", value="User is not in the server", inline=False)
        
        if warn_count >= PUNISHMENT_THRESHOLDS["warns"]:
            embed.add_field(
                name="⚠️ Threshold Reached",
                value="User will be auto-kicked!" if member else "User would be kicked if in server",
                inline=False
            )
        
        await interaction.response.send_message(embed=embed)
        
        mod_channel = self.bot.get_channel(MOD_LOG_CHANNEL_ID)
        if mod_channel:
            await mod_channel.send(embed=embed)
        
        if member:
            await self.check_auto_punishment(user_id, interaction.user, interaction.guild)
    
    # ===== UNWARN =====
    @app_commands.command(name="unwarn", description="Remove a warning from a user")
    @app_commands.checks.has_permissions(moderate_members=True)
    @app_commands.describe(
        user="Member OR User ID",
        warning_type="Type of warning to remove (verbal_warn or warn)"
    )
    @app_commands.choices(warning_type=[
        app_commands.Choice(name="Verbal Warning", value="verbal_warn"),
        app_commands.Choice(name="Formal Warning", value="warn")
    ])
    async def unwarn(self, interaction: discord.Interaction, 
                    user: str, warning_type: str):
        """Remove warnings - accepts member mention or user ID"""
        # Try to parse as user ID
        try:
            user_id = int(user.strip('<@!>'))
        except ValueError:
            await interaction.response.send_message("❌ Invalid user format! Use @mention or user ID", ephemeral=True)
            return
        
        # Get user object
        try:
            user_obj = await self.bot.fetch_user(user_id)
        except discord.NotFound:
            await interaction.response.send_message("❌ User not found!", ephemeral=True)
            return
        
        punishments = self.bot.db.get_active_punishments(user_id, warning_type)
        
        if not punishments:
            await interaction.response.send_message(
                f"❌ {user_obj.mention} has no active {warning_type.replace('_', ' ')}s", 
                ephemeral=True
            )
            return
        
        # Remove most recent warning
        self.bot.db.remove_punishment(punishments[0][0], interaction.user.id)
        self.bot.db.log_staff_action(interaction.user.id, f"remove_{warning_type}", user_id)
        
        remaining = self.bot.db.get_punishment_count(user_id, warning_type)
        
        embed = discord.Embed(
            title=f"✅ {warning_type.replace('_', ' ').title()} Removed",
            description=f"Removed {warning_type.replace('_', ' ')} from {user_obj.mention}",
            color=COLORS["success"]
        )
        embed.add_field(name="User ID", value=str(user_id), inline=True)
        embed.add_field(name="Removed By", value=interaction.user.mention, inline=True)
        embed.add_field(name="Remaining", value=str(remaining), inline=True)
        
        await interaction.response.send_message(embed=embed)
        
        mod_channel = self.bot.get_channel(MOD_LOG_CHANNEL_ID)
        if mod_channel:
            await mod_channel.send(embed=embed)
    
    # ===== KICK =====
    @app_commands.command(name="kick", description="Kick a user from the server")
    @app_commands.checks.has_permissions(kick_members=True)
    @app_commands.describe(
        user="Member to kick OR User ID if they're not in server",
        reason="Reason for kick"
    )
    async def kick(self, interaction: discord.Interaction, 
                   user: str, reason: str):
        """Kick user - accepts member mention or user ID"""
        # Try to parse as user ID first
        try:
            user_id = int(user.strip('<@!>'))
            member = interaction.guild.get_member(user_id)
            
            if not member:
                await interaction.response.send_message("❌ User is not in the server and cannot be kicked!", ephemeral=True)
                return
        except ValueError:
            await interaction.response.send_message("❌ Invalid user format! Use @mention or user ID", ephemeral=True)
            return
        
        if member.bot:
            await interaction.response.send_message("❌ Cannot kick bots!", ephemeral=True)
            return
        
        if member.top_role >= interaction.user.top_role and interaction.user.id != interaction.guild.owner_id:
            await interaction.response.send_message("❌ Cannot kick someone with equal or higher role!", ephemeral=True)
            return
        
        try:
            # Send DM before kicking
            await self.send_punishment_dm(member, "kick", reason, interaction.user)
            
            # Kick
            await member.kick(reason=f"{reason} | By: {interaction.user}")
            
            # Log to database
            self.bot.db.add_punishment(member.id, "kick", reason, interaction.user.id)
            self.bot.db.log_staff_action(interaction.user.id, "kick", member.id, reason)
            
            embed = discord.Embed(
                title="👢 User Kicked",
                color=COLORS["error"],
                timestamp=datetime.now(timezone.utc)
            )
            embed.add_field(name="User", value=f"{member.mention} ({member.name}#{member.discriminator})", inline=True)
            embed.add_field(name="Moderator", value=interaction.user.mention, inline=True)
            embed.add_field(name="Reason", value=reason, inline=False)
            
            await interaction.response.send_message(embed=embed)
            
            mod_channel = self.bot.get_channel(MOD_LOG_CHANNEL_ID)
            if mod_channel:
                await mod_channel.send(embed=embed)
            
        except discord.Forbidden:
            await interaction.response.send_message("❌ I don't have permission to kick this member!", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ An error occurred: {str(e)}", ephemeral=True)
    
    # ===== BAN =====
    @app_commands.command(name="ban", description="Ban a user from the server")
    @app_commands.checks.has_permissions(ban_members=True)
    @app_commands.describe(
        user="Member to ban OR User ID (works even if they left)",
        reason="Reason for ban",
        delete_days="Number of days of messages to delete (0-7)"
    )
    async def ban(self, interaction: discord.Interaction, 
                  user: str, reason: str, delete_days: int = 0):
        """Ban user - accepts member mention or user ID"""
        if delete_days < 0 or delete_days > 7:
            delete_days = 0
        
        # Try to parse as user ID
        try:
            user_id = int(user.strip('<@!>'))
        except ValueError:
            await interaction.response.send_message("❌ Invalid user format! Use @mention or user ID", ephemeral=True)
            return
        
        # Try to get as member first
        member = interaction.guild.get_member(user_id)
        
        # Get user object (works even if not in server)
        try:
            user_obj = await self.bot.fetch_user(user_id)
        except discord.NotFound:
            await interaction.response.send_message("❌ User not found!", ephemeral=True)
            return
        
        # Check permissions if user is in server
        if member:
            if member.bot:
                await interaction.response.send_message("❌ Cannot ban bots!", ephemeral=True)
                return
            
            if member.top_role >= interaction.user.top_role and interaction.user.id != interaction.guild.owner_id:
                await interaction.response.send_message("❌ Cannot ban someone with equal or higher role!", ephemeral=True)
                return
        
        try:
            # Send DM before banning (only if they're in server)
            if member:
                await self.send_punishment_dm(user_obj, "ban", reason, interaction.user)
            
            # Ban
            await interaction.guild.ban(user_obj, reason=f"{reason} | By: {interaction.user}", 
                           delete_message_days=delete_days)
            
            # Log to database
            self.bot.db.add_punishment(user_id, "ban", reason, interaction.user.id)
            self.bot.db.log_staff_action(interaction.user.id, "ban", user_id, reason)
            
            embed = discord.Embed(
                title="🔨 User Banned",
                color=COLORS["error"],
                timestamp=datetime.now(timezone.utc)
            )
            embed.add_field(name="User", value=f"{user_obj.mention} ({user_obj.name})", inline=True)
            embed.add_field(name="User ID", value=str(user_id), inline=True)
            embed.add_field(name="Moderator", value=interaction.user.mention, inline=True)
            embed.add_field(name="Reason", value=reason, inline=False)
            
            if delete_days > 0:
                embed.add_field(name="Messages Deleted", value=f"Last {delete_days} day(s)", inline=True)
            
            if not member:
                embed.add_field(name="ℹ️ Note", value="User was not in the server", inline=False)
            
            await interaction.response.send_message(embed=embed)
            
            mod_channel = self.bot.get_channel(MOD_LOG_CHANNEL_ID)
            if mod_channel:
                await mod_channel.send(embed=embed)
            
        except discord.Forbidden:
            await interaction.response.send_message("❌ I don't have permission to ban this user!", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ An error occurred: {str(e)}", ephemeral=True)
    
    # ===== UNBAN =====
    @app_commands.command(name="unban", description="Unban a user from the server")
    @app_commands.checks.has_permissions(ban_members=True)
    async def unban(self, interaction: discord.Interaction, user_id: str, reason: str = "No reason provided"):
        """Unban user"""
        try:
            user = await self.bot.fetch_user(int(user_id))
            await interaction.guild.unban(user, reason=f"{reason} | By: {interaction.user}")
            
            # Update database
            punishments = self.bot.db.get_active_punishments(user.id, "ban")
            for punishment in punishments:
                self.bot.db.remove_punishment(punishment[0], interaction.user.id)
            
            self.bot.db.log_staff_action(interaction.user.id, "unban", user.id, reason)
            
            embed = discord.Embed(
                title="✅ User Unbanned",
                color=COLORS["success"],
                timestamp=datetime.now(timezone.utc)
            )
            embed.add_field(name="User", value=f"{user.mention} ({user.name})", inline=True)
            embed.add_field(name="Moderator", value=interaction.user.mention, inline=True)
            embed.add_field(name="Reason", value=reason, inline=False)
            
            await interaction.response.send_message(embed=embed)
            
            mod_channel = self.bot.get_channel(MOD_LOG_CHANNEL_ID)
            if mod_channel:
                await mod_channel.send(embed=embed)
            
        except ValueError:
            await interaction.response.send_message("❌ Invalid user ID!", ephemeral=True)
        except discord.NotFound:
            await interaction.response.send_message("❌ User not found or not banned!", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ An error occurred: {str(e)}", ephemeral=True)
    
    # ===== TIMEOUT =====
    @app_commands.command(name="timeout", description="Timeout a user")
    @app_commands.checks.has_permissions(moderate_members=True)
    @app_commands.describe(
        user="Member to timeout (must be in server)",
        duration="Timeout duration",
        unit="Time unit (minutes, hours, days)",
        reason="Reason for timeout"
    )
    @app_commands.choices(unit=[
        app_commands.Choice(name="Minutes", value="minutes"),
        app_commands.Choice(name="Hours", value="hours"),
        app_commands.Choice(name="Days", value="days")
    ])
    async def timeout(self, interaction: discord.Interaction, 
                     user: str, duration: int, unit: str, reason: str):
        """Timeout user - must be in server"""
        # Try to parse as user ID
        try:
            user_id = int(user.strip('<@!>'))
        except ValueError:
            await interaction.response.send_message("❌ Invalid user format! Use @mention or user ID", ephemeral=True)
            return
        
        # Must be a member for timeout
        member = interaction.guild.get_member(user_id)
        if not member:
            await interaction.response.send_message("❌ User must be in the server to timeout!", ephemeral=True)
            return
        if member.bot:
            await interaction.response.send_message("❌ Cannot timeout bots!", ephemeral=True)
            return
        
        if member.top_role >= interaction.user.top_role and interaction.user.id != interaction.guild.owner_id:
            await interaction.response.send_message("❌ Cannot timeout someone with equal or higher role!", ephemeral=True)
            return
        
        # Calculate timeout duration
        if unit == "minutes":
            delta = timedelta(minutes=duration)
        elif unit == "hours":
            delta = timedelta(hours=duration)
        else:
            delta = timedelta(days=duration)
        
        # Max timeout is 28 days
        if delta > timedelta(days=28):
            await interaction.response.send_message("❌ Maximum timeout duration is 28 days!", ephemeral=True)
            return
        
        try:
            expires_at = datetime.now(timezone.utc) + delta
            
            # Apply timeout
            await member.timeout(delta, reason=f"{reason} | By: {interaction.user}")
            
            # Log to database
            self.bot.db.add_punishment(member.id, "timeout", reason, interaction.user.id, expires_at)
            self.bot.db.log_staff_action(interaction.user.id, "timeout", member.id, reason)
            
            # Send DM
            await self.send_punishment_dm(member, "timeout", reason, interaction.user, expires_at)
            
            embed = discord.Embed(
                title="⏰ User Timed Out",
                color=COLORS["warning"],
                timestamp=datetime.now(timezone.utc)
            )
            embed.add_field(name="User", value=f"{member.mention} ({member.id})", inline=True)
            embed.add_field(name="Duration", value=f"{duration} {unit}", inline=True)
            embed.add_field(name="Expires", value=f"<t:{int(expires_at.timestamp())}:R>", inline=True)
            embed.add_field(name="Moderator", value=interaction.user.mention, inline=True)
            embed.add_field(name="Reason", value=reason, inline=False)
            
            await interaction.response.send_message(embed=embed)
            
            mod_channel = self.bot.get_channel(MOD_LOG_CHANNEL_ID)
            if mod_channel:
                await mod_channel.send(embed=embed)
            
        except discord.Forbidden:
            await interaction.response.send_message("❌ I don't have permission to timeout this member!", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ An error occurred: {str(e)}", ephemeral=True)
    
    # ===== UNTIMEOUT =====
    @app_commands.command(name="untimeout", description="Remove timeout from a user")
    @app_commands.checks.has_permissions(moderate_members=True)
    async def untimeout(self, interaction: discord.Interaction, member: discord.Member):
        """Remove timeout"""
        try:
            await member.timeout(None)
            
            # Update database
            timeouts = self.bot.db.get_active_punishments(member.id, "timeout")
            for timeout in timeouts:
                self.bot.db.remove_punishment(timeout[0], interaction.user.id)
            
            self.bot.db.log_staff_action(interaction.user.id, "untimeout", member.id)
            
            embed = discord.Embed(
                title="✅ Timeout Removed",
                description=f"Removed timeout from {member.mention}",
                color=COLORS["success"]
            )
            embed.add_field(name="Moderator", value=interaction.user.mention, inline=True)
            
            await interaction.response.send_message(embed=embed)
            
            mod_channel = self.bot.get_channel(MOD_LOG_CHANNEL_ID)
            if mod_channel:
                await mod_channel.send(embed=embed)
            
        except Exception as e:
            await interaction.response.send_message(f"❌ An error occurred: {str(e)}", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Moderation(bot))