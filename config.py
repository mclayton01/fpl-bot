"""
Configuration settings and environment variable parser for FPL Automated Bot.
"""
import os

# FPL Team Settings
FPL_TEAM_ID = int(os.getenv("FPL_TEAM_ID", "8662144"))
FPL_COOKIE = os.getenv("FPL_COOKIE", "").strip()

# Execution Controls
# In DRY_RUN mode, the bot calculates all moves and logs them without sending POST requests to FPL.
DRY_RUN = os.getenv("DRY_RUN", "").lower() in ("true", "1", "yes")

# If FORCE_RUN is True, the bot optimizes and executes regardless of the deadline window.
FORCE_RUN = os.getenv("FORCE_RUN", "false").lower() in ("true", "1", "yes")

# Window before gameweek deadline (in hours) to execute updates.
# Set to 24.0 hours so GitHub Actions cron delays never miss a deadline.
HOURS_BEFORE_DEADLINE = float(os.getenv("HOURS_BEFORE_DEADLINE", "24.0"))

# Transfer Strategy Settings
MIN_TRANSFER_IMPROVEMENT = float(os.getenv("MIN_TRANSFER_IMPROVEMENT", "0.75"))
MAX_TRANSFERS = int(os.getenv("MAX_TRANSFERS", "1"))

# Base FPL API URLs
FPL_BASE_URL = "https://fantasy.premierleague.com/api"
