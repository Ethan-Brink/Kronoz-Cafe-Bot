import discord
from discord import app_commands, ui
from discord.ext import commands
from config import EMBED_COLOR


class TicketSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="ticketsetup", description="Create a ticket panel (Staff only)")
    @app_commands.default_permissions(manage_guild=True)
    async def ticket_setup(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="🎟️ Kronoz Cafe Support",
            description="Click the button below to create a ticket!",
            color=EMBED_COLOR
        )
        embed.set_footer(text="Our staff will help you shortly.")

        view = TicketView()
        await interaction.response.send_message(embed=embed, view=view)

    # Auto ticket creation via button (handled in View below)


class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Create Ticket", style=discord.ButtonStyle.blurple, emoji="🎟️")
    async def create_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Create ticket channel
        guild = interaction.guild
        member = interaction.user

        # Check if user already has a ticket
        for channel in guild.channels:
            if channel.name.startswith("ticket-") and str(member.id) in channel.name:
                return await interaction.response.send_message("You already have an open ticket!", ephemeral=True)

        # Create channel
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            member: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }

        ticket_channel = await guild.create_text_channel(
            f"ticket-{member.name}", 
            overwrites=overwrites,
            reason=f"Ticket created by {member}"
        )

        embed = discord.Embed(
            title="🎟️ New Ticket",
            description=f"Welcome {member.mention}!\nStaff will be with you shortly.",
            color=EMBED_COLOR
        )
        embed.add_field(name="How to close", value="Use `/ticket close`", inline=False)

        await ticket_channel.send(embed=embed)
        await interaction.response.send_message(f"✅ Ticket created! {ticket_channel.mention}", ephemeral=True)


    @app_commands.command(name="ticketclose", description="Close the current ticket")
    async def close_ticket(self, interaction: discord.Interaction):
        if not interaction.channel.name.startswith("ticket-"):
            return await interaction.response.send_message("This is not a ticket channel!", ephemeral=True)

        await interaction.response.send_message("Closing ticket in 5 seconds...")
        await discord.utils.sleep_until(discord.utils.utcnow() + discord.timedelta(seconds=5))
        await interaction.channel.delete()


async def setup(bot):
    await bot.add_cog(TicketSystem(bot))