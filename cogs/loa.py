# cogs/loa.py - Leave of Absence System
import discord
from discord import app_commands
from discord.ext import commands, tasks
from datetime import datetime, timedelta, timezone
from config import *

class LOA(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.check_expired_loas.start()
    
    def cog_unload(self):
        self.check_expired_loas.cancel()
    
    @tasks.loop(hours=6)
    async def check_expired_loas(self):
        """Check for expired LOAs and notify"""
        conn = self.bot.db.get_connection()
        cursor = conn.cursor()
        
        # Find approved LOAs that have expired
        now = datetime.now(timezone.utc)
        cursor.execute("""
            SELECT * FROM loa_requests 
            WHERE status = 'approved' AND end_date <= ?
        """, (now,))
        
        expired_loas = cursor.fetchall()
        
        for loa in expired_loas:
            loa_id, user_id, start_date, end_date, reason, status, reviewed_by, reviewed_at, created_at = loa
            
            # Mark as expired
            cursor.execute("""
                UPDATE loa_requests SET status = 'expired' WHERE id = ?
            """, (loa_id,))
            
            # Notify user and staff
            guild = self.bot.get_guild(GUILD_ID)
            if guild:
                member = guild.get_member(user_id)
                if member:
                    try:
                        embed = discord.Embed(
                            title="⏰ Leave of Absence Expired",
                            description="Your approved LOA has now ended. Welcome back!",
                            color=COLORS["info"],
                            timestamp=datetime.now(timezone.utc)
                        )
                        embed.add_field(name="End Date", value=f"<t:{int(datetime.fromisoformat(end_date).timestamp())}:F>", inline=True)
                        embed.add_field(name="Reason", value=reason, inline=False)
                        embed.set_footer(text="Please resume your regular duties")
                        
                        await member.send(embed=embed)
                    except:
                        pass
                
                # Notify LOA channel
                if LOA_CHANNEL_ID:
                    loa_channel = self.bot.get_channel(LOA_CHANNEL_ID)
                    if loa_channel:
                        embed = discord.Embed(
                            title="⏰ LOA Expired",
                            description=f"{member.mention}'s LOA has expired",
                            color=COLORS["warning"]
                        )
                        embed.add_field(name="Staff Member", value=member.mention if member else f"<@{user_id}>", inline=True)
                        embed.add_field(name="Duration", value=f"{start_date} to {end_date}", inline=False)
                        await loa_channel.send(embed=embed)
        
        conn.commit()
        conn.close()
    
    @check_expired_loas.before_loop
    async def before_check_loas(self):
        await self.bot.wait_until_ready()
    
    @app_commands.command(name="requestloa", description="Request a Leave of Absence (Staff only)")
    @app_commands.describe(
        start_date="Start date (YYYY-MM-DD)",
        end_date="End date (YYYY-MM-DD)",
        reason="Reason for LOA"
    )
    async def request_loa(self, interaction: discord.Interaction, start_date: str, end_date: str, reason: str):
        """Request LOA"""
        # Check if user is staff
        is_staff = False
        for role_id in STAFF_ROLES.values():
            if role_id and interaction.guild.get_role(role_id) in interaction.user.roles:
                is_staff = True
                break
        
        if not is_staff and not interaction.user.guild_permissions.moderate_members:
            await interaction.response.send_message("❌ This command is for staff members only!", ephemeral=True)
            return
        
        # Parse dates
        try:
            start = datetime.strptime(start_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            end = datetime.strptime(end_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except ValueError:
            await interaction.response.send_message("❌ Invalid date format! Use YYYY-MM-DD (e.g., 2026-01-20)", ephemeral=True)
            return
        
        # Validation
        if start >= end:
            await interaction.response.send_message("❌ End date must be after start date!", ephemeral=True)
            return
        
        if start < datetime.now(timezone.utc):
            await interaction.response.send_message("❌ Start date cannot be in the past!", ephemeral=True)
            return
        
        duration = (end - start).days
        if duration > 60:
            await interaction.response.send_message("❌ LOA duration cannot exceed 60 days! Please contact management for longer absences.", ephemeral=True)
            return
        
        # Check for overlapping LOAs
        existing_loas = self.bot.db.get_user_loas(interaction.user.id)
        for loa in existing_loas:
            if loa[5] == 'pending' or loa[5] == 'approved':  # status
                existing_start = datetime.fromisoformat(loa[2])
                existing_end = datetime.fromisoformat(loa[3])
                
                # Check for overlap
                if not (end < existing_start or start > existing_end):
                    await interaction.response.send_message(
                        "❌ You already have a pending/approved LOA that overlaps with these dates!",
                        ephemeral=True
                    )
                    return
        
        # Create LOA request
        loa_id = self.bot.db.create_loa(interaction.user.id, start, end, reason)
        
        embed = discord.Embed(
            title="✅ LOA Request Submitted",
            description="Your Leave of Absence request has been submitted for approval.",
            color=COLORS["success"],
            timestamp=datetime.now(timezone.utc)
        )
        
        embed.add_field(name="Start Date", value=f"<t:{int(start.timestamp())}:D>", inline=True)
        embed.add_field(name="End Date", value=f"<t:{int(end.timestamp())}:D>", inline=True)
        embed.add_field(name="Duration", value=f"{duration} days", inline=True)
        embed.add_field(name="Reason", value=reason, inline=False)
        embed.add_field(name="Request ID", value=f"#{loa_id}", inline=True)
        embed.set_footer(text="You will be notified when your request is reviewed")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
        
        # Notify LOA channel or admins
        if LOA_CHANNEL_ID:
            loa_channel = self.bot.get_channel(LOA_CHANNEL_ID)
        else:
            loa_channel = self.bot.get_channel(MOD_LOG_CHANNEL_ID)
        
        if loa_channel:
            notif_embed = discord.Embed(
                title="📝 New LOA Request",
                description=f"{interaction.user.mention} has requested a Leave of Absence",
                color=COLORS["warning"],
                timestamp=datetime.now(timezone.utc)
            )
            
            notif_embed.add_field(name="Staff Member", value=f"{interaction.user.mention}\n{interaction.user.name}", inline=True)
            notif_embed.add_field(name="Request ID", value=f"#{loa_id}", inline=True)
            notif_embed.add_field(name="Duration", value=f"{duration} days", inline=True)
            notif_embed.add_field(name="Start Date", value=f"<t:{int(start.timestamp())}:D>", inline=True)
            notif_embed.add_field(name="End Date", value=f"<t:{int(end.timestamp())}:D>", inline=True)
            notif_embed.add_field(name="Reason", value=reason, inline=False)
            notif_embed.set_footer(text=f"Use /loa approve {loa_id} or /loa deny {loa_id}")
            
            await loa_channel.send(embed=notif_embed)
        
        self.bot.db.log_staff_action(interaction.user.id, "loa_request", None, f"LOA #{loa_id}: {duration} days")
    
    @app_commands.command(name="loa", description="Manage LOA requests (Admin only)")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(
        action="Action to perform",
        loa_id="LOA request ID",
        reason="Reason for denial (required for deny action)"
    )
    @app_commands.choices(action=[
        app_commands.Choice(name="Approve", value="approve"),
        app_commands.Choice(name="Deny", value="deny"),
        app_commands.Choice(name="List Pending", value="list")
    ])
    async def loa_manage(self, interaction: discord.Interaction, action: str, loa_id: int = None, reason: str = None):
        """Manage LOA requests"""
        
        if action == "list":
            # List pending LOAs
            pending_loas = self.bot.db.get_pending_loas()
            
            if not pending_loas:
                await interaction.response.send_message("✅ No pending LOA requests!", ephemeral=True)
                return
            
            embed = discord.Embed(
                title="📋 Pending LOA Requests",
                description=f"Total: {len(pending_loas)}",
                color=COLORS["info"]
            )
            
            for loa in pending_loas[:10]:  # Show max 10
                loa_id_db, user_id, start_date, end_date, reason_db, status, reviewed_by, reviewed_at, created_at = loa
                
                member = interaction.guild.get_member(user_id)
                user_name = member.mention if member else f"<@{user_id}>"
                
                start = datetime.fromisoformat(start_date)
                end = datetime.fromisoformat(end_date)
                duration = (end - start).days
                
                embed.add_field(
                    name=f"LOA #{loa_id_db} - {member.name if member else 'Unknown User'}",
                    value=(
                        f"**User:** {user_name}\n"
                        f"**Duration:** {duration} days\n"
                        f"**Dates:** <t:{int(start.timestamp())}:D> to <t:{int(end.timestamp())}:D>\n"
                        f"**Reason:** {reason_db[:100]}{'...' if len(reason_db) > 100 else ''}\n"
                        f"**Requested:** <t:{int(datetime.fromisoformat(created_at).timestamp())}:R>"
                    ),
                    inline=False
                )
            
            if len(pending_loas) > 10:
                embed.set_footer(text=f"Showing 10 of {len(pending_loas)} pending requests")
            
            await interaction.response.send_message(embed=embed)
            return
        
        # Approve or Deny actions require loa_id
        if loa_id is None:
            await interaction.response.send_message("❌ Please provide an LOA ID!", ephemeral=True)
            return
        
        # Get LOA from database
        conn = self.bot.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM loa_requests WHERE id = ?", (loa_id,))
        loa_data = cursor.fetchone()
        conn.close()
        
        if not loa_data:
            await interaction.response.send_message(f"❌ LOA request #{loa_id} not found!", ephemeral=True)
            return
        
        loa_db_id, user_id, start_date, end_date, reason_db, status, reviewed_by_db, reviewed_at_db, created_at = loa_data
        
        if status != 'pending':
            await interaction.response.send_message(f"❌ LOA #{loa_id} has already been {status}!", ephemeral=True)
            return
        
        if action == "approve":
            # Approve LOA
            self.bot.db.update_loa_status(loa_id, 'approved', interaction.user.id)
            
            embed = discord.Embed(
                title="✅ LOA Request Approved",
                description=f"LOA #{loa_id} has been approved",
                color=COLORS["success"],
                timestamp=datetime.now(timezone.utc)
            )
            
            member = interaction.guild.get_member(user_id)
            embed.add_field(name="Staff Member", value=member.mention if member else f"<@{user_id}>", inline=True)
            embed.add_field(name="Approved By", value=interaction.user.mention, inline=True)
            
            start = datetime.fromisoformat(start_date)
            end = datetime.fromisoformat(end_date)
            duration = (end - start).days
            
            embed.add_field(name="Duration", value=f"{duration} days", inline=True)
            embed.add_field(name="Start", value=f"<t:{int(start.timestamp())}:D>", inline=True)
            embed.add_field(name="End", value=f"<t:{int(end.timestamp())}:D>", inline=True)
            
            await interaction.response.send_message(embed=embed)
            
            # Notify user
            if member:
                try:
                    dm_embed = discord.Embed(
                        title="✅ LOA Request Approved",
                        description=f"Your Leave of Absence request has been approved!",
                        color=COLORS["success"],
                        timestamp=datetime.now(timezone.utc)
                    )
                    dm_embed.add_field(name="Start Date", value=f"<t:{int(start.timestamp())}:F>", inline=False)
                    dm_embed.add_field(name="End Date", value=f"<t:{int(end.timestamp())}:F>", inline=False)
                    dm_embed.add_field(name="Duration", value=f"{duration} days", inline=True)
                    dm_embed.add_field(name="Approved By", value=interaction.user.mention, inline=True)
                    dm_embed.set_footer(text="Enjoy your time off!")
                    
                    await member.send(embed=dm_embed)
                except:
                    pass
            
            self.bot.db.log_staff_action(interaction.user.id, "loa_approve", user_id, f"LOA #{loa_id}")
            
        elif action == "deny":
            if not reason:
                await interaction.response.send_message("❌ Please provide a reason for denial!", ephemeral=True)
                return
            
            # Deny LOA
            self.bot.db.update_loa_status(loa_id, 'denied', interaction.user.id, reason)
            
            embed = discord.Embed(
                title="❌ LOA Request Denied",
                description=f"LOA #{loa_id} has been denied",
                color=COLORS["error"],
                timestamp=datetime.now(timezone.utc)
            )
            
            member = interaction.guild.get_member(user_id)
            embed.add_field(name="Staff Member", value=member.mention if member else f"<@{user_id}>", inline=True)
            embed.add_field(name="Denied By", value=interaction.user.mention, inline=True)
            embed.add_field(name="Reason", value=reason, inline=False)
            
            await interaction.response.send_message(embed=embed)
            
            # Notify user
            if member:
                try:
                    dm_embed = discord.Embed(
                        title="❌ LOA Request Denied",
                        description=f"Your Leave of Absence request has been denied.",
                        color=COLORS["error"],
                        timestamp=datetime.now(timezone.utc)
                    )
                    dm_embed.add_field(name="Denied By", value=interaction.user.mention, inline=True)
                    dm_embed.add_field(name="Reason", value=reason, inline=False)
                    dm_embed.set_footer(text="Please contact management if you have questions")
                    
                    await member.send(embed=dm_embed)
                except:
                    pass
            
            self.bot.db.log_staff_action(interaction.user.id, "loa_deny", user_id, f"LOA #{loa_id}: {reason}")
    
    @app_commands.command(name="myloas", description="View your LOA history")
    async def my_loas(self, interaction: discord.Interaction):
        """View personal LOA history"""
        loas = self.bot.db.get_user_loas(interaction.user.id)
        
        if not loas:
            await interaction.response.send_message("You have no LOA requests on record.", ephemeral=True)
            return
        
        embed = discord.Embed(
            title="📋 Your LOA History",
            description=f"Total Requests: {len(loas)}",
            color=COLORS["info"]
        )
        
        for loa in loas[:5]:  # Show last 5
            loa_id, user_id, start_date, end_date, reason, status, reviewed_by, reviewed_at, created_at = loa
            
            start = datetime.fromisoformat(start_date)
            end = datetime.fromisoformat(end_date)
            duration = (end - start).days
            
            status_emoji = {
                'pending': '⏳',
                'approved': '✅',
                'denied': '❌',
                'expired': '⏰'
            }
            
            embed.add_field(
                name=f"{status_emoji.get(status, '📋')} LOA #{loa_id} - {status.title()}",
                value=(
                    f"**Duration:** {duration} days\n"
                    f"**Dates:** <t:{int(start.timestamp())}:D> to <t:{int(end.timestamp())}:D>\n"
                    f"**Requested:** <t:{int(datetime.fromisoformat(created_at).timestamp())}:R>"
                ),
                inline=False
            )
        
        if len(loas) > 5:
            embed.set_footer(text=f"Showing 5 of {len(loas)} requests")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(LOA(bot))