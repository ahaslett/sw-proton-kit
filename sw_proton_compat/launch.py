"""Apply env profiles and relaunch Steam app 2426960."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

from sw_proton_compat.constants import APP_ID, STEAM_RUN_URI
from sw_proton_compat.settings import env_for_profile


def steam_candidates() -> list[list[str]]:
    """Command prefixes that can open a steam:// URI on this host."""

    commands: list[list[str]] = []
    steam = shutil.which("steam")
    if steam:
        commands.append([steam])
    if shutil.which("flatpak"):
        commands.append(["flatpak", "run", "com.valvesoftware.Steam"])
    xdg = shutil.which("xdg-open")
    if xdg:
        commands.append([xdg])
    return commands


def relaunch_game(*, dry_run: bool = False) -> tuple[bool, str]:
    """Ask Steam to start AppID 2426960. Never launches a patched binary."""

    uri = STEAM_RUN_URI
    if dry_run:
        return True, f"dry-run: would open {uri}"
    last_error = "steam client not found"
    for prefix in steam_candidates():
        try:
            completed = subprocess.run(
                [*prefix, uri],
                check=False,
                capture_output=True,
                text=True,
                timeout=30,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            last_error = str(exc)
            continue
        if completed.returncode == 0:
            return True, f"launched via {' '.join(prefix)} {uri}"
        last_error = completed.stderr.strip() or f"exit {completed.returncode}"
    return False, f"failed to open {uri}: {last_error}"


def apply_profile_to_environ(profile: str, environ: dict[str, str] | None = None) -> dict[str, str]:
    """Return a copy of environ with the profile applied."""

    merged = dict(os.environ if environ is None else environ)
    merged.update(env_for_profile(profile))
    merged.setdefault("STEAM_COMPAT_APP_ID", APP_ID)
    return merged


def default_state_path() -> Path:
    xdg = os.environ.get("XDG_STATE_HOME")
    root = Path(xdg) if xdg else Path.home() / ".local" / "state"
    return root / "sw-proton-compat" / "watchdog.json"
