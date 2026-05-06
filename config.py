import os
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID", 0))

# Bot Settings
DEFAULT_XP_PER_MSG = 15
XP_COOLDOWN = 45  # seconds

# Colors
EMBED_COLOR = 0xD2A679   # Coffee theme
SUCCESS = 0x57F287
ERROR = 0xED4245