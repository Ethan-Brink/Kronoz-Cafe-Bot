# cogs/fun.py - Fun & Engagement Features (NO DUPLICATE LEADERBOARD)
import discord
from discord.ext import commands
from discord import app_commands
import random
import asyncio
from datetime import datetime, timedelta
from typing import Optional

class Fun(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.trivia_active = {}
        self.polls = {}
    
    # Helper method for database
    def db_query(self, query, params=()):
        try:
            cursor = self.bot.db.cursor
            cursor.execute(query, params)
            self.bot.db.conn.commit()
            return cursor
        except Exception as e:
            print(f"Database error (fun): {e}")
            return None
    
    # 1. TRIVIA SYSTEM
    @app_commands.command(name="trivia", description="Start a trivia game in this channel")
    @app_commands.choices(category=[
        app_commands.Choice(name="General Knowledge", value="general"),
        app_commands.Choice(name="Gaming", value="gaming"),
        app_commands.Choice(name="Movies", value="movies"),
        app_commands.Choice(name="Science", value="science")
    ])
    async def trivia(self, interaction: discord.Interaction, category: str):
        if interaction.channel.id in self.trivia_active:
            await interaction.response.send_message("❌ A trivia game is already active in this channel!", ephemeral=True)
            return
        
        questions = {
            "general": [
                {"q": "What is the capital of France?", "a": ["Paris", "paris"], "choices": ["London", "Paris", "Berlin", "Madrid"]},
                {"q": "How many continents are there?", "a": ["7", "seven"], "choices": ["5", "6", "7", "8"]},
                {"q": "What is the largest ocean?", "a": ["Pacific", "pacific"], "choices": ["Atlantic", "Pacific", "Indian", "Arctic"]},
            ],
            "gaming": [
                {"q": "Which company created Minecraft?", "a": ["Mojang", "mojang"], "choices": ["Microsoft", "Mojang", "Epic Games", "Valve"]},
                {"q": "What year was Roblox released?", "a": ["2006"], "choices": ["2004", "2006", "2008", "2010"]},
                {"q": "What is the most played game on Steam?", "a": ["Counter-Strike", "CS2", "cs2"], "choices": ["Dota 2", "Counter-Strike", "PUBG", "GTA V"]},
            ],
            "movies": [
                {"q": "Who directed Inception?", "a": ["Christopher Nolan", "nolan"], "choices": ["Steven Spielberg", "Christopher Nolan", "James Cameron", "Quentin Tarantino"]},
                {"q": "What year was the first Toy Story released?", "a": ["1995"], "choices": ["1993", "1995", "1997", "1999"]},
            ],
            "science": [
                {"q": "What is the chemical symbol for gold?", "a": ["Au", "au"], "choices": ["Go", "Gd", "Au", "Ag"]},
                {"q": "How many planets are in our solar system?", "a": ["8", "eight"], "choices": ["7", "8", "9", "10"]},
            ]
        }
        
        question = random.choice(questions.get(category, questions["general"]))
        self.trivia_active[interaction.channel.id] = {"answer": question["a"], "answered": False}
        
        embed = discord.Embed(
            title="🎯 Trivia Time!",
            description=f"**Category:** {category.title()}\n\n**Question:**\n{question['q']}",
            color=discord.Color.blue()
        )
        
        if "choices" in question:
            choices_text = "\n".join([f"{chr(65+i)}. {choice}" for i, choice in enumerate(question["choices"])])
            embed.add_field(name="Choices", value=choices_text, inline=False)
        
        embed.set_footer(text="You have 30 seconds to answer! Type your answer below.")
        
        await interaction.response.send_message(embed=embed)
        
        # Wait for answer
        def check(m):
            return m.channel.id == interaction.channel.id and not m.author.bot
        
        try:
            msg = await self.bot.wait_for('message', timeout=30.0, check=check)
            
            if msg.content.lower() in [a.lower() for a in question["a"]]:
                self.trivia_active[interaction.channel.id]["answered"] = True
                
                winner_embed = discord.Embed(
                    title="🎉 Correct Answer!",
                    description=f"{msg.author.mention} got it right!\n**Answer:** {question['a'][0]}",
                    color=discord.Color.green()
                )
                await interaction.channel.send(embed=winner_embed)
                
                # Award points in database
                try:
                    self.db_query(
                        "INSERT INTO trivia_scores (user_id, points) VALUES (?, 1) ON CONFLICT(user_id) DO UPDATE SET points = points + 1",
                        (msg.author.id,)
                    )
                except:
                    pass
            else:
                timeout_embed = discord.Embed(
                    title="❌ Wrong Answer!",
                    description=f"The correct answer was: **{question['a'][0]}**",
                    color=discord.Color.red()
                )
                await interaction.channel.send(embed=timeout_embed)
                
        except asyncio.TimeoutError:
            timeout_embed = discord.Embed(
                title="⏰ Time's Up!",
                description=f"Nobody answered in time!\nThe correct answer was: **{question['a'][0]}**",
                color=discord.Color.orange()
            )
            await interaction.channel.send(embed=timeout_embed)
        
        finally:
            del self.trivia_active[interaction.channel.id]
    
    # 2. POLL SYSTEM
    @app_commands.command(name="poll", description="Create a poll with custom options")
    @app_commands.describe(
        question="The poll question",
        option1="First option",
        option2="Second option",
        option3="Third option (optional)",
        option4="Fourth option (optional)",
        duration="Poll duration in minutes (default: 60)"
    )
    async def poll(
        self, 
        interaction: discord.Interaction, 
        question: str,
        option1: str,
        option2: str,
        option3: Optional[str] = None,
        option4: Optional[str] = None,
        duration: int = 60
    ):
        options = [option1, option2]
        if option3:
            options.append(option3)
        if option4:
            options.append(option4)
        
        if len(options) > 10:
            await interaction.response.send_message("❌ Maximum 10 options allowed!", ephemeral=True)
            return
        
        # Emoji reactions
        emojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
        
        embed = discord.Embed(
            title="📊 Poll",
            description=f"**{question}**\n\n" + "\n".join([f"{emojis[i]} {opt}" for i, opt in enumerate(options)]),
            color=discord.Color.blue()
        )
        embed.set_footer(text=f"Poll ends in {duration} minutes | React to vote!")
        embed.timestamp = datetime.utcnow()
        
        await interaction.response.send_message(embed=embed)
        msg = await interaction.original_response()
        
        # Add reactions
        for i in range(len(options)):
            await msg.add_reaction(emojis[i])
        
        # Store poll data
        self.polls[msg.id] = {
            "question": question,
            "options": options,
            "end_time": datetime.utcnow() + timedelta(minutes=duration),
            "channel_id": interaction.channel.id
        }
        
        # Schedule poll end
        await asyncio.sleep(duration * 60)
        await self.end_poll(msg.id)
    
    async def end_poll(self, message_id: int):
        if message_id not in self.polls:
            return
        
        poll_data = self.polls[message_id]
        channel = self.bot.get_channel(poll_data["channel_id"])
        
        try:
            message = await channel.fetch_message(message_id)
            
            # Count reactions
            results = {}
            emojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
            
            for i, option in enumerate(poll_data["options"]):
                reaction = discord.utils.get(message.reactions, emoji=emojis[i])
                count = reaction.count - 1 if reaction else 0
                results[option] = count
            
            # Create results embed
            total_votes = sum(results.values())
            results_text = ""
            
            for option, count in results.items():
                percentage = (count / total_votes * 100) if total_votes > 0 else 0
                bar = "█" * int(percentage / 5)
                results_text += f"**{option}**\n{bar} {count} votes ({percentage:.1f}%)\n\n"
            
            embed = discord.Embed(
                title="📊 Poll Results",
                description=f"**{poll_data['question']}**\n\n{results_text}\n**Total Votes:** {total_votes}",
                color=discord.Color.green()
            )
            embed.set_footer(text="Poll has ended")
            
            await channel.send(embed=embed)
            
        except Exception as e:
            print(f"Error ending poll: {e}")
        
        finally:
            del self.polls[message_id]
    
    # 3. 8BALL COMMAND
    @app_commands.command(name="8ball", description="Ask the magic 8-ball a question")
    @app_commands.describe(question="Your yes/no question")
    async def eightball(self, interaction: discord.Interaction, question: str):
        responses = [
            "Yes, definitely! ✅",
            "It is certain. 💯",
            "Without a doubt! 👍",
            "You may rely on it. 🤝",
            "As I see it, yes. 👀",
            "Most likely. 📈",
            "Outlook good. 🌟",
            "Signs point to yes. ➡️",
            "Reply hazy, try again. 🌫️",
            "Ask again later. ⏰",
            "Better not tell you now. 🤐",
            "Cannot predict now. 🔮",
            "Concentrate and ask again. 🧘",
            "Don't count on it. ❌",
            "My reply is no. 🚫",
            "My sources say no. 📰",
            "Outlook not so good. 📉",
            "Very doubtful. 🤔"
        ]
        
        embed = discord.Embed(
            title="🎱 Magic 8-Ball",
            color=discord.Color.purple()
        )
        embed.add_field(name="Question", value=question, inline=False)
        embed.add_field(name="Answer", value=random.choice(responses), inline=False)
        embed.set_footer(text=f"Asked by {interaction.user.display_name}")
        
        await interaction.response.send_message(embed=embed)
    
    # 4. COIN FLIP
    @app_commands.command(name="coinflip", description="Flip a coin")
    async def coinflip(self, interaction: discord.Interaction):
        result = random.choice(["Heads", "Tails"])
        emoji = "🪙"
        
        embed = discord.Embed(
            title=f"{emoji} Coin Flip",
            description=f"The coin landed on... **{result}**!",
            color=discord.Color.gold()
        )
        
        await interaction.response.send_message(embed=embed)
    
    # 5. DICE ROLL
    @app_commands.command(name="roll", description="Roll dice (e.g., 2d6 for two six-sided dice)")
    @app_commands.describe(dice="Dice notation (e.g., 2d6, 1d20)")
    async def roll(self, interaction: discord.Interaction, dice: str = "1d6"):
        try:
            parts = dice.lower().split('d')
            if len(parts) != 2:
                raise ValueError
            
            num_dice = int(parts[0]) if parts[0] else 1
            num_sides = int(parts[1])
            
            if num_dice < 1 or num_dice > 100:
                await interaction.response.send_message("❌ Please roll between 1 and 100 dice!", ephemeral=True)
                return
            
            if num_sides < 2 or num_sides > 1000:
                await interaction.response.send_message("❌ Dice must have between 2 and 1000 sides!", ephemeral=True)
                return
            
            rolls = [random.randint(1, num_sides) for _ in range(num_dice)]
            total = sum(rolls)
            
            embed = discord.Embed(
                title="🎲 Dice Roll",
                description=f"**Rolling {dice}**",
                color=discord.Color.blue()
            )
            
            if num_dice <= 20:
                embed.add_field(name="Rolls", value=", ".join(map(str, rolls)), inline=False)
            
            embed.add_field(name="Total", value=f"**{total}**", inline=False)
            
            await interaction.response.send_message(embed=embed)
            
        except (ValueError, IndexError):
            await interaction.response.send_message("❌ Invalid dice notation! Use format like `2d6` or `1d20`", ephemeral=True)
    
    # 6. RANDOM CHOICE
    @app_commands.command(name="choose", description="Let the bot choose between options")
    @app_commands.describe(options="Options separated by commas (e.g., pizza, burger, tacos)")
    async def choose(self, interaction: discord.Interaction, options: str):
        choices = [opt.strip() for opt in options.split(',') if opt.strip()]
        
        if len(choices) < 2:
            await interaction.response.send_message("❌ Please provide at least 2 options separated by commas!", ephemeral=True)
            return
        
        chosen = random.choice(choices)
        
        embed = discord.Embed(
            title="🤔 Random Choice",
            description=f"I choose... **{chosen}**!",
            color=discord.Color.purple()
        )
        embed.add_field(name="Options", value=", ".join(choices), inline=False)
        
        await interaction.response.send_message(embed=embed)
    
    # REMOVED LEADERBOARD - Already exists in your other cogs!
    
    # 8. REMINDER SYSTEM (Simplified - no background task)
    @app_commands.command(name="remind", description="Set a reminder")
    @app_commands.describe(
        duration="Duration (e.g., 30m, 2h, 1d)",
        message="What to remind you about"
    )
    async def remind(self, interaction: discord.Interaction, duration: str, message: str):
        try:
            time_units = {'s': 1, 'm': 60, 'h': 3600, 'd': 86400}
            unit = duration[-1].lower()
            amount = int(duration[:-1])
            
            if unit not in time_units:
                raise ValueError
            
            seconds = amount * time_units[unit]
            
            if seconds < 60 or seconds > 604800:
                await interaction.response.send_message("❌ Duration must be between 1 minute and 7 days!", ephemeral=True)
                return
            
            await interaction.response.send_message(f"⏰ I'll remind you in {duration}!", ephemeral=True)
            
            # Wait and send reminder
            await asyncio.sleep(seconds)
            
            reminder_embed = discord.Embed(
                title="⏰ Reminder!",
                description=message,
                color=discord.Color.green()
            )
            reminder_embed.set_footer(text=f"Set {duration} ago")
            
            try:
                await interaction.user.send(embed=reminder_embed)
            except:
                try:
                    await interaction.channel.send(f"{interaction.user.mention}", embed=reminder_embed)
                except:
                    pass
            
        except (ValueError, IndexError):
            await interaction.response.send_message("❌ Invalid duration! Use format like `30m`, `2h`, or `1d`", ephemeral=True)
    
    # 9. SERVER INFO
    @app_commands.command(name="serverinfo", description="Get information about the server")
    async def serverinfo(self, interaction: discord.Interaction):
        guild = interaction.guild
        
        embed = discord.Embed(
            title=f"📊 {guild.name}",
            color=discord.Color.blue()
        )
        
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)
        
        embed.add_field(name="👑 Owner", value=guild.owner.mention, inline=True)
        embed.add_field(name="📅 Created", value=f"<t:{int(guild.created_at.timestamp())}:D>", inline=True)
        embed.add_field(name="🆔 Server ID", value=guild.id, inline=True)
        
        embed.add_field(name="👥 Members", value=guild.member_count, inline=True)
        embed.add_field(name="💬 Channels", value=len(guild.channels), inline=True)
        embed.add_field(name="😊 Emojis", value=len(guild.emojis), inline=True)
        
        embed.add_field(name="🎭 Roles", value=len(guild.roles), inline=True)
        embed.add_field(name="📈 Boost Level", value=f"Level {guild.premium_tier}", inline=True)
        embed.add_field(name="💎 Boosters", value=guild.premium_subscription_count, inline=True)
        
        await interaction.response.send_message(embed=embed)
    
    # 10. USER INFO
    @app_commands.command(name="fun_userinfo", description="Get information about a user")
    @app_commands.describe(user="The user to get info about (leave empty for yourself)")
    async def userinfo(self, interaction: discord.Interaction, user: Optional[discord.Member] = None):
        target = user or interaction.user
        
        embed = discord.Embed(
            title=f"👤 {target.display_name}",
            color=target.color if target.color != discord.Color.default() else discord.Color.blue()
        )
        
        embed.set_thumbnail(url=target.display_avatar.url)
        
        embed.add_field(name="🏷️ Username", value=str(target), inline=True)
        embed.add_field(name="🆔 ID", value=target.id, inline=True)
        embed.add_field(name="🤖 Bot", value="Yes" if target.bot else "No", inline=True)
        
        embed.add_field(name="📅 Joined Server", value=f"<t:{int(target.joined_at.timestamp())}:D>", inline=True)
        embed.add_field(name="📅 Account Created", value=f"<t:{int(target.created_at.timestamp())}:D>", inline=True)
        
        if target.premium_since:
            embed.add_field(name="💎 Boosting Since", value=f"<t:{int(target.premium_since.timestamp())}:D>", inline=True)
        
        roles = [role.mention for role in target.roles[1:]]
        if roles:
            embed.add_field(name=f"🎭 Roles [{len(roles)}]", value=" ".join(roles[:10]) + ("..." if len(roles) > 10 else ""), inline=False)
        
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(Fun(bot))