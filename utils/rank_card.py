from PIL import Image, ImageDraw, ImageFont, ImageFilter
import discord
import io
import os

async def create_rank_card(user: discord.Member, level: int, xp: int, next_level_xp: int):
    # Create base image (dark coffee theme)
    width, height = 900, 300
    image = Image.new('RGB', (width, height), color=(30, 25, 35))
    draw = ImageDraw.Draw(image)

    # Background gradient
    for i in range(height):
        color = (45 + i//10, 35 + i//15, 55)
        draw.line([(0, i), (width, i)], fill=color)

    # Get avatar
    avatar_bytes = await user.display_avatar.with_size(256).read()
    avatar = Image.open(io.BytesIO(avatar_bytes)).resize((200, 200)).convert("RGB")
    
    # Circular avatar mask
    mask = Image.new('L', (200, 200), 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.ellipse((0, 0, 200, 200), fill=255)
    avatar.putalpha(mask)

    # Paste avatar
    image.paste(avatar, (50, 50), avatar)

    # Progress bar background
    bar_x, bar_y = 290, 180
    bar_width = 570
    bar_height = 35
    draw.rectangle([bar_x, bar_y, bar_x + bar_width, bar_y + bar_height], fill=(50, 45, 60), outline=(80, 70, 90), width=3)

    # Progress fill
    progress = min(xp / next_level_xp, 1.0)
    fill_width = int(bar_width * progress)
    draw.rectangle([bar_x, bar_y, bar_x + fill_width, bar_y + bar_height], fill=(210, 166, 121))  # Coffee color

    # Text
    try:
        title_font = ImageFont.truetype("arial.ttf", 45)
        small_font = ImageFont.truetype("arial.ttf", 28)
        xp_font = ImageFont.truetype("arial.ttf", 24)
    except:
        title_font = ImageFont.load_default()
        small_font = ImageFont.load_default()
        xp_font = ImageFont.load_default()

    # Username
    draw.text((290, 70), user.display_name, fill=(255, 255, 255), font=title_font)

    # Level
    draw.text((290, 130), f"Level {level}", fill=(210, 166, 121), font=small_font)

    # XP Text
    xp_text = f"{xp:,} / {next_level_xp:,} XP"
    draw.text((bar_x + bar_width - 180, bar_y - 35), xp_text, fill=(200, 200, 210), font=xp_font, anchor="ra")

    # Progress percentage
    percent = int(progress * 100)
    draw.text((bar_x + 15, bar_y + 8), f"{percent}%", fill=(255, 255, 255), font=small_font)

    # Save to bytes
    img_bytes = io.BytesIO()
    image.save(img_bytes, format='PNG')
    img_bytes.seek(0)
    
    return img_bytes