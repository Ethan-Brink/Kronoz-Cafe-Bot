# config.py - Bot Configuration
import os

# Discord Server IDs
GUILD_ID = 1457746056749125644  # Your server ID
COUNTING_CHANNEL_ID = 1462001538011496474
MOD_LOG_CHANNEL_ID = 1462001894934315009
ANNOUNCEMENTS_CHANNEL_ID = 1458731506947199019
TICKET_CATEGORY_ID = 1462002045895704710  # Create a category for tickets
APPEAL_CHANNEL_ID = 1462002231720280248
LOA_CHANNEL_ID = 1462002349101940914

# Roblox Configuration
ROBLOX_GROUP_ID = 941192442  # Your Roblox group ID (if applicable)
ROBLOX_GAME_ID = 114976671702338  # Your game place ID
ROBLOX_UNIVERSE_ID = None  # Your universe ID (for API calls)

# Punishment Thresholds (auto-escalation)
PUNISHMENT_THRESHOLDS = {
    "verbal_warns": 3,  # 3 verbal warns = 1 formal warn
    "warns": 3,         # 3 warns = kick
    "kicks": 2          # 2 kicks = ban
}

# Ticket Settings
TICKET_CATEGORIES = {
    "support": "General Support",
    "appeal": "Ban/Warn Appeal",
    "report": "Player Report",
    "loa": "Leave of Absence",
    "staff_app": "Staff Application",
    "other": "Other"
}

# Colors
COLORS = {
    "success": 0x00ff00,
    "error": 0xff0000,
    "warning": 0xff9900,
    "info": 0x3498db,
    "primary": 0x8B4513  # Coffee brown
}

# Staff Role IDs (set these to your server's role IDs)
STAFF_ROLES = {
    "admin": None,
    "senior_mod": None,
    "moderator": None,
    "trial_mod": None
}

# Cooldowns (in seconds)
COOLDOWNS = {
    "ticket_create": 300,  # 5 minutes between tickets
    "loa_request": 86400   # 24 hours between LOA requests
}