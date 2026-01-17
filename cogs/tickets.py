# cogs/tickets.py - Ticket System with Button UI
import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime, timezone
import io
from config import *

TICKET_PROMPT_CHANNEL_ID = 1458731578892095529

class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    
    @discord.ui.button(label="General Support", style=discord.ButtonStyle.green, custom_id="ticket:general", emoji="💬")
    async def general_support(self, interaction: discord.Interaction, button: discord.ui.Button):
        await create_ticket(interaction, "General Support", "general")
    
    @discord.ui.button(label="Player Report", style=discord.ButtonStyle.red, custom_id="ticket:report", emoji="🚨")
    async def player_report(self, interaction: discord.Interaction, button: discord.ui.Button):
        await create_ticket(interaction, "Player Report", "report")
    
    @discord.ui.button(label="Appeal Support", style=discord.ButtonStyle.blurple, custom_id="ticket:appeal", emoji="📝")
    async def appeal_support(self, interaction: discord.Interaction, button: discord.ui.Button):
        await create_ticket(interaction, "Appeal Support", "appeal")
    
    @discord.ui.button(label="Development Support", style=discord.ButtonStyle.gray, custom_id="ticket:dev", emoji="⚙️")
    async def dev_support(self, interaction: discord.Interaction, button: discord.ui.Button):
        await create_ticket(interaction, "Development Support", "dev")

class TicketControlView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    
    @discord.ui.button(label="Close Ticket", style=discord.ButtonStyle.red, custom_id="ticket:close", emoji="🔒")
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Check if user is staff or ticket owner
        if not interaction.user.guild_permissions.manage_messages:
            ticket_data = interaction.client.db.get_ticket_by_channel(interaction.channel.id)
            if not ticket_data or ticket_data[2] != interaction.user.id:
                await interaction.response.send_message("❌ Only staff or the ticket owner can close this ticket!", ephemeral=True)
                return
        
        await interaction.response.send_message("🔒 Closing ticket and generating transcript...", ephemeral=True)
        await close_ticket(interaction)

async def create_ticket(interaction: discord.Interaction, category_name: str, category_key: str):
    """Create a new ticket"""
    bot = interaction.client
    
    # Check cooldown
    existing_tickets = bot.db.get_connection().execute(
        "SELECT * FROM tickets WHERE user_id = ? AND status = 'open'",
        (interaction.user.id,)
    ).fetchall()
    
    if len(existing_tickets) >= 3:
        await interaction.response.send_message(
            "❌ You already have 3 open tickets! Please close one before opening another.",
            ephemeral=True
        )
        return
    
    await interaction.response.defer(ephemeral=True)
    
    try:
        # Create ticket channel
        guild = interaction.guild
        category = discord.utils.get(guild.categories, id=TICKET_CATEGORY_ID)
        
        if not category:
            # Create category if it doesn't exist
            category = await guild.create_category("📂 Tickets")
            await category.set_permissions(guild.default_role, view_channel=False)
            await category.set_permissions(guild.me, view_channel=True, send_messages=True, manage_channels=True)
        
        # Get ticket number
        ticket_number = bot.db.create_ticket(
            user_id=interaction.user.id,
            channel_id=0,  # Will update after creating channel
            category=category_key,
            subject=category_name
        )
        
        # Create channel
        channel_name = f"ticket-{ticket_number:04d}"
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
            guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True, manage_messages=True)
        }
        
        # Add staff roles
        for role_id in STAFF_ROLES.values():
            if role_id:
                role = guild.get_role(role_id)
                if role:
                    overwrites[role] = discord.PermissionOverwrite(view_channel=True, send_messages=True)
        
        channel = await category.create_text_channel(
            name=channel_name,
            overwrites=overwrites
        )
        
        # Update ticket with channel ID
        conn = bot.db.get_connection()
        conn.execute("UPDATE tickets SET channel_id = ? WHERE ticket_number = ?", (channel.id, ticket_number))
        conn.commit()
        conn.close()
        
        # Create ticket embed
        embed = discord.Embed(
            title=f"🎫 Ticket #{ticket_number:04d} - {category_name}",
            description=f"Thank you for opening a ticket, {interaction.user.mention}!\n\nA staff member will be with you shortly.",
            color=COLORS["primary"],
            timestamp=datetime.now(timezone.utc)
        )
        
        embed.add_field(
            name="📋 Category",
            value=category_name,
            inline=True
        )
        
        embed.add_field(
            name="👤 Opened By",
            value=interaction.user.mention,
            inline=True
        )
        
        if category_key == "appeal":
            embed.add_field(
                name="ℹ️ Appeal Information",
                value="Please provide:\n• What punishment you're appealing\n• Why you believe it should be removed\n• Any evidence to support your appeal",
                inline=False
            )
        elif category_key == "report":
            embed.add_field(
                name="ℹ️ Report Information",
                value="Please provide:\n• Player's Roblox username\n• What rule they broke\n• Evidence (screenshots/videos)\n• When it happened",
                inline=False
            )
        
        embed.set_footer(text="Click the 🔒 button below to close this ticket")
        
        # Send ticket message with controls
        await channel.send(
            content=f"{interaction.user.mention}",
            embed=embed,
            view=TicketControlView()
        )
        
        # Log ticket creation
        bot.db.log_staff_action(interaction.user.id, "ticket_create", None, f"Ticket #{ticket_number:04d} - {category_name}")
        
        # Log to mod channel
        mod_channel = bot.get_channel(MOD_LOG_CHANNEL_ID)
        if mod_channel:
            log_embed = discord.Embed(
                title="🎫 New Ticket Created",
                color=COLORS["info"],
                timestamp=datetime.now(timezone.utc)
            )
            log_embed.add_field(name="Ticket", value=f"#{ticket_number:04d}", inline=True)
            log_embed.add_field(name="Category", value=category_name, inline=True)
            log_embed.add_field(name="User", value=interaction.user.mention, inline=True)
            log_embed.add_field(name="Channel", value=channel.mention, inline=True)
            await mod_channel.send(embed=log_embed)
        
        await interaction.followup.send(
            f"✅ Ticket created! {channel.mention}",
            ephemeral=True
        )
        
    except Exception as e:
        print(f"Error creating ticket: {e}")
        await interaction.followup.send(
            f"❌ Failed to create ticket: {str(e)}",
            ephemeral=True
        )

