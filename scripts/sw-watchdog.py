#!/usr/bin/env python3
"""Recover a wedged Summoners War Proton session without touching GameGuard.

Detects zombie/defunct SummonersWar.exe (and public GameGuard helper names)
in the Steam AppID 2426960 prefix, then optionally kills that prefix and
asks Steam to relaunch the store build.

This is process hygiene. It does not patch GameMon, fake kernel anti-cheat,
or retry a broken Hive login forever.
"""

from __future__ import annotations

import argparse
import json
import os
import signal
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from sw_proton_compat.constants import (  # noqa: E402
    APP_ID,
    DEFAULT_POLL_INTERVAL_SEC,
    DEFAULT_STARTUP_GRACE_SEC,
    GAME_EXE,
)
from sw_proton_compat.detect import (  # noqa: E402
    ProcSnapshot,
    prefix_procs,
    recovery_needed,
    watched_sw_procs,
)
from sw_proton_compat.launch import default_state_path, relaunch_game  # noqa: E402
from sw_proton_compat.safety import (  # noqa: E402
    SafetyPolicy,
    can_relaunch,
    load_state,
    looks_like_login_error,
    record_failed_start,
    record_healthy_start,
    record_relaunch,
    save_state,
)


def _pid_alive(pid: int, proc_root: Path) -> bool:
    return (proc_root / str(pid) / "status").is_file()


def _signal_pid(pid: int, sig: int, dry_run: bool) -> None:
    if dry_run:
        print(f"dry-run: would send {sig} to {pid}")
        return
    try:
        os.kill(pid, sig)
    except ProcessLookupError:
        return
    except PermissionError as exc:
        print(f"warning: cannot signal {pid}: {exc}", file=sys.stderr)


def terminate_prefix(procs: list[ProcSnapshot], *, dry_run: bool, proc_root: Path) -> None:
    """TERM then KILL processes in this prefix only. Never signals Steam itself."""

    pids = [snap.pid for snap in procs if not snap.is_zombie]
    # Zombies cannot be killed directly; their parent (usually wineserver) must exit.
    parents = [snap.pid for snap in procs]
    ordered = list(dict.fromkeys(pids + parents))
    skip_names = {"steam", "steam.sh", "steamwebhelper"}
    filtered: list[int] = []
    for pid in ordered:
        snap = next((item for item in procs if item.pid == pid), None)
        name = (snap.name if snap else "").lower()
        if name in skip_names or "steamwebhelper" in name:
            continue
        filtered.append(pid)
    for pid in filtered:
        _signal_pid(pid, signal.SIGTERM, dry_run)
    deadline = time.time() + 8
    while time.time() < deadline:
        if not any(_pid_alive(pid, proc_root) for pid in filtered):
            break
        time.sleep(0.25)
    for pid in filtered:
        if _pid_alive(pid, proc_root):
            _signal_pid(pid, signal.SIGKILL, dry_run)


def wait_for_live_game(proc_root: Path, grace_sec: int) -> bool:
    deadline = time.time() + grace_sec
    while time.time() < deadline:
        watched = watched_sw_procs(proc_root)
        live = [
            snap
            for snap in watched
            if GAME_EXE.lower().startswith(snap.name.lower()[:12]) or GAME_EXE.lower() in snap.cmdline.lower()
        ]
        if any(not snap.is_zombie for snap in live):
            return True
        time.sleep(1)
    return False


