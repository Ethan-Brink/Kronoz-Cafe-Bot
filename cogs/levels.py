@app_commands.command(name="rank", description="Show your beautiful rank card")
async def rank(self, interaction: discord.Interaction):
        async with await get_db() as db:
            async with db.execute(
                "SELECT xp, level FROM users WHERE user_id = ? AND guild_id = ?",
                (interaction.user.id, interaction.guild.id)
            ) as cursor:
                row = await cursor.fetchone()

        if not row:
            embed = discord.Embed(description="You have no XP yet. Start chatting in the server!", color=0xED4245)
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        xp, level = row
        next_level_xp = self._xp_for_level(level + 1)

        # Generate rank card
        await interaction.response.defer()
        
        from utils.rank_card import create_rank_card
        img_bytes = await create_rank_card(interaction.user, level, xp, next_level_xp)

        file = discord.File(img_bytes, filename="rank.png")
        await interaction.followup.send(file=file)