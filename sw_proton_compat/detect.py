"""Read /proc-style trees for Summoners War / GameGuard Wine processes."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from sw_proton_compat.constants import (
    APP_ID,
    COMPATDATA_MARKER,
    STEAM_APP_ENV_KEYS,
    WATCHED_NAME_PREFIXES,
)


@dataclass(frozen=True)
class ProcSnapshot:
    """One process from a /proc (or fixture) tree."""

    pid: int
    name: str
    state: str
    cmdline: str
    environ: dict[str, str]
    path: Path

    @property
    def is_zombie(self) -> bool:
        return self.state.upper().startswith("Z") or "zombie" in self.name.lower()

    @property
    def is_uninterruptible(self) -> bool:
        return self.state.upper().startswith("D")

    def env_app_id(self) -> str | None:
        for key in STEAM_APP_ENV_KEYS:
            value = self.environ.get(key)
            if value:
                return value
        return None

    def belongs_to_summoners_war(self) -> bool:
        if self.env_app_id() == APP_ID:
            return True
        blob = " ".join(
            (
                self.cmdline,
                " ".join(f"{key}={value}" for key, value in self.environ.items()),
                str(self.path),
            )
        )
        return COMPATDATA_MARKER in blob

    def is_watched_name(self) -> bool:
        comm = self.name
        cmd = self.cmdline
        for prefix in WATCHED_NAME_PREFIXES:
            if comm.startswith(prefix) or prefix.lower() in cmd.lower():
                return True
        return False


def _parse_status(text: str) -> tuple[str, str]:
    name = ""
    state = ""
    for line in text.splitlines():
        if line.startswith("Name:"):
            name = line.split(":", 1)[1].strip()
        elif line.startswith("State:"):
            state = line.split(":", 1)[1].strip()
    return name, state


def _parse_environ(data: bytes) -> dict[str, str]:
    env: dict[str, str] = {}
    for chunk in data.split(b"\0"):
        if not chunk or b"=" not in chunk:
            continue
        try:
            decoded = chunk.decode("utf-8", "replace")
        except Exception:  # pragma: no cover - decode never fails with replace
            continue
        key, value = decoded.split("=", 1)
        env[key] = value
    return env


def read_proc(pid_dir: Path) -> ProcSnapshot | None:
    """Parse one /proc/<pid> directory. Missing files mean the pid exited."""

    try:
        pid = int(pid_dir.name)
    except ValueError:
        return None
    status_path = pid_dir / "status"
    if not status_path.is_file():
        return None
    try:
        name, state = _parse_status(status_path.read_text(encoding="utf-8", errors="replace"))
    except OSError:
        return None
    cmdline = ""
    cmdline_path = pid_dir / "cmdline"
    try:
        cmdline = cmdline_path.read_bytes().replace(b"\0", b" ").decode("utf-8", "replace").strip()
    except OSError:
        pass
    environ: dict[str, str] = {}
    environ_path = pid_dir / "environ"
    try:
        environ = _parse_environ(environ_path.read_bytes())
    except OSError:
        pass
    return ProcSnapshot(
        pid=pid,
        name=name,
        state=state,
        cmdline=cmdline,
        environ=environ,
        path=pid_dir,
    )


def scan_proc(proc_root: Path) -> list[ProcSnapshot]:
    """Return every readable numeric pid under proc_root."""

    if not proc_root.is_dir():
        return []
    snaps: list[ProcSnapshot] = []
    for entry in proc_root.iterdir():
        if not entry.name.isdigit():
            continue
        snap = read_proc(entry)
        if snap is not None:
            snaps.append(snap)
    return snaps


def watched_sw_procs(proc_root: Path) -> list[ProcSnapshot]:
    """Processes that look like this game or its public GameGuard helpers."""

    matches: list[ProcSnapshot] = []
    for snap in scan_proc(proc_root):
        if not snap.is_watched_name():
            continue
        if snap.belongs_to_summoners_war() or snap.env_app_id() in (None, APP_ID):
            # Name match plus either confirmed AppID or no AppID (zombie with empty environ).
            matches.append(snap)
    return matches


def prefix_procs(proc_root: Path) -> list[ProcSnapshot]:
    """Every process in the 2426960 Proton prefix, including wineserver."""

    return [snap for snap in scan_proc(proc_root) if snap.belongs_to_summoners_war()]


def recovery_needed(watched: list[ProcSnapshot]) -> tuple[bool, str]:
    """Whether the prefix looks wedged in the reported zombie-window way."""

    zombies = [snap for snap in watched if snap.is_zombie]
    if not zombies:
        return False, "no watched zombie processes"
    names = ", ".join(sorted({f"{snap.name}[{snap.pid}]" for snap in zombies}))
    return True, f"zombie/defunct: {names}"