def snapshot_status(proc_root: Path) -> dict[str, object]:
    watched = watched_sw_procs(proc_root)
    prefix = prefix_procs(proc_root)
    needed, reason = recovery_needed(watched)
    return {
        "app_id": APP_ID,
        "recovery_needed": needed,
        "reason": reason,
        "watched": [
            {
                "pid": snap.pid,
                "name": snap.name,
                "state": snap.state,
                "zombie": snap.is_zombie,
                "cmdline": snap.cmdline,
            }
            for snap in watched
        ],
        "prefix_pid_count": len(prefix),
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Watch Summoners War (2426960) for zombie Proton processes and recover the prefix.",
    )
    parser.add_argument("--proc-root", type=Path, default=Path("/proc"), help="Process tree (default /proc; tests pass a fixture).")
    parser.add_argument("--interval", type=int, default=DEFAULT_POLL_INTERVAL_SEC, help="Seconds between polls.")
    parser.add_argument("--once", action="store_true", help="Check once and exit (default if --relaunch is not set? still loops unless --once).")
    parser.add_argument("--relaunch", action="store_true", help="Allow kill + steam://rungameid/2426960 after a zombie is seen.")
    parser.add_argument("--dry-run", action="store_true", help="Print actions without signaling or launching Steam.")
    parser.add_argument("--state-file", type=Path, default=None, help="JSON restart budget (default XDG_STATE_HOME).")
    parser.add_argument("--max-restarts", type=int, default=3)
    parser.add_argument("--window-sec", type=int, default=20 * 60)
    parser.add_argument("--cooldown-sec", type=int, default=90)
    parser.add_argument("--startup-grace-sec", type=int, default=DEFAULT_STARTUP_GRACE_SEC)
    parser.add_argument("--failed-start-limit", type=int, default=2)
    parser.add_argument("--json", action="store_true", help="Machine-readable status on stdout.")
    parser.add_argument("--reset-state", action="store_true", help="Clear the restart budget and exit.")
    parser.add_argument(
        "--login-log",
        type=Path,
        default=None,
        help="Optional Proton/Steam log to scan for Hive H:2101 before relaunching.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    state_path = args.state_file or default_state_path()
    if args.reset_state:
        if state_path.is_file():
            state_path.unlink()
        print(f"cleared {state_path}")
        return 0

    policy = SafetyPolicy(
        max_restarts=args.max_restarts,
        window_sec=args.window_sec,
        cooldown_sec=args.cooldown_sec,
        failed_start_limit=args.failed_start_limit,
    )
    state = load_state(state_path)

    def emit(payload: dict[str, object]) -> None:
        if args.json:
            print(json.dumps(payload, indent=2))
        else:
            print(payload.get("message") or payload.get("reason") or json.dumps(payload))

    def cycle() -> str:
        status = snapshot_status(args.proc_root)
        if args.login_log and args.login_log.is_file():
            try:
                text = args.login_log.read_text(encoding="utf-8", errors="replace")[-64_000:]
            except OSError:
                text = ""
            if looks_like_login_error(text):
                state.stopped_reason = "hive_login_error_in_log (H:2101 / network) — not relaunching"
                save_state(state_path, state)
                status["recovery_needed"] = False
                status["reason"] = state.stopped_reason
                status["message"] = state.stopped_reason
                emit(status)
                return "stop"

        if not status["recovery_needed"]:
            live = [
                item
                for item in status["watched"]  # type: ignore[union-attr]
                if isinstance(item, dict) and not item.get("zombie")
            ]
            if live:
                record_healthy_start(state)
                save_state(state_path, state)
            status["message"] = status["reason"]
            emit(status)
            return "ok"

        allowed, why = can_relaunch(state, policy)
        status["safety"] = why
        if not args.relaunch:
            status["message"] = f"{status['reason']} (pass --relaunch to recover)"
            emit(status)
            return "needs-relaunch"

        if not allowed:
            status["message"] = why
            emit(status)
            save_state(state_path, state)
            return "stop" if state.stopped_reason else "ok"

        prefix = prefix_procs(args.proc_root)
        status["message"] = f"recovering prefix ({status['reason']})"
        emit(status)
        terminate_prefix(prefix, dry_run=args.dry_run, proc_root=args.proc_root)
        ok, detail = relaunch_game(dry_run=args.dry_run)
        record_relaunch(state)
        if not ok:
            record_failed_start(state)
            save_state(state_path, state)
            print(detail, file=sys.stderr)
            return "ok"
        if args.dry_run:
            save_state(state_path, state)
            return "ok"
        if wait_for_live_game(args.proc_root, args.startup_grace_sec):
            record_healthy_start(state)
        else:
            record_failed_start(state)
            print("game did not stay up after relaunch; counting as failed start", file=sys.stderr)
        save_state(state_path, state)
        return "ok"

    if args.once:
        result = cycle()
        return 0 if result != "stop" else 4

    while True:
        result = cycle()
        if result == "stop":
            return 4
        time.sleep(max(1, args.interval))


if __name__ == "__main__":
    sys.exit(main())