async def close_ticket(interaction: discord.Interaction):
    """Close ticket and create transcript"""
    bot = interaction.client
    channel = interaction.channel
    
    # Get ticket data
    ticket_data = bot.db.get_ticket_by_channel(channel.id)
    
    if not ticket_data:
        await interaction.followup.send("❌ This is not a ticket channel!", ephemeral=True)
        return
    
    ticket_id, ticket_number, user_id, channel_id, category, subject, status, created_at, closed_at, closed_by, handled_by = ticket_data
    
    if status == "closed":
        await interaction.followup.send("❌ This ticket is already closed!", ephemeral=True)
        return
    
    # Generate transcript
    messages = []
    async for message in channel.history(limit=500, oldest_first=True):
        timestamp = message.created_at.strftime("%Y-%m-%d %H:%M:%S UTC")
        author = f"{message.author.name}#{message.author.discriminator}"
        content = message.content or "[No text content]"
        
        # Include attachments
        if message.attachments:
            content += "\n[Attachments: " + ", ".join([a.url for a in message.attachments]) + "]"
        
        messages.append(f"[{timestamp}] {author}: {content}")
    
    transcript = "\n".join(messages)
    transcript_file = discord.File(
        io.BytesIO(transcript.encode()),
        filename=f"ticket-{ticket_number:04d}-transcript.txt"
    )
    
    # Close in database
    bot.db.close_ticket(channel.id, interaction.user.id)
    bot.db.log_staff_action(interaction.user.id, "ticket_close", user_id, f"Ticket #{ticket_number:04d}")
    
    # Send transcript to mod channel
    mod_channel = bot.get_channel(MOD_LOG_CHANNEL_ID)
    if mod_channel:
        embed = discord.Embed(
            title=f"🔒 Ticket Closed - #{ticket_number:04d}",
            color=COLORS["error"],
            timestamp=datetime.now(timezone.utc)
        )
        embed.add_field(name="Category", value=subject or category, inline=True)
        
        ticket_user = interaction.guild.get_member(user_id)
        embed.add_field(name="Opened By", value=ticket_user.mention if ticket_user else f"<@{user_id}>", inline=True)
        embed.add_field(name="Closed By", value=interaction.user.mention, inline=True)
        
        # Calculate duration
        created = datetime.fromisoformat(created_at)
        duration = datetime.now(timezone.utc) - created
        hours = int(duration.total_seconds() // 3600)
        minutes = int((duration.total_seconds() % 3600) // 60)
        embed.add_field(name="Duration", value=f"{hours}h {minutes}m", inline=True)
        
        await mod_channel.send(embed=embed, file=transcript_file)
    
    # Send closing message
    embed = discord.Embed(
        title="🔒 Ticket Closed",
        description=f"This ticket has been closed by {interaction.user.mention}",
        color=COLORS["error"],
        timestamp=datetime.now(timezone.utc)
    )
    embed.add_field(name="Ticket", value=f"#{ticket_number:04d}", inline=True)
    embed.add_field(name="Category", value=subject or category, inline=True)
    embed.set_footer(text="This channel will be deleted in 10 seconds...")
    
    await channel.send(embed=embed)
    
    # Try to DM the user with transcript
    try:
        ticket_user = interaction.guild.get_member(user_id)
        if ticket_user:
            dm_embed = discord.Embed(
                title=f"📋 Ticket #{ticket_number:04d} Transcript",
                description=f"Your ticket in **{interaction.guild.name}** has been closed.",
                color=COLORS["info"]
            )
            dm_embed.add_field(name="Category", value=subject or category, inline=True)
            dm_embed.add_field(name="Closed By", value=interaction.user.mention, inline=True)
            
            transcript_file_dm = discord.File(
                io.BytesIO(transcript.encode()),
                filename=f"ticket-{ticket_number:04d}-transcript.txt"
            )
            
            await ticket_user.send(embed=dm_embed, file=transcript_file_dm)
    except:
        pass
    
    # Delete channel after delay
    await asyncio.sleep(10)
    await channel.delete(reason=f"Ticket #{ticket_number:04d} closed by {interaction.user}")

class Tickets(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @commands.Cog.listener()
    async def on_ready(self):
        """Send ticket prompt on bot startup"""
        # Add persistent views
        self.bot.add_view(TicketView())
        self.bot.add_view(TicketControlView())
        
        # Send ticket prompt to designated channel
        await self.send_ticket_prompt()
    
    async def send_ticket_prompt(self):
        """Send or update the ticket creation message"""
        channel = self.bot.get_channel(TICKET_PROMPT_CHANNEL_ID)
        
        if not channel:
            print(f"⚠️ Ticket prompt channel {TICKET_PROMPT_CHANNEL_ID} not found!")
            return
        
        embed = discord.Embed(
            title="🎫 Kronoz Cafe Support Tickets",
            description=(
                "Need help? Create a support ticket by clicking one of the buttons below.\n\n"
                "**Available Categories:**\n"
                "💬 **General Support** - General questions and assistance\n"
                "🚨 **Player Report** - Report rule-breaking players\n"
                "📝 **Appeal Support** - Appeal warnings or bans\n"
                "⚙️ **Development Support** - Technical or development questions"
            ),
            color=COLORS["primary"]
        )
        
        embed.add_field(
            name="📋 Guidelines",
            value=(
                "• Only create tickets for legitimate issues\n"
                "• Be patient - staff will respond soon\n"
                "• Provide all relevant information\n"
                "• Maximum 3 open tickets per user"
            ),
            inline=False
        )
        
        embed.set_footer(text="Kronoz Cafe Support Team")
        embed.set_thumbnail(url=self.bot.user.display_avatar.url if self.bot.user else None)
        
        # Try to find existing message and edit, otherwise send new
        try:
            # Check last 10 messages for existing prompt
            async for message in channel.history(limit=10):
                if message.author == self.bot.user and message.embeds:
                    if "Support Tickets" in message.embeds[0].title:
                        await message.edit(embed=embed, view=TicketView())
                        print(f"✅ Updated ticket prompt in #{channel.name}")
                        return
            
            # No existing message found, send new one
            await channel.send(embed=embed, view=TicketView())
            print(f"✅ Sent ticket prompt to #{channel.name}")
            
        except Exception as e:
            print(f"❌ Error sending ticket prompt: {e}")
    
    @app_commands.command(name="add", description="Add a user to the current ticket")
    @app_commands.checks.has_permissions(manage_messages=True)
    async def add_user(self, interaction: discord.Interaction, member: discord.Member):
        """Add user to ticket"""
        ticket_data = self.bot.db.get_ticket_by_channel(interaction.channel.id)
        
        if not ticket_data:
            await interaction.response.send_message("❌ This is not a ticket channel!", ephemeral=True)
            return
        
        try:
            await interaction.channel.set_permissions(
                member,
                view_channel=True,
                send_messages=True,
                read_message_history=True
            )
            
            await interaction.response.send_message(f"✅ Added {member.mention} to this ticket.")
            self.bot.db.log_staff_action(interaction.user.id, "ticket_add_user", member.id, f"Added to ticket {ticket_data[1]}")
            
        except Exception as e:
            await interaction.response.send_message(f"❌ Failed to add user: {str(e)}", ephemeral=True)
    
    @app_commands.command(name="remove", description="Remove a user from the current ticket")
    @app_commands.checks.has_permissions(manage_messages=True)
    async def remove_user(self, interaction: discord.Interaction, member: discord.Member):
        """Remove user from ticket"""
        ticket_data = self.bot.db.get_ticket_by_channel(interaction.channel.id)
        
        if not ticket_data:
            await interaction.response.send_message("❌ This is not a ticket channel!", ephemeral=True)
            return
        
        # Don't allow removing ticket owner
        if member.id == ticket_data[2]:
            await interaction.response.send_message("❌ Cannot remove the ticket owner!", ephemeral=True)
            return
        
        try:
            await interaction.channel.set_permissions(member, overwrite=None)
            await interaction.response.send_message(f"✅ Removed {member.mention} from this ticket.")
            self.bot.db.log_staff_action(interaction.user.id, "ticket_remove_user", member.id, f"Removed from ticket {ticket_data[1]}")
            
        except Exception as e:
            await interaction.response.send_message(f"❌ Failed to remove user: {str(e)}", ephemeral=True)
    
    @app_commands.command(name="close", description="Close the current ticket")
    async def close_ticket_command(self, interaction: discord.Interaction, reason: str = "No reason provided"):
        """Close ticket via command"""
        # Check if user is staff or ticket owner
        if not interaction.user.guild_permissions.manage_messages:
            ticket_data = self.bot.db.get_ticket_by_channel(interaction.channel.id)
            if not ticket_data or ticket_data[2] != interaction.user.id:
                await interaction.response.send_message("❌ Only staff or the ticket owner can close this ticket!", ephemeral=True)
                return
        
        await interaction.response.send_message(f"🔒 Closing ticket...\n**Reason:** {reason}")
        await close_ticket(interaction)
    
    @app_commands.command(name="ticketstats", description="View ticket statistics")
    @app_commands.checks.has_permissions(manage_messages=True)
    async def ticket_stats(self, interaction: discord.Interaction):
        """View ticket statistics"""
        conn = self.bot.db.get_connection()
        cursor = conn.cursor()
        
        # Total tickets
        cursor.execute("SELECT COUNT(*) FROM tickets")
        total_tickets = cursor.fetchone()[0]
        
        # Open tickets
        cursor.execute("SELECT COUNT(*) FROM tickets WHERE status = 'open'")
        open_tickets = cursor.fetchone()[0]
        
        # Closed tickets
        cursor.execute("SELECT COUNT(*) FROM tickets WHERE status = 'closed'")
        closed_tickets = cursor.fetchone()[0]
        
        # Tickets by category
        cursor.execute("""
            SELECT category, COUNT(*) as count
            FROM tickets
            GROUP BY category
            ORDER BY count DESC
        """)
        category_stats = cursor.fetchall()
        
        conn.close()
        
        embed = discord.Embed(
            title="📊 Ticket Statistics",
            color=COLORS["info"],
            timestamp=datetime.now(timezone.utc)
        )
        
        embed.add_field(name="Total Tickets", value=str(total_tickets), inline=True)
        embed.add_field(name="Open Tickets", value=str(open_tickets), inline=True)
        embed.add_field(name="Closed Tickets", value=str(closed_tickets), inline=True)
        
        if category_stats:
            category_text = "\n".join([f"{cat}: {count}" for cat, count in category_stats])
            embed.add_field(name="By Category", value=category_text, inline=False)
        
        await interaction.response.send_message(embed=embed)

import asyncio

async def setup(bot):
    await bot.add_cog(Tickets(bot))