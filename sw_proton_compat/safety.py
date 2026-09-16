"""Restart-limiter so a broken Hive login cannot loop the watchdog."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path

from sw_proton_compat.constants import (
    DEFAULT_COOLDOWN_SEC,
    DEFAULT_FAILED_START_LIMIT,
    DEFAULT_MAX_RESTARTS,
    DEFAULT_RESTART_WINDOW_SEC,
)

LOGIN_BROKEN_HINTS = (
    "H:2101",
    "HIVE login server connection failed",
    "Failed to connect with the network",
)


@dataclass
class SafetyState:
    """Persisted restart history."""

    restarts: list[float] = field(default_factory=list)
    failed_starts: int = 0
    last_relaunch_at: float | None = None
    stopped_reason: str | None = None

    def to_json(self) -> dict[str, object]:
        return {
            "restarts": list(self.restarts),
            "failed_starts": self.failed_starts,
            "last_relaunch_at": self.last_relaunch_at,
            "stopped_reason": self.stopped_reason,
        }

    @classmethod
    def from_json(cls, data: dict[str, object]) -> SafetyState:
        restarts_raw = data.get("restarts", [])
        restarts = [float(item) for item in restarts_raw] if isinstance(restarts_raw, list) else []
        failed = data.get("failed_starts", 0)
        last = data.get("last_relaunch_at")
        reason = data.get("stopped_reason")
        return cls(
            restarts=restarts,
            failed_starts=int(failed) if isinstance(failed, (int, float)) else 0,
            last_relaunch_at=float(last) if isinstance(last, (int, float)) else None,
            stopped_reason=str(reason) if isinstance(reason, str) else None,
        )


def load_state(path: Path) -> SafetyState:
    if not path.is_file():
        return SafetyState()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return SafetyState()
    if not isinstance(data, dict):
        return SafetyState()
    return SafetyState.from_json(data)


def save_state(path: Path, state: SafetyState) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state.to_json(), indent=2) + "\n", encoding="utf-8")


@dataclass(frozen=True)
class SafetyPolicy:
    max_restarts: int = DEFAULT_MAX_RESTARTS
    window_sec: int = DEFAULT_RESTART_WINDOW_SEC
    cooldown_sec: int = DEFAULT_COOLDOWN_SEC
    failed_start_limit: int = DEFAULT_FAILED_START_LIMIT


def prune_restarts(state: SafetyState, now: float, window_sec: int) -> SafetyState:
    kept = [stamp for stamp in state.restarts if now - stamp <= window_sec]
    state.restarts = kept
    return state


def can_relaunch(
    state: SafetyState,
    policy: SafetyPolicy,
    now: float | None = None,
) -> tuple[bool, str]:
    """Decide whether a kill+relaunch is allowed."""

    now = time.time() if now is None else now
    if state.stopped_reason:
        return False, f"watchdog stopped: {state.stopped_reason}"
    prune_restarts(state, now, policy.window_sec)
    if state.failed_starts >= policy.failed_start_limit:
        state.stopped_reason = (
            "login_or_startup_loop — process never stayed up; "
            "refusing to loop (Hive H:2101 / GameGuard init / crash-on-start)"
        )
        return False, state.stopped_reason
    if len(state.restarts) >= policy.max_restarts:
        state.stopped_reason = (
            f"restart_budget_exhausted — {policy.max_restarts} recoveries "
            f"in {policy.window_sec}s; not looping"
        )
        return False, state.stopped_reason
    if state.last_relaunch_at is not None:
        elapsed = now - state.last_relaunch_at
        if elapsed < policy.cooldown_sec:
            remain = int(policy.cooldown_sec - elapsed)
            return False, f"cooldown {remain}s remaining"
    return True, "ok"


def record_relaunch(state: SafetyState, now: float | None = None) -> SafetyState:
    now = time.time() if now is None else now
    state.restarts.append(now)
    state.last_relaunch_at = now
    return state


def record_failed_start(state: SafetyState) -> SafetyState:
    state.failed_starts += 1
    return state


def record_healthy_start(state: SafetyState) -> SafetyState:
    state.failed_starts = 0
    return state


def looks_like_login_error(text: str) -> bool:
    """True if a log snippet looks like Hive/network login failure, not a freeze."""

    lowered = text.lower()
    return any(hint.lower() in lowered for hint in LOGIN_BROKEN_HINTS)
