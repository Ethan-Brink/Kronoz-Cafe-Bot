# cogs/staff_management.py - Staff Statistics and Management
import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime, timedelta, timezone
from config import *
from typing import Optional

class StaffManagement(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @app_commands.command(name="staffstats", description="View staff member statistics")
    @app_commands.checks.has_permissions(moderate_members=True)
    @app_commands.describe(
        member="Staff member to view stats for (leave empty for yourself)",
        days="Number of days to analyze (default: 30)"
    )
    async def staff_stats(self, interaction: discord.Interaction, 
                         member: Optional[discord.Member] = None, 
                         days: int = 30):
        """View staff statistics"""
        target = member or interaction.user
        
        if days < 1 or days > 365:
            await interaction.response.send_message("❌ Days must be between 1 and 365!", ephemeral=True)
            return
        
        # Get stats from database
        stats = self.bot.db.get_staff_stats(target.id, days)
        
        if not stats:
            await interaction.response.send_message(
                f"📊 {target.mention} has no recorded staff activity in the last {days} days.",
                ephemeral=True
            )
            return
        
        embed = discord.Embed(
            title=f"📊 Staff Statistics: {target.display_name}",
            description=f"Activity over the last {days} days",
            color=target.color or COLORS["info"],
            timestamp=datetime.now(timezone.utc)
        )
        
        embed.set_thumbnail(url=target.display_avatar.url)
        
        # Organize stats
        action_counts = {}
        total_actions = 0
        
        for action_type, count in stats:
            action_counts[action_type] = count
            total_actions += count
        
        embed.add_field(name="📈 Total Actions", value=str(total_actions), inline=True)
        
        # Moderation actions
        mod_actions = []
        if 'verbal_warn' in action_counts:
            mod_actions.append(f"⚠️ Verbal Warns: {action_counts['verbal_warn']}")
        if 'warn' in action_counts:
            mod_actions.append(f"🚨 Warns: {action_counts['warn']}")
        if 'kick' in action_counts:
            mod_actions.append(f"👢 Kicks: {action_counts['kick']}")
        if 'ban' in action_counts:
            mod_actions.append(f"🔨 Bans: {action_counts['ban']}")
        if 'timeout' in action_counts:
            mod_actions.append(f"⏰ Timeouts: {action_counts['timeout']}")
        if 'unban' in action_counts:
            mod_actions.append(f"✅ Unbans: {action_counts['unban']}")
        
        if mod_actions:
            embed.add_field(
                name="🛡️ Moderation Actions",
                value="\n".join(mod_actions),
                inline=False
            )
        
        # Ticket actions
        ticket_actions = []
        if 'ticket_create' in action_counts:
            ticket_actions.append(f"🎫 Tickets Created: {action_counts['ticket_create']}")
        if 'ticket_close' in action_counts:
            ticket_actions.append(f"🔒 Tickets Closed: {action_counts['ticket_close']}")
        
        if ticket_actions:
            embed.add_field(
                name="🎫 Ticket Activity",
                value="\n".join(ticket_actions),
                inline=False
            )
        
        # LOA actions
        loa_actions = []
        if 'loa_request' in action_counts:
            loa_actions.append(f"📝 LOA Requests: {action_counts['loa_request']}")
        if 'loa_approve' in action_counts:
            loa_actions.append(f"✅ LOAs Approved: {action_counts['loa_approve']}")
        if 'loa_deny' in action_counts:
            loa_actions.append(f"❌ LOAs Denied: {action_counts['loa_deny']}")
        
        if loa_actions:
            embed.add_field(
                name="📋 LOA Management",
                value="\n".join(loa_actions),
                inline=False
            )
        
        # Calculate average actions per day
        avg_per_day = total_actions / days
        embed.add_field(
            name="📊 Average",
            value=f"{avg_per_day:.1f} actions/day",
            inline=True
        )
        
        # Activity rating
        if avg_per_day >= 5:
            rating = "🔥 Very Active"
        elif avg_per_day >= 2:
            rating = "✅ Active"
        elif avg_per_day >= 0.5:
            rating = "⚠️ Moderate"
        else:
            rating = "❌ Low Activity"
        
        embed.add_field(name="📈 Activity Level", value=rating, inline=True)
        
        embed.set_footer(text=f"Requested by {interaction.user.name}")
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="leaderboard", description="View staff activity leaderboard")
    @app_commands.checks.has_permissions(moderate_members=True)
    @app_commands.describe(
        days="Number of days to analyze (default: 30)"
    )
    async def leaderboard(self, interaction: discord.Interaction, days: int = 30):
        """Staff activity leaderboard"""
        if days < 1 or days > 365:
            await interaction.response.send_message("❌ Days must be between 1 and 365!", ephemeral=True)
            return
        
        # Get all staff stats
        all_stats = self.bot.db.get_all_staff_stats(days)
        
        if not all_stats:
            await interaction.response.send_message(
                f"📊 No staff activity recorded in the last {days} days.",
                ephemeral=True
            )
            return
        
        # Aggregate by staff member
        staff_totals = {}
        for staff_id, action_type, count in all_stats:
            if staff_id not in staff_totals:
                staff_totals[staff_id] = 0
            staff_totals[staff_id] += count
        
        # Sort by total actions
        sorted_staff = sorted(staff_totals.items(), key=lambda x: x[1], reverse=True)
        
        embed = discord.Embed(
            title="🏆 Staff Activity Leaderboard",
            description=f"Top staff members over the last {days} days",
            color=COLORS["primary"],
            timestamp=datetime.now(timezone.utc)
        )
        
        # Medal emojis
        medals = ["🥇", "🥈", "🥉"]
        
        for i, (staff_id, total_actions) in enumerate(sorted_staff[:10], 1):
            member = interaction.guild.get_member(staff_id)
            
            if not member:
                continue
            
            # Get specific action breakdown
            member_stats = self.bot.db.get_staff_stats(staff_id, days)
            action_breakdown = {}
            for action_type, count in member_stats:
                action_breakdown[action_type] = count
            
            # Top actions
            top_actions = sorted(action_breakdown.items(), key=lambda x: x[1], reverse=True)[:3]
            action_text = ", ".join([f"{action.replace('_', ' ').title()}: {count}" for action, count in top_actions])
            
            avg_per_day = total_actions / days
            
            medal = medals[i-1] if i <= 3 else f"#{i}"
            
            embed.add_field(
                name=f"{medal} {member.display_name}",
                value=(
                    f"**Total Actions:** {total_actions}\n"
                    f"**Avg/Day:** {avg_per_day:.1f}\n"
                    f"**Top Actions:** {action_text}"
                ),
                inline=False
            )
        
        embed.set_footer(text=f"Showing top {min(10, len(sorted_staff))} staff members")
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="note", description="Manage staff notes on users")
    @app_commands.checks.has_permissions(moderate_members=True)
    @app_commands.describe(
        action="Action to perform",
        member="User to add note to / view notes for",
        note="Note content (for add action)"
    )
    @app_commands.choices(action=[
        app_commands.Choice(name="Add Note", value="add"),
        app_commands.Choice(name="View Notes", value="view")
    ])
    async def note_manage(self, interaction: discord.Interaction, 
                         action: str, 
                         member: discord.Member, 
                         note: str = None):
        """Manage staff notes"""
        
        if action == "add":
            if not note:
                await interaction.response.send_message("❌ Please provide a note to add!", ephemeral=True)
                return
            
            if len(note) > 1000:
                await interaction.response.send_message("❌ Note is too long! Maximum 1000 characters.", ephemeral=True)
                return
            
            # Add note to database
            self.bot.db.add_note(member.id, note, interaction.user.id)
            self.bot.db.log_staff_action(interaction.user.id, "note_add", member.id, f"Added note: {note[:50]}...")
            
            embed = discord.Embed(
                title="📝 Note Added",
                description=f"Added note for {member.mention}",
                color=COLORS["success"],
                timestamp=datetime.now(timezone.utc)
            )
            embed.add_field(name="Note", value=note, inline=False)
            embed.add_field(name="Added By", value=interaction.user.mention, inline=True)
            
            await interaction.response.send_message(embed=embed)
            
            # Log to mod channel
            mod_channel = self.bot.get_channel(MOD_LOG_CHANNEL_ID)
            if mod_channel:
                log_embed = discord.Embed(
                    title="📝 Staff Note Added",
                    color=COLORS["info"],
                    timestamp=datetime.now(timezone.utc)
                )
                log_embed.add_field(name="User", value=f"{member.mention} ({member.id})", inline=False)
                log_embed.add_field(name="Added By", value=interaction.user.mention, inline=True)
                log_embed.add_field(name="Note", value=note, inline=False)
                await mod_channel.send(embed=log_embed)
        
        elif action == "view":
            # Get notes from database
            notes = self.bot.db.get_notes(member.id)
            
            if not notes:
                await interaction.response.send_message(
                    f"📝 No staff notes found for {member.mention}",
                    ephemeral=True
                )
                return
            
            embed = discord.Embed(
                title=f"📝 Staff Notes: {member.display_name}",
                description=f"Total Notes: {len(notes)}",
                color=COLORS["info"]
            )
            
            embed.set_thumbnail(url=member.display_avatar.url)
            
            # Show most recent notes
            for note_data in notes[:10]:
                note_id, user_id, note_text, added_by, timestamp = note_data
                
                added_by_member = interaction.guild.get_member(added_by)
                added_by_name = added_by_member.mention if added_by_member else f"<@{added_by}>"
                
                time_str = f"<t:{int(datetime.fromisoformat(timestamp).timestamp())}:R>"
                
                embed.add_field(
                    name=f"Note #{note_id}",
                    value=(
                        f"**Added by:** {added_by_name}\n"
                        f"**Date:** {time_str}\n"
                        f"**Note:** {note_text}"
                    ),
                    inline=False
                )
            
            if len(notes) > 10:
                embed.set_footer(text=f"Showing 10 of {len(notes)} notes")
            
            await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="activity", description="View recent staff activity")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(
        hours="Number of hours to look back (default: 24)"
    )
    async def recent_activity(self, interaction: discord.Interaction, hours: int = 24):
        """View recent staff activity"""
        if hours < 1 or hours > 168:  # Max 1 week
            await interaction.response.send_message("❌ Hours must be between 1 and 168 (1 week)!", ephemeral=True)
            return
        
        conn = self.bot.db.get_connection()
        cursor = conn.cursor()
        
        since = datetime.now(timezone.utc) - timedelta(hours=hours)
        
        cursor.execute("""
            SELECT * FROM staff_activity
            WHERE timestamp >= ?
            ORDER BY timestamp DESC
            LIMIT 20
        """, (since,))
        
        activities = cursor.fetchall()
        conn.close()
        
        if not activities:
            await interaction.response.send_message(
                f"📊 No staff activity recorded in the last {hours} hours.",
                ephemeral=True
            )
            return
        
        embed = discord.Embed(
            title="📊 Recent Staff Activity",
            description=f"Activity in the last {hours} hours (showing latest 20)",
            color=COLORS["info"],
            timestamp=datetime.now(timezone.utc)
        )
        
        action_emojis = {
            "verbal_warn": "⚠️",
            "warn": "🚨",
            "kick": "👢",
            "ban": "🔨",
            "unban": "✅",
            "timeout": "⏰",
            "ticket_create": "🎫",
            "ticket_close": "🔒",
            "loa_request": "📝",
            "loa_approve": "✅",
            "loa_deny": "❌",
            "note_add": "📝"
        }
        
        activity_text = []
        for activity in activities:
            activity_id, staff_id, action_type, target_user_id, details, timestamp = activity
            
            staff = interaction.guild.get_member(staff_id)
            staff_name = staff.mention if staff else f"<@{staff_id}>"
            
            target = ""
            if target_user_id:
                target_member = interaction.guild.get_member(target_user_id)
                target = f" → {target_member.mention if target_member else f'<@{target_user_id}>'}"
            
            emoji = action_emojis.get(action_type, "📋")
            action_display = action_type.replace("_", " ").title()
            
            time_str = f"<t:{int(datetime.fromisoformat(timestamp).timestamp())}:R>"
            
            activity_text.append(
                f"{emoji} **{action_display}**\n"
                f"└ {staff_name}{target} • {time_str}"
            )
        
        # Split into chunks if too long
        chunks = []
        current_chunk = ""
        
        for line in activity_text:
            if len(current_chunk) + len(line) > 1024:
                chunks.append(current_chunk)
                current_chunk = line
            else:
                current_chunk += "\n\n" + line if current_chunk else line
        
        if current_chunk:
            chunks.append(current_chunk)
        
        for i, chunk in enumerate(chunks[:3], 1):  # Max 3 fields
            embed.add_field(
                name=f"Activity (Part {i})" if len(chunks) > 1 else "Activity",
                value=chunk,
                inline=False
            )
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="inactivity", description="Check for inactive staff members")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(
        days="Number of days to check for inactivity (default: 7)"
    )
    async def check_inactivity(self, interaction: discord.Interaction, days: int = 7):
        """Check for inactive staff"""
        if days < 1 or days > 90:
            await interaction.response.send_message("❌ Days must be between 1 and 90!", ephemeral=True)
            return
        
        await interaction.response.defer()
        
        # Get all staff members
        staff_members = []
        for role_id in STAFF_ROLES.values():
            if role_id:
                role = interaction.guild.get_role(role_id)
                if role:
                    staff_members.extend(role.members)
        
        # Remove duplicates
        staff_members = list(set(staff_members))
        
        # Check activity for each
        inactive_staff = []
        
        for member in staff_members:
            stats = self.bot.db.get_staff_stats(member.id, days)
            
            total_actions = sum(count for _, count in stats)
            
            if total_actions == 0:
                # Check if they have an active LOA
                loas = self.bot.db.get_user_loas(member.id)
                has_active_loa = any(
                    loa[5] == 'approved' and 
                    datetime.fromisoformat(loa[2]) <= datetime.now(timezone.utc) <= datetime.fromisoformat(loa[3])
                    for loa in loas
                )
                
                inactive_staff.append((member, has_active_loa))
        
        if not inactive_staff:
            embed = discord.Embed(
                title="✅ No Inactive Staff",
                description=f"All staff members have been active in the last {days} days!",
                color=COLORS["success"]
            )
            await interaction.followup.send(embed=embed)
            return
        
        embed = discord.Embed(
            title="⚠️ Inactive Staff Report",
            description=f"Staff members with no recorded activity in the last {days} days",
            color=COLORS["warning"],
            timestamp=datetime.now(timezone.utc)
        )
        
        inactive_no_loa = []
        inactive_with_loa = []
        
        for member, has_loa in inactive_staff:
            if has_loa:
                inactive_with_loa.append(member.mention)
            else:
                inactive_no_loa.append(member.mention)
        
        if inactive_no_loa:
            embed.add_field(
                name=f"❌ Inactive ({len(inactive_no_loa)})",
                value="\n".join(inactive_no_loa[:20]),
                inline=False
            )
        
        if inactive_with_loa:
            embed.add_field(
                name=f"📝 On LOA ({len(inactive_with_loa)})",
                value="\n".join(inactive_with_loa[:20]),
                inline=False
            )
        
        embed.set_footer(text=f"Total inactive: {len(inactive_staff)} / {len(staff_members)} staff members")
        
        await interaction.followup.send(embed=embed)

async def setup(bot):
    await bot.add_cog(StaffManagement(bot))