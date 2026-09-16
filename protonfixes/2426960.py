"""Summoners War (Steam 2426960) local protonfix.

Loaded only by GE-Proton / UMU-Proton protonfixes. Official Proton 9.0-4
does not import this file — use scripts/sw-compat-wrapper.sh there.

ProtonDB reporters say GE-Proton and Proton Experimental hide the login
window for this title. This module exists so a GE install logs that
warning. It does not patch, disable, or DLL-override nProtect GameGuard.
"""

from __future__ import annotations

from protonfixes import util
from protonfixes.logger import log


def main() -> None:
    """Apply non-invasive packaging defaults. Never touch GameGuard DLLs."""

    log(
        "Summoners War (2426960): ProtonDB prefers official Proton 9.0-4. "
        "GE-Proton / Experimental have been reported to hide the Hive/Google "
        "login window. This protonfix does not bypass GameGuard."
    )
    # Marker only — overlay disable belongs in the launch wrapper (LD_PRELOAD
    # is already applied by Steam before protonfixes runs).
    util.set_environment("SW_PROTON_COMPAT", "1")
    # Intentionally omitted:
    # - util.winedll_override on GameMon / GameGuard / npgg*
    # - deleting or replacing GameGuard folder contents
    # - kernel / ntoskrnl hooks
