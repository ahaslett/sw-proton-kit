"""Summoners War (Steam 2426960) Proton packaging helpers.

This package applies documented Proton/Wine compatibility defaults and
recovers hung Wine prefixes. It does not patch, disable, or emulate
nProtect GameGuard.
"""

from sw_proton_compat.constants import APP_ID, GAME_EXE

__all__ = ["APP_ID", "GAME_EXE"]
