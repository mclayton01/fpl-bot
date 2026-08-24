"""
Configuration settings and environment variable parser for FPL Automated Bot.
"""
import os

# FPL Team Settings
FPL_TEAM_ID = int(os.getenv("FPL_TEAM_ID", "8662144"))
FPL_COOKIE = os.getenv("FPL_COOKIE", "").strip()

# Execution Controls
# In DRY_RUN mode, the bot calculates all moves and logs them without sending POST requests to FPL.
# If no cookie is provided, DRY_RUN automatically activates.
DRY_RUN = os.getenv("DRY_RUN", "").lower() in ("true", "1", "yes") or not FPL_COOKIE

# If FORCE_RUN is True, the bot optimizes and executes regardless of the deadline window.
# If False, the bot only executes within HOURS_BEFORE_DEADLINE window.
FORCE_RUN = os.getenv("FORCE_RUN", "true").lower() in ("true", "1", "yes")

# Window before gameweek deadline (in hours) to execute live updates (ensures latest injury news is known)
HOURS_BEFORE_DEADLINE = float(os.getenv("HOURS_BEFORE_DEADLINE", "6.0"))

# Transfer Strategy Settings
# Minimum expected points improvement required to justify using a free transfer
MIN_TRANSFER_IMPROVEMENT = float(os.getenv("MIN_TRANSFER_IMPROVEMENT", "0.75"))

# Maximum number of transfers to execute per gameweek (1 = free transfer only, no point hits)
MAX_TRANSFERS = int(os.getenv("MAX_TRANSFERS", "1"))

# Base FPL API URLs
FPL_BASE_URL = "https://fantasy.premierleague.com/api"
