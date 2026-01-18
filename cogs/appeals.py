# cogs/appeals.py - Appeal System
import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime, timezone
from config import *
from typing import Optional

class AppealView(discord.ui.View):
    def __init__(self, appeal_id: int):
        super().__init__(timeout=None)
        self.appeal_id = appeal_id
    
    @discord.ui.button(label="Approve Appeal", style=discord.ButtonStyle.green, custom_id="appeal:approve", emoji="✅")
    async def approve_appeal(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ Only administrators can review appeals!", ephemeral=True)
            return
        
        # Get appeal data
        conn = interaction.client.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM appeals WHERE id = ?", (self.appeal_id,))
        appeal_data = cursor.fetchone()
        conn.close()
        
        if not appeal_data:
            await interaction.response.send_message("❌ Appeal not found!", ephemeral=True)
            return
        
        appeal_id, user_id, punishment_id, appeal_text, status, reviewed_by, reviewed_at, decision, created_at = appeal_data
        
        if status != 'pending':
            await interaction.response.send_message(f"❌ This appeal has already been {status}!", ephemeral=True)
            return
        
        # Show modal for decision reason
        modal = AppealDecisionModal(self.appeal_id, user_id, punishment_id, "approve")
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="Deny Appeal", style=discord.ButtonStyle.red, custom_id="appeal:deny", emoji="❌")
    async def deny_appeal(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ Only administrators can review appeals!", ephemeral=True)
            return
        
        # Get appeal data
        conn = interaction.client.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM appeals WHERE id = ?", (self.appeal_id,))
        appeal_data = cursor.fetchone()
        conn.close()
        
        if not appeal_data:
            await interaction.response.send_message("❌ Appeal not found!", ephemeral=True)
            return
        
        appeal_id, user_id, punishment_id, appeal_text, status, reviewed_by, reviewed_at, decision, created_at = appeal_data
        
        if status != 'pending':
            await interaction.response.send_message(f"❌ This appeal has already been {status}!", ephemeral=True)
            return
        
        # Show modal for decision reason
        modal = AppealDecisionModal(self.appeal_id, user_id, punishment_id, "deny")
        await interaction.response.send_modal(modal)

class AppealDecisionModal(discord.ui.Modal, title="Appeal Decision"):
    def __init__(self, appeal_id: int, user_id: int, punishment_id: int, action: str):
        super().__init__()
        self.appeal_id = appeal_id
        self.user_id = user_id
        self.punishment_id = punishment_id
        self.action = action
        
        self.decision_reason = discord.ui.TextInput(
            label=f"Reason for {action}ing appeal",
            style=discord.TextStyle.paragraph,
            placeholder="Explain your decision...",
            required=True,
            max_length=1000
        )
        self.add_item(self.decision_reason)
    
    async def on_submit(self, interaction: discord.Interaction):
        bot = interaction.client
        reason = self.decision_reason.value
        
        # Update appeal status
        bot.db.update_appeal(self.appeal_id, self.action + "d", interaction.user.id, reason)
        
        # Get punishment info
        punishment_data = bot.db.get_punishment_by_id(self.punishment_id)
        
        if self.action == "approve":
            # Remove the punishment
            bot.db.remove_punishment(self.punishment_id, interaction.user.id)
            
            # If it was a ban, unban the user
            if punishment_data and punishment_data[2] == "ban":
                try:
                    user = await bot.fetch_user(self.user_id)
                    await interaction.guild.unban(user, reason=f"Appeal approved by {interaction.user}")
                except:
                    pass
            
            color = COLORS["success"]
            status_text = "✅ Approved"
        else:
            color = COLORS["error"]
            status_text = "❌ Denied"
        
        # Send response
        embed = discord.Embed(
            title=f"{status_text} - Appeal #{self.appeal_id}",
            description=f"Appeal has been {self.action}d",
            color=color,
            timestamp=datetime.now(timezone.utc)
        )
        
        member = interaction.guild.get_member(self.user_id)
        embed.add_field(name="User", value=member.mention if member else f"<@{self.user_id}>", inline=True)
        embed.add_field(name="Reviewed By", value=interaction.user.mention, inline=True)
        embed.add_field(name="Decision", value=reason, inline=False)
        
        if punishment_data:
            p_type = punishment_data[2].replace("_", " ").title()
            embed.add_field(name="Original Punishment", value=p_type, inline=True)
            embed.add_field(name="Punishment Reason", value=punishment_data[3], inline=False)
        
        await interaction.response.send_message(embed=embed)
        
        # Update the original appeal message
        try:
            message = interaction.message
            for item in message.components:
                for button in item.children:
                    button.disabled = True
            
            original_embed = message.embeds[0]
            original_embed.color = color
            original_embed.title = f"{status_text} - {original_embed.title}"
            original_embed.add_field(name="Status", value=f"{status_text} by {interaction.user.mention}", inline=False)
            
            await message.edit(embed=original_embed, view=None)
        except:
            pass
        
        # Notify user
        if member:
            try:
                dm_embed = discord.Embed(
                    title=f"Appeal {self.action.title()}d",
                    description=f"Your appeal for punishment has been {self.action}d",
                    color=color,
                    timestamp=datetime.now(timezone.utc)
                )
                
                dm_embed.add_field(name="Decision", value=reason, inline=False)
                dm_embed.add_field(name="Reviewed By", value=interaction.user.name, inline=True)
                
                if self.action == "approve":
                    dm_embed.add_field(
                        name="✅ What This Means",
                        value="Your punishment has been removed from your record.",
                        inline=False
                    )
                else:
                    dm_embed.add_field(
                        name="❌ What This Means",
                        value="Your punishment remains active. If you have additional evidence, you may submit another appeal in the future.",
                        inline=False
                    )
                
                await member.send(embed=dm_embed)
            except:
                pass
        
        # Log to mod channel
        mod_channel = bot.get_channel(MOD_LOG_CHANNEL_ID)
        if mod_channel and mod_channel.id != interaction.channel.id:
            await mod_channel.send(embed=embed)
        
        bot.db.log_staff_action(interaction.user.id, f"appeal_{self.action}", self.user_id, f"Appeal #{self.appeal_id}")

class Appeals(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @app_commands.command(name="appeal", description="Appeal a punishment (warn, kick, or ban)")
    @app_commands.describe(
        punishment_type="Type of punishment you're appealing",
        reason="Why should this punishment be removed?"
    )
    @app_commands.choices(punishment_type=[
        app_commands.Choice(name="Verbal Warning", value="verbal_warn"),
        app_commands.Choice(name="Formal Warning", value="warn"),
        app_commands.Choice(name="Kick", value="kick"),
        app_commands.Choice(name="Ban", value="ban"),
        app_commands.Choice(name="Timeout", value="timeout")
    ])
    async def appeal(self, interaction: discord.Interaction, punishment_type: str, reason: str):
        """Submit an appeal for a punishment"""
        
        if len(reason) < 20:
            await interaction.response.send_message(
                "❌ Appeal reason must be at least 20 characters. Please provide a detailed explanation.",
                ephemeral=True
            )
            return
        
        if len(reason) > 1000:
            await interaction.response.send_message(
                "❌ Appeal reason is too long! Maximum 1000 characters.",
                ephemeral=True
            )
            return
        
        # Get user's active punishments of this type
        punishments = self.bot.db.get_active_punishments(interaction.user.id, punishment_type)
        
        if not punishments:
            await interaction.response.send_message(
                f"❌ You don't have any active {punishment_type.replace('_', ' ')}s to appeal!",
                ephemeral=True
            )
            return
        
        # Get the most recent punishment
        punishment = punishments[0]
        punishment_id = punishment[0]
        
        # Check if already appealed
        conn = self.bot.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM appeals 
            WHERE user_id = ? AND punishment_id = ? AND status = 'pending'
        """, (interaction.user.id, punishment_id))
        existing_appeal = cursor.fetchone()
        conn.close()
        
        if existing_appeal:
            await interaction.response.send_message(
                "❌ You already have a pending appeal for this punishment! Please wait for a decision.",
                ephemeral=True
            )
            return
        
        # Create appeal
        appeal_id = self.bot.db.create_appeal(interaction.user.id, punishment_id, reason)
        
        # Send confirmation to user
        confirm_embed = discord.Embed(
            title="✅ Appeal Submitted",
            description="Your appeal has been submitted for review by administrators.",
            color=COLORS["success"],
            timestamp=datetime.now(timezone.utc)
        )
        
        confirm_embed.add_field(name="Appeal ID", value=f"#{appeal_id}", inline=True)
        confirm_embed.add_field(name="Punishment Type", value=punishment_type.replace("_", " ").title(), inline=True)
        confirm_embed.add_field(name="Your Reason", value=reason, inline=False)
        confirm_embed.set_footer(text="You will be notified when your appeal is reviewed")
        
        await interaction.response.send_message(embed=confirm_embed, ephemeral=True)
        
        # Get punishment details
        moderator_id = punishment[4]
        punishment_reason = punishment[3]
        punishment_time = punishment[5]
        
        moderator = interaction.guild.get_member(moderator_id)
        mod_name = moderator.mention if moderator else f"<@{moderator_id}>"
        
        # Send to appeal channel or mod log
        if APPEAL_CHANNEL_ID:
            appeal_channel = self.bot.get_channel(APPEAL_CHANNEL_ID)
        else:
            appeal_channel = self.bot.get_channel(MOD_LOG_CHANNEL_ID)
        
        if appeal_channel:
            appeal_embed = discord.Embed(
                title=f"📝 New Appeal - #{appeal_id}",
                description=f"{interaction.user.mention} has submitted an appeal",
                color=COLORS["warning"],
                timestamp=datetime.now(timezone.utc)
            )
            
            appeal_embed.set_thumbnail(url=interaction.user.display_avatar.url)
            
            appeal_embed.add_field(
                name="User",
                value=f"{interaction.user.mention}\n{interaction.user.name}\nID: {interaction.user.id}",
                inline=True
            )
            
            appeal_embed.add_field(
                name="Punishment Type",
                value=punishment_type.replace("_", " ").title(),
                inline=True
            )
            
            appeal_embed.add_field(
                name="Issued By",
                value=mod_name,
                inline=True
            )
            
            appeal_embed.add_field(
                name="Original Punishment Reason",
                value=punishment_reason,
                inline=False
            )
            
            appeal_embed.add_field(
                name="Appeal Reason",
                value=reason,
                inline=False
            )
            
            ts = datetime.fromisoformat(punishment_time)
            appeal_embed.add_field(
                name="Punishment Date",
                value=f"<t:{int(ts.timestamp())}:R>",
                inline=True
            )
            
            appeal_embed.set_footer(text="Use the buttons below to review this appeal")
            
            # Send with buttons
            view = AppealView(appeal_id)
            await appeal_channel.send(embed=appeal_embed, view=view)
        
        self.bot.db.log_staff_action(interaction.user.id, "appeal_submit", None, f"Appeal #{appeal_id} for {punishment_type}")
    
    @app_commands.command(name="myappeals", description="View your appeal history")
    async def my_appeals(self, interaction: discord.Interaction):
        """View personal appeal history"""
        conn = self.bot.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM appeals 
            WHERE user_id = ?
            ORDER BY created_at DESC
        """, (interaction.user.id,))
        appeals = cursor.fetchall()
        conn.close()
        
        if not appeals:
            await interaction.response.send_message(
                "You have no appeal history.",
                ephemeral=True
            )
            return
        
        embed = discord.Embed(
            title="📋 Your Appeal History",
            description=f"Total Appeals: {len(appeals)}",
            color=COLORS["info"]
        )
        
        status_emojis = {
            'pending': '⏳',
            'approved': '✅',
            'denied': '❌'
        }
        
        for appeal in appeals[:5]:  # Show last 5
            appeal_id, user_id, punishment_id, appeal_text, status, reviewed_by, reviewed_at, decision, created_at = appeal
            
            # Get punishment info
            punishment = self.bot.db.get_punishment_by_id(punishment_id)
            p_type = punishment[2].replace("_", " ").title() if punishment else "Unknown"
            
            status_emoji = status_emojis.get(status, '📋')
            
            field_value = f"**Status:** {status_emoji} {status.title()}\n"
            field_value += f"**Punishment:** {p_type}\n"
            field_value += f"**Submitted:** <t:{int(datetime.fromisoformat(created_at).timestamp())}:R>\n"
            
            if reviewed_at:
                field_value += f"**Reviewed:** <t:{int(datetime.fromisoformat(reviewed_at).timestamp())}:R>\n"
            
            if decision and status != 'pending':
                field_value += f"**Decision:** {decision[:100]}{'...' if len(decision) > 100 else ''}"
            
            embed.add_field(
                name=f"Appeal #{appeal_id}",
                value=field_value,
                inline=False
            )
        
        if len(appeals) > 5:
            embed.set_footer(text=f"Showing 5 of {len(appeals)} appeals")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @app_commands.command(name="viewappeals", description="View all pending appeals (Admin only)")
    @app_commands.checks.has_permissions(administrator=True)
    async def view_appeals(self, interaction: discord.Interaction):
        """View all pending appeals"""
        pending_appeals = self.bot.db.get_pending_appeals()
        
        if not pending_appeals:
            await interaction.response.send_message(
                "✅ No pending appeals!",
                ephemeral=True
            )
            return
        
        embed = discord.Embed(
            title="📋 Pending Appeals",
            description=f"Total Pending: {len(pending_appeals)}",
            color=COLORS["warning"]
        )
        
        for appeal in pending_appeals[:10]:  # Show max 10
            appeal_id, user_id, punishment_id, appeal_text, status, reviewed_by, reviewed_at, decision, created_at = appeal
            
            member = interaction.guild.get_member(user_id)
            user_name = member.mention if member else f"<@{user_id}>"
            
            # Get punishment info
            punishment = self.bot.db.get_punishment_by_id(punishment_id)
            if punishment:
                p_type = punishment[2].replace("_", " ").title()
                p_reason = punishment[3]
                
                embed.add_field(
                    name=f"Appeal #{appeal_id} - {member.name if member else 'Unknown User'}",
                    value=(
                        f"**User:** {user_name}\n"
                        f"**Punishment:** {p_type}\n"
                        f"**Original Reason:** {p_reason[:100]}{'...' if len(p_reason) > 100 else ''}\n"
                        f"**Appeal:** {appeal_text[:100]}{'...' if len(appeal_text) > 100 else ''}\n"
                        f"**Submitted:** <t:{int(datetime.fromisoformat(created_at).timestamp())}:R>"
                    ),
                    inline=False
                )
        
        if len(pending_appeals) > 10:
            embed.set_footer(text=f"Showing 10 of {len(pending_appeals)} pending appeals")
        
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(Appeals(bot))