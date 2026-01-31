# cogs/economy.py - Economy & Utility Features
import discord
from discord.ext import commands, tasks
from discord import app_commands
import random
from datetime import datetime, timedelta
from typing import Optional

class Economy(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.daily_cooldowns = {}
        self.work_cooldowns = {}
        self.check_reminders.start()
    
    def cog_unload(self):
        self.check_reminders.cancel()
    
    # 11. ECONOMY - BALANCE
    @app_commands.command(name="balance", description="Check your cafe coins balance")
    @app_commands.describe(user="User to check balance for (optional)")
    async def balance(self, interaction: discord.Interaction, user: Optional[discord.Member] = None):
        target = user or interaction.user
        
        result = self.bot.db.execute(
            "SELECT balance FROM economy WHERE user_id = ?",
            (target.id,)
        ).fetchone()
        
        balance = result[0] if result else 0
        
        embed = discord.Embed(
            title="☕ Cafe Wallet",
            description=f"**{target.display_name}**'s balance",
            color=discord.Color.gold()
        )
        embed.add_field(name="Balance", value=f"☕ {balance:,} Cafe Coins", inline=False)
        embed.set_thumbnail(url=target.display_avatar.url)
        
        await interaction.response.send_message(embed=embed)
    
    # 12. DAILY REWARD
    @app_commands.command(name="daily", description="Claim your daily cafe coins")
    async def daily(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        now = datetime.utcnow()
        
        # Check cooldown
        if user_id in self.daily_cooldowns:
            next_claim = self.daily_cooldowns[user_id]
            if now < next_claim:
                remaining = next_claim - now
                hours = int(remaining.total_seconds() // 3600)
                minutes = int((remaining.total_seconds() % 3600) // 60)
                
                embed = discord.Embed(
                    title="⏰ Daily Cooldown",
                    description=f"You can claim your daily reward in **{hours}h {minutes}m**!",
                    color=discord.Color.orange()
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
        
        # Award daily coins
        amount = random.randint(100, 300)
        
        self.bot.db.execute(
            "INSERT INTO economy (user_id, balance) VALUES (?, ?) ON CONFLICT(user_id) DO UPDATE SET balance = balance + ?",
            (user_id, amount, amount)
        )
        
        # Set cooldown (24 hours)
        self.daily_cooldowns[user_id] = now + timedelta(hours=24)
        
        embed = discord.Embed(
            title="🎁 Daily Reward",
            description=f"You claimed **☕ {amount}** Cafe Coins!",
            color=discord.Color.green()
        )
        embed.set_footer(text="Come back tomorrow for more!")
        
        await interaction.response.send_message(embed=embed)
    
    # 13. WORK COMMAND
    @app_commands.command(name="work", description="Work at the cafe to earn coins")
    async def work(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        now = datetime.utcnow()
        
        # Check cooldown (1 hour)
        if user_id in self.work_cooldowns:
            next_work = self.work_cooldowns[user_id]
            if now < next_work:
                remaining = next_work - now
                minutes = int(remaining.total_seconds() // 60)
                
                embed = discord.Embed(
                    title="⏰ Work Cooldown",
                    description=f"You're tired! Rest for **{minutes} minutes** before working again.",
                    color=discord.Color.orange()
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
        
        # Work scenarios
        jobs = [
            ("brewed some amazing coffee", 50, 100),
            ("served customers with a smile", 40, 90),
            ("baked fresh pastries", 60, 120),
            ("cleaned the cafe", 30, 70),
            ("took orders efficiently", 45, 95),
            ("received a generous tip", 70, 150),
            ("made the perfect latte art", 80, 140),
            ("organized the storage room", 35, 75)
        ]
        
        job, min_pay, max_pay = random.choice(jobs)
        amount = random.randint(min_pay, max_pay)
        
        self.bot.db.execute(
            "INSERT INTO economy (user_id, balance) VALUES (?, ?) ON CONFLICT(user_id) DO UPDATE SET balance = balance + ?",
            (user_id, amount, amount)
        )
        
        # Set cooldown
        self.work_cooldowns[user_id] = now + timedelta(hours=1)
        
        embed = discord.Embed(
            title="💼 Work Complete",
            description=f"You {job} and earned **☕ {amount}** Cafe Coins!",
            color=discord.Color.green()
        )
        
        await interaction.response.send_message(embed=embed)
    
    # 14. TRANSFER COINS
    @app_commands.command(name="pay", description="Transfer cafe coins to another user")
    @app_commands.describe(
        user="User to pay",
        amount="Amount of cafe coins to transfer"
    )
    async def pay(self, interaction: discord.Interaction, user: discord.Member, amount: int):
        if user.bot:
            await interaction.response.send_message("❌ You can't pay bots!", ephemeral=True)
            return
        
        if user.id == interaction.user.id:
            await interaction.response.send_message("❌ You can't pay yourself!", ephemeral=True)
            return
        
        if amount <= 0:
            await interaction.response.send_message("❌ Amount must be positive!", ephemeral=True)
            return
        
        # Check sender balance
        result = self.bot.db.execute(
            "SELECT balance FROM economy WHERE user_id = ?",
            (interaction.user.id,)
        ).fetchone()
        
        sender_balance = result[0] if result else 0
        
        if sender_balance < amount:
            await interaction.response.send_message(
                f"❌ You don't have enough coins! Your balance: ☕ {sender_balance}",
                ephemeral=True
            )
            return
        
        # Transfer coins
        self.bot.db.execute(
            "UPDATE economy SET balance = balance - ? WHERE user_id = ?",
            (amount, interaction.user.id)
        )
        
        self.bot.db.execute(
            "INSERT INTO economy (user_id, balance) VALUES (?, ?) ON CONFLICT(user_id) DO UPDATE SET balance = balance + ?",
            (user.id, amount, amount)
        )
        
        embed = discord.Embed(
            title="💸 Payment Sent",
            description=f"{interaction.user.mention} paid {user.mention} **☕ {amount}** Cafe Coins!",
            color=discord.Color.green()
        )
        
        await interaction.response.send_message(embed=embed)
    
    # 15. SHOP SYSTEM
    @app_commands.command(name="shop", description="View the cafe shop")
    async def shop(self, interaction: discord.Interaction):
        items = [
            {"name": "☕ Coffee", "price": 50, "description": "A refreshing cup of coffee"},
            {"name": "🍰 Cake", "price": 100, "description": "Delicious chocolate cake"},
            {"name": "🎨 Name Color", "price": 500, "description": "Custom colored name role"},
            {"name": "⭐ VIP Pass", "price": 1000, "description": "7-day VIP access"},
            {"name": "🎭 Custom Role", "price": 2000, "description": "Your own custom role"},
        ]
        
        embed = discord.Embed(
            title="🛒 Cafe Shop",
            description="Purchase items with your Cafe Coins!",
            color=discord.Color.blue()
        )
        
        for i, item in enumerate(items, 1):
            embed.add_field(
                name=f"{i}. {item['name']} - ☕ {item['price']}",
                value=item['description'],
                inline=False
            )
        
        embed.set_footer(text="Use /buy <item_number> to purchase")
        
        await interaction.response.send_message(embed=embed)
    
    # 16. BUY FROM SHOP
    @app_commands.command(name="buy", description="Buy an item from the shop")
    @app_commands.describe(item_number="Item number from the shop")
    async def buy(self, interaction: discord.Interaction, item_number: int):
        items = [
            {"name": "☕ Coffee", "price": 50, "role_id": None},
            {"name": "🍰 Cake", "price": 100, "role_id": None},
            {"name": "🎨 Name Color", "price": 500, "role_id": None},
            {"name": "⭐ VIP Pass", "price": 1000, "role_id": None},  # Set actual role ID in config
            {"name": "🎭 Custom Role", "price": 2000, "role_id": None},
        ]
        
        if item_number < 1 or item_number > len(items):
            await interaction.response.send_message("❌ Invalid item number!", ephemeral=True)
            return
        
        item = items[item_number - 1]
        
        # Check balance
        result = self.bot.db.execute(
            "SELECT balance FROM economy WHERE user_id = ?",
            (interaction.user.id,)
        ).fetchone()
        
        balance = result[0] if result else 0
        
        if balance < item["price"]:
            await interaction.response.send_message(
                f"❌ Not enough coins! You need ☕ {item['price']} but have ☕ {balance}",
                ephemeral=True
            )
            return
        
        # Deduct coins
        self.bot.db.execute(
            "UPDATE economy SET balance = balance - ? WHERE user_id = ?",
            (item["price"], interaction.user.id)
        )
        
        # Record purchase
        self.bot.db.execute(
            "INSERT INTO purchases (user_id, item_name, price, purchased_at) VALUES (?, ?, ?, ?)",
            (interaction.user.id, item["name"], item["price"], datetime.utcnow().isoformat())
        )
        
        embed = discord.Embed(
            title="✅ Purchase Successful",
            description=f"You bought **{item['name']}** for ☕ {item['price']}!",
            color=discord.Color.green()
        )
        embed.add_field(name="Remaining Balance", value=f"☕ {balance - item['price']:,}", inline=False)
        
        await interaction.response.send_message(embed=embed)
    
    # 17. RICH LEADERBOARD
    @app_commands.command(name="richest", description="View the richest cafe members")
    async def richest(self, interaction: discord.Interaction):
        top_users = self.bot.db.execute(
            "SELECT user_id, balance FROM economy ORDER BY balance DESC LIMIT 10"
        ).fetchall()
        
        if not top_users:
            await interaction.response.send_message("📊 No economy data yet!", ephemeral=True)
            return
        
        embed = discord.Embed(
            title="💰 Richest Cafe Members",
            description="Top 10 wealthiest members!",
            color=discord.Color.gold()
        )
        
        medals = ["🥇", "🥈", "🥉"]
        leaderboard_text = ""
        
        for i, (user_id, balance) in enumerate(top_users, 1):
            try:
                user = self.bot.get_user(user_id) or await self.bot.fetch_user(user_id)
                medal = medals[i-1] if i <= 3 else f"`#{i}`"
                leaderboard_text += f"{medal} **{user.display_name}** - ☕ {balance:,}\n"
            except:
                continue
        
        embed.description = leaderboard_text
        await interaction.response.send_message(embed=embed)
    
    # Background task for reminders
    @tasks.loop(minutes=1)
    async def check_reminders(self):
        now = datetime.utcnow()
        
        reminders = self.bot.db.execute(
            "SELECT id, user_id, channel_id, message, remind_at FROM reminders WHERE remind_at <= ?",
            (now.isoformat(),)
        ).fetchall()
        
        for reminder_id, user_id, channel_id, message, remind_at in reminders:
            try:
                user = self.bot.get_user(user_id)
                if user:
                    embed = discord.Embed(
                        title="⏰ Reminder!",
                        description=message,
                        color=discord.Color.green()
                    )
                    
                    try:
                        await user.send(embed=embed)
                    except:
                        channel = self.bot.get_channel(channel_id)
                        if channel:
                            await channel.send(f"{user.mention}", embed=embed)
                
                # Delete reminder
                self.bot.db.execute("DELETE FROM reminders WHERE id = ?", (reminder_id,))
                
            except Exception as e:
                print(f"Error sending reminder: {e}")
    
    @check_reminders.before_loop
    async def before_check_reminders(self):
        await self.bot.wait_until_ready()

async def setup(bot):
    await bot.add_cog(Economy(bot))