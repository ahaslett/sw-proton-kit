"""Recommended Proton launch defaults for Steam app 2426960.

Each setting is documented with *why* and a source. Nothing here disables
or overrides GameGuard / GameMon DLLs.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping


@dataclass(frozen=True)
class EnvSetting:
    """One environment override the wrapper may export."""

    name: str
    value: str
    why: str
    source: str
    default_enabled: bool = False


# Official Proton 9.0 README names (not the unofficial WINED3D11 alias).
# https://github.com/ValveSoftware/Proton/blob/proton_9.0/README.md
PROTON_LOG = EnvSetting(
    name="PROTON_LOG",
    value="1",
    why="Writes $PROTON_LOG_DIR/steam-2426960.log for hang/login diagnosis. Off by default (noisy, large).",
    source="Valve Proton 9.0 README, Runtime Config Options",
    default_enabled=False,
)

DISABLE_OVERLAY_PRELOAD = EnvSetting(
    name="LD_PRELOAD",
    value="",
    why=(
        "Clears Steam overlay injection for this launch. Overlay/HUD injectors "
        "are a common source of mid-session hitches and have been reported to "
        "interfere with Summoners War login (RivaTuner on Windows). This does "
        "not unload GameGuard."
    ),
    source="Steam Linux overlay troubleshooting; ProtonDB overlay-adjacent reports",
    default_enabled=True,
)

NO_ESYNC = EnvSetting(
    name="PROTON_NO_ESYNC",
    value="1",
    why=(
        "Disables eventfd esync. A general Proton hang workaround, not proven "
        "for this title. Enable only if the default profile still zombies."
    ),
    source="Valve Proton 9.0 README (PROTON_NO_ESYNC / noesync)",
    default_enabled=False,
)

NO_FSYNC = EnvSetting(
    name="PROTON_NO_FSYNC",
    value="1",
    why=(
        "Disables futex fsync. Pair with PROTON_NO_ESYNC as an optional freeze "
        "mitigation. Can reduce performance; not a GameGuard workaround."
    ),
    source="Valve Proton 9.0 README (PROTON_NO_FSYNC / nofsync)",
    default_enabled=False,
)

USE_WINED3D = EnvSetting(
    name="PROTON_USE_WINED3D",
    value="1",
    why=(
        "Falls back to OpenGL wined3d instead of DXVK. Optional graphics "
        "fallback only. ProtonDB does not treat this as required. The "
        "community string PROTON_USE_WINED3D11 is not a Proton 9 option."
    ),
    source="Valve Proton 9.0 README (PROTON_USE_WINED3D); RootGamer note discarded as default",
    default_enabled=False,
)

MARKER = EnvSetting(
    name="SW_PROTON_COMPAT",
    value="1",
    why="Marks launches that went through this wrapper so logs and the watchdog can tell them apart.",
    source="this package",
    default_enabled=True,
)

ALL_SETTINGS: tuple[EnvSetting, ...] = (
    MARKER,
    DISABLE_OVERLAY_PRELOAD,
    PROTON_LOG,
    NO_ESYNC,
    NO_FSYNC,
    USE_WINED3D,
)


@dataclass
class Profile:
    """Named set of wrapper toggles."""

    name: str
    description: str
    enable: tuple[str, ...] = field(default_factory=tuple)


PROFILES: Mapping[str, Profile] = {
    "default": Profile(
        name="default",
        description=(
            "ProtonDB consensus for 2426960: official Proton 9.0-4, keep "
            "%command%, drop Steam overlay preload. No esync/fsync/wined3d changes."
        ),
        enable=("SW_PROTON_COMPAT", "LD_PRELOAD"),
    ),
    "diag": Profile(
        name="diag",
        description="Default plus Proton logging for a freeze or Hive login investigation.",
        enable=("SW_PROTON_COMPAT", "LD_PRELOAD", "PROTON_LOG"),
    ),
    "freeze-mitigation": Profile(
        name="freeze-mitigation",
        description=(
            "Optional hang experiment: disable esync and fsync. Not a GameGuard "
            "bypass. Revert if the game becomes unstable."
        ),
        enable=("SW_PROTON_COMPAT", "LD_PRELOAD", "PROTON_NO_ESYNC", "PROTON_NO_FSYNC"),
    ),
}

FORBIDDEN_DLL_OVERRIDE_NEEDLES = (
    "gamemon",
    "gameguard",
    "npgg",
    "npgame",
    "ggerror",
)


def recommended_proton_version() -> str:
    """Proton build ProtonDB reporters keep landing on for this AppID."""

    return "proton-9.0-4"


def recommended_launch_options(wrapper_path: str | None = None) -> str:
    """Steam launch-option string. Wrapper is preferred; bare %command% still works."""

    if wrapper_path:
        return f'"{wrapper_path}" %command%'
    return "%command%"


def env_for_profile(profile: str) -> dict[str, str]:
    """Return environment overrides for a named profile."""

    spec = PROFILES.get(profile)
    if spec is None:
        known = ", ".join(sorted(PROFILES))
        raise ValueError(f"unknown profile {profile!r}; expected one of: {known}")
    enabled = set(spec.enable)
    return {item.name: item.value for item in ALL_SETTINGS if item.name in enabled}


def looks_like_gameguard_dll_override(value: str) -> bool:
    """True if a WINEDLLOVERRIDES string targets GameGuard helpers."""

    lowered = value.lower()
    return any(needle in lowered for needle in FORBIDDEN_DLL_OVERRIDE_NEEDLES)
