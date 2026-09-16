"""Shared identifiers for Summoners War on Steam.

Process names below are the public nProtect GameGuard helper filenames
documented by nProtect error codes (GameMon.des / GameGuard.des) and
Steam GameGuard firewall guides. They are used only to recognize hung
Wine processes — never to patch or disable those binaries.
"""

from __future__ import annotations

APP_ID = "2426960"
GAME_NAME = "Summoners War"
GAME_EXE = "SummonersWar.exe"
STEAM_RUN_URI = f"steam://rungameid/{APP_ID}"

# Wine truncates /proc/<pid>/comm to 15 bytes.
GAME_COMM_PREFIXES = (
    "SummonersWar.ex",
    "SummonersWar.exe",
)

# Public GameGuard helper names. Do not add undocumented internals.
GAMEGUARD_HELPER_NAMES = (
    "GameMon.des",
    "GameMon64.des",
    "GameGuard.des",
)

WATCHED_NAME_PREFIXES = GAME_COMM_PREFIXES + GAMEGUARD_HELPER_NAMES

STEAM_APP_ENV_KEYS = (
    "SteamAppId",
    "SteamGameId",
    "STEAM_COMPAT_APP_ID",
)

COMPATDATA_MARKER = f"compatdata/{APP_ID}"

DEFAULT_RESTART_WINDOW_SEC = 20 * 60
DEFAULT_MAX_RESTARTS = 3
DEFAULT_COOLDOWN_SEC = 90
DEFAULT_STARTUP_GRACE_SEC = 45
DEFAULT_FAILED_START_LIMIT = 2
DEFAULT_POLL_INTERVAL_SEC = 15
