# cogs/roblox_integration.py - Roblox Integration Commands
import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime, timezone
from config import *

class RobloxIntegration(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @app_commands.command(name="linkroblox", description="Link your Discord account to your Roblox account")
    async def linkroblox(self, interaction: discord.Interaction, roblox_username: str):
        """Link Discord to Roblox account"""
        await interaction.response.defer(ephemeral=True)
        
        # Get Roblox user
        roblox_user = await self.bot.roblox.get_user_by_username(roblox_username)
        
        if not roblox_user:
            await interaction.followup.send(
                "❌ Roblox user not found. Please check the username and try again.",
                ephemeral=True
            )
            return
        
        # Check if another user is already linked to this Roblox account
        existing = self.bot.db.get_user_by_roblox_id(roblox_user["id"])
        if existing and existing[0] != interaction.user.id:
            await interaction.followup.send(
                f"❌ This Roblox account is already linked to another Discord user!",
                ephemeral=True
            )
            return
        
        # Save to database
        self.bot.db.create_or_update_user(
            discord_id=interaction.user.id,
            roblox_id=roblox_user["id"],
            roblox_username=roblox_user["name"]
        )
        
        # Get group rank if in group
        group_rank = None
        if ROBLOX_GROUP_ID:
            group_rank = await self.bot.roblox.get_group_rank(roblox_user["id"], ROBLOX_GROUP_ID)
        
        embed = discord.Embed(
            title="✅ Account Linked Successfully",
            description=f"Your Discord account has been linked to Roblox user **{roblox_user['name']}**",
            color=COLORS["success"],
            timestamp=datetime.now(timezone.utc)
        )
        
        embed.set_thumbnail(url=await self.bot.roblox.get_user_thumbnail(roblox_user["id"]))
        
        embed.add_field(name="Roblox Username", value=roblox_user["name"], inline=True)
        embed.add_field(name="Roblox ID", value=str(roblox_user["id"]), inline=True)
        embed.add_field(name="Display Name", value=roblox_user.get("displayName", roblox_user["name"]), inline=True)
        
        if group_rank:
            embed.add_field(name="Group Rank", value=group_rank.get("name", "Unknown"), inline=True)
        
        embed.add_field(
            name="🔗 Profile",
            value=f"[View on Roblox](https://www.roblox.com/users/{roblox_user['id']}/profile)",
            inline=False
        )
        
        await interaction.followup.send(embed=embed, ephemeral=True)
        
        # Log to mod channel
        mod_channel = self.bot.get_channel(MOD_LOG_CHANNEL_ID)
        if mod_channel:
            log_embed = discord.Embed(
                title="🔗 New Roblox Account Linked",
                color=COLORS["info"],
                timestamp=datetime.now(timezone.utc)
            )
            log_embed.add_field(name="Discord User", value=f"{interaction.user.mention} ({interaction.user.id})", inline=False)
            log_embed.add_field(name="Roblox User", value=f"{roblox_user['name']} ({roblox_user['id']})", inline=False)
            if group_rank:
                log_embed.add_field(name="Group Rank", value=group_rank.get("name", "Unknown"), inline=True)
            await mod_channel.send(embed=log_embed)
    
    @app_commands.command(name="finduser", description="Find a Roblox user and see if they're in our game")
    async def finduser(self, interaction: discord.Interaction, username: str):
        """Find Roblox user and check if they're in the game"""
        await interaction.response.defer()
        
        # Get Roblox user
        roblox_user = await self.bot.roblox.get_user_by_username(username)
        
        if not roblox_user:
            await interaction.followup.send("❌ Roblox user not found.")
            return
        
        user_id = roblox_user["id"]
        
        # Get presence info
        presence_data = await self.bot.roblox.get_user_presence([user_id])
        
        embed = discord.Embed(
            title=f"🔍 Roblox User: {roblox_user['name']}",
            color=COLORS["info"]
        )
        
        embed.set_thumbnail(url=await self.bot.roblox.get_user_thumbnail(user_id))
        
        embed.add_field(name="Username", value=roblox_user["name"], inline=True)
        embed.add_field(name="User ID", value=str(user_id), inline=True)
        embed.add_field(name="Display Name", value=roblox_user.get("displayName", roblox_user["name"]), inline=True)
        
        # Check if linked to Discord
        db_user = self.bot.db.get_user_by_roblox_id(user_id)
        if db_user:
            discord_user = interaction.guild.get_member(db_user[0])
            if discord_user:
                embed.add_field(
                    name="🔗 Linked Discord Account",
                    value=f"{discord_user.mention} ({discord_user.id})",
                    inline=False
                )
        
        # Get group info if applicable
        if ROBLOX_GROUP_ID:
            group_rank = await self.bot.roblox.get_group_rank(user_id, ROBLOX_GROUP_ID)
            if group_rank:
                embed.add_field(name="Group Rank", value=group_rank.get("name", "Unknown"), inline=True)
                embed.add_field(name="Rank Number", value=str(group_rank.get("rank", "Unknown")), inline=True)
        
        # Check presence
        if presence_data and presence_data.get("userPresences"):
            presence = presence_data["userPresences"][0]
            user_presence_type = presence.get("userPresenceType", 0)
            
            if user_presence_type == 0:
                embed.add_field(name="Status", value="🔴 Offline", inline=True)
            elif user_presence_type == 1:
                embed.add_field(name="Status", value="🟢 Online (Website)", inline=True)
            elif user_presence_type == 2:
                # User is in a game
                game_id = presence.get("placeId")
                
                if game_id == ROBLOX_GAME_ID:
                    # User is in OUR game!
                    embed.color = COLORS["success"]
                    embed.add_field(name="Status", value="🎮 **IN KRONOZ CAFE!**", inline=False)
                    
                    # Provide join link
                    job_id = presence.get("gameId")  # Server instance ID
                    if job_id:
                        join_link = f"https://www.roblox.com/games/start?placeId={ROBLOX_GAME_ID}&gameInstanceId={job_id}"
                        embed.add_field(
                            name="🔗 Join Their Server",
                            value=f"[Click here to join the same server!]({join_link})",
                            inline=False
                        )
                    
                    # Check server info
                    last_location = presence.get("lastLocation")
                    if last_location:
                        embed.add_field(name="Last Location", value=last_location, inline=True)
                else:
                    embed.add_field(name="Status", value="🎮 In Game (Different Game)", inline=True)
                    if game_id:
                        embed.add_field(name="Playing", value=f"Place ID: {game_id}", inline=True)
            elif user_presence_type == 3:
                embed.add_field(name="Status", value="🟡 Online (Roblox Studio)", inline=True)
        
        embed.add_field(
            name="🔗 Profile Link",
            value=f"[View on Roblox](https://www.roblox.com/users/{user_id}/profile)",
            inline=False
        )
        
        # If user is viewing their own linked account
        current_user_db = self.bot.db.get_user(interaction.user.id)
        if current_user_db and current_user_db[1] == user_id:
            embed.set_footer(text="✅ This is your linked Roblox account")
        
        await interaction.followup.send(embed=embed)
    
    @app_commands.command(name="userinfo", description="Get detailed information about a server member")
    @app_commands.checks.has_permissions(moderate_members=True)
    async def userinfo(self, interaction: discord.Interaction, member: discord.Member = None):
        """Get comprehensive user information"""
        member = member or interaction.user
        
        embed = discord.Embed(
            title=f"👤 User Info: {member.display_name}",
            color=member.color or COLORS["info"],
            timestamp=datetime.now(timezone.utc)
        )
        
        embed.set_thumbnail(url=member.display_avatar.url)
        
        # Basic info
        embed.add_field(name="Username", value=f"{member.name}", inline=True)
        embed.add_field(name="User ID", value=str(member.id), inline=True)
        embed.add_field(name="Nickname", value=member.nick or "None", inline=True)
        
        # Dates
        embed.add_field(name="Account Created", value=f"<t:{int(member.created_at.timestamp())}:R>", inline=True)
        embed.add_field(name="Joined Server", value=f"<t:{int(member.joined_at.timestamp())}:R>", inline=True)
        
        # Check database
        db_user = self.bot.db.get_user(member.id)
        
        # Roblox info
        if db_user and db_user[1]:  # Has Roblox linked
            roblox_user = await self.bot.roblox.get_user_by_id(db_user[1])
            if roblox_user:
                embed.add_field(
                    name="🎮 Roblox Account",
                    value=f"[{db_user[2]}](https://www.roblox.com/users/{db_user[1]}/profile)",
                    inline=False
                )
                
                # Check if in game
                presence_data = await self.bot.roblox.get_user_presence([db_user[1]])
                if presence_data and presence_data.get("userPresences"):
                    presence = presence_data["userPresences"][0]
                    if presence.get("userPresenceType") == 2 and presence.get("placeId") == ROBLOX_GAME_ID:
                        embed.add_field(name="Game Status", value="🟢 Currently in Kronoz Cafe!", inline=True)
        else:
            embed.add_field(name="🎮 Roblox Account", value="Not linked", inline=False)
        
        # Punishment history
        all_punishments = self.bot.db.get_all_punishments(member.id)
        active_punishments = [p for p in all_punishments if p[6] == 1]  # active = 1
        
        # Count by type
        verbal_count = len([p for p in active_punishments if p[2] == "verbal_warn"])
        warn_count = len([p for p in active_punishments if p[2] == "warn"])
        kick_count = len([p for p in all_punishments if p[2] == "kick"])
        ban_count = len([p for p in all_punishments if p[2] == "ban"])
        timeout_count = len([p for p in active_punishments if p[2] == "timeout"])
        
        punishment_text = []
        if verbal_count > 0:
            punishment_text.append(f"⚠️ Verbal Warns: {verbal_count}/{PUNISHMENT_THRESHOLDS['verbal_warns']}")
        if warn_count > 0:
            punishment_text.append(f"🚨 Warns: {warn_count}/{PUNISHMENT_THRESHOLDS['warns']}")
        if kick_count > 0:
            punishment_text.append(f"👢 Kicks: {kick_count}")
        if ban_count > 0:
            punishment_text.append(f"🔨 Bans: {ban_count}")
        if timeout_count > 0:
            punishment_text.append(f"⏰ Active Timeouts: {timeout_count}")
        
        embed.add_field(
            name="📋 Punishment History",
            value="\n".join(punishment_text) if punishment_text else "✅ Clean record",
            inline=False
        )
        
        # Staff notes
        notes = self.bot.db.get_notes(member.id)
        if notes and len(notes) > 0:
            embed.add_field(name="📝 Staff Notes", value=f"{len(notes)} note(s) on file", inline=True)
        
        # Roles
        roles = [role.mention for role in member.roles if role.name != "@everyone"]
        if roles:
            # Limit to first 10 roles to avoid embed limits
            role_display = ", ".join(roles[:10])
            if len(roles) > 10:
                role_display += f" *and {len(roles) - 10} more...*"
            embed.add_field(name=f"Roles ({len(roles)})", value=role_display, inline=False)
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="history", description="View detailed punishment history for a user")
    @app_commands.checks.has_permissions(moderate_members=True)
    async def history(self, interaction: discord.Interaction, member: discord.Member):
        """View punishment history"""
        all_punishments = self.bot.db.get_all_punishments(member.id)
        
        if not all_punishments:
            await interaction.response.send_message(
                f"✅ {member.mention} has a clean record - no punishments on file.",
                ephemeral=True
            )
            return
        
        embed = discord.Embed(
            title=f"📋 Punishment History: {member.display_name}",
            description=f"Total Punishments: **{len(all_punishments)}**",
            color=COLORS["warning"]
        )
        
        embed.set_thumbnail(url=member.display_avatar.url)
        
        # Group by type
        punishment_types = {}
        for p in all_punishments:
            p_type = p[2]
            if p_type not in punishment_types:
                punishment_types[p_type] = []
            punishment_types[p_type].append(p)
        
        # Show summary
        summary = []
        for p_type, punishments in punishment_types.items():
            active_count = len([p for p in punishments if p[6] == 1])
            total_count = len(punishments)
            
            if p_type == "verbal_warn":
                summary.append(f"⚠️ Verbal Warnings: {active_count} active / {total_count} total")
            elif p_type == "warn":
                summary.append(f"🚨 Formal Warnings: {active_count} active / {total_count} total")
            elif p_type == "kick":
                summary.append(f"👢 Kicks: {total_count}")
            elif p_type == "ban":
                summary.append(f"🔨 Bans: {total_count}")
            elif p_type == "timeout":
                summary.append(f"⏰ Timeouts: {active_count} active / {total_count} total")
        
        embed.add_field(name="Summary", value="\n".join(summary), inline=False)
        
        # Show recent punishments (last 5)
        recent = sorted(all_punishments, key=lambda x: x[5], reverse=True)[:5]
        
        recent_text = []
        for p in recent:
            p_id, user_id, p_type, reason, mod_id, timestamp, active, expires, removed_by, removed_at = p
            
            # Get moderator
            moderator = interaction.guild.get_member(mod_id)
            mod_name = moderator.mention if moderator else f"<@{mod_id}>"
            
            # Format timestamp
            ts = datetime.fromisoformat(timestamp)
            time_str = f"<t:{int(ts.timestamp())}:R>"
            
            # Status
            status = "✅ Active" if active == 1 else "❌ Removed"
            
            emoji_map = {
                "verbal_warn": "⚠️",
                "warn": "🚨",
                "kick": "👢",
                "ban": "🔨",
                "timeout": "⏰"
            }
            
            emoji = emoji_map.get(p_type, "📋")
            
            recent_text.append(
                f"{emoji} **{p_type.replace('_', ' ').title()}** ({status})\n"
                f"└ By {mod_name} • {time_str}\n"
                f"└ *{reason[:50]}{'...' if len(reason) > 50 else ''}*"
            )
        
        if recent_text:
            embed.add_field(name="Recent Punishments", value="\n\n".join(recent_text), inline=False)
        
        # Check for active warnings
        active_punishments = [p for p in all_punishments if p[6] == 1]
        if active_punishments:
            embed.set_footer(text=f"⚠️ {len(active_punishments)} active punishment(s)")
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="unlinkroblox", description="Unlink your Roblox account from Discord")
    async def unlinkroblox(self, interaction: discord.Interaction, member: discord.Member = None):
        """Unlink Roblox account (admins can unlink others)"""
        # If member specified, check if user has admin
        if member and member.id != interaction.user.id:
            if not interaction.user.guild_permissions.administrator:
                await interaction.response.send_message("❌ Only administrators can unlink other users!", ephemeral=True)
                return
            target = member
        else:
            target = interaction.user
        
        db_user = self.bot.db.get_user(target.id)
        
        if not db_user or not db_user[1]:
            await interaction.response.send_message(
                f"❌ {target.mention} doesn't have a linked Roblox account.",
                ephemeral=True
            )
            return
        
        # Unlink
        self.bot.db.create_or_update_user(target.id, None, None)
        
        embed = discord.Embed(
            title="✅ Roblox Account Unlinked",
            description=f"Roblox account has been unlinked from {target.mention}",
            color=COLORS["success"]
        )
        
        if member and member.id != interaction.user.id:
            embed.set_footer(text=f"Unlinked by {interaction.user}")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(RobloxIntegration(bot))