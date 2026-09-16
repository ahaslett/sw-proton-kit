#!/usr/bin/env bash
# Launch wrapper for Summoners War (Steam 2426960).
#
# Usage (Steam launch options):
#   "/path/to/sw-compat-wrapper.sh" %command%
#
# This script only exports documented Proton/Wine environment defaults.
# It does not patch, disable, or replace nProtect GameGuard / GameMon.

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROFILE="${SW_PROTON_PROFILE:-default}"
USER_ENV="${SW_PROTON_ENV_FILE:-${XDG_CONFIG_HOME:-$HOME/.config}/sw-proton-compat/env}"

# Repo checkout, or files copied by install-sw-proton.sh into a prefix.
PACKAGE_ROOT=""
for candidate in \
  "${SW_PROTON_SHARE:-}" \
  "${SCRIPT_DIR}/.." \
  "${SCRIPT_DIR}/../share/sw-proton-compat" \
  "${HOME}/.local/share/sw-proton-compat"
do
  if [[ -n "$candidate" && -d "${candidate}/sw_proton_compat" ]]; then
    PACKAGE_ROOT="$candidate"
    break
  fi
done
if [[ -z "$PACKAGE_ROOT" ]]; then
  echo "sw-compat-wrapper: cannot find sw_proton_compat package" >&2
  exit 1
fi

export PYTHONPATH="${PACKAGE_ROOT}${PYTHONPATH:+:${PYTHONPATH}}"

if [[ "${1:-}" == "--print-env" ]]; then
  python3 - "$PROFILE" <<'PY'
import sys
from sw_proton_compat.settings import env_for_profile, PROFILES

profile = sys.argv[1]
if profile not in PROFILES:
    raise SystemExit(f"unknown profile {profile!r}; choose: {', '.join(sorted(PROFILES))}")
env = env_for_profile(profile)
for key, value in env.items():
    print(f"{key}={value}")
PY
  exit 0
fi

if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
  cat <<'EOF'
sw-compat-wrapper.sh — Summoners War Proton launch wrapper

Steam launch options:
  "/full/path/to/sw-compat-wrapper.sh" %command%

Environment:
  SW_PROTON_PROFILE=default|diag|freeze-mitigation
  SW_PROTON_ENV_FILE=~/.config/sw-proton-compat/env   # optional extra KEY=value lines

This wrapper will not set WINEDLLOVERRIDES for GameGuard/GameMon.
EOF
  exit 0
fi

if [[ "$#" -eq 0 ]]; then
  echo "sw-compat-wrapper: missing command. Steam launch options should be:" >&2
  echo "  \"$0\" %command%" >&2
  exit 2
fi

eval "$(
  python3 - "$PROFILE" <<'PY'
import shlex
import sys
from sw_proton_compat.settings import env_for_profile, PROFILES

profile = sys.argv[1]
if profile not in PROFILES:
    raise SystemExit(f"unknown profile {profile!r}")
for key, value in env_for_profile(profile).items():
    print(f"export {shlex.quote(key)}={shlex.quote(value)}")
PY
)"

if [[ -f "$USER_ENV" ]]; then
  # shellcheck disable=SC1090
  set -a
  # User file is KEY=value only. Reject GameGuard DLL overrides.
  if grep -qiE 'WINEDLLOVERRIDES=.*(gamemon|gameguard|npgg|npgame)' "$USER_ENV"; then
    echo "sw-compat-wrapper: refusing $USER_ENV because it overrides GameGuard DLLs." >&2
    exit 3
  fi
  # shellcheck disable=SC1090
  source "$USER_ENV"
  set +a
fi

if [[ -n "${WINEDLLOVERRIDES:-}" ]]; then
  python3 -c 'import os,sys; from sw_proton_compat.settings import looks_like_gameguard_dll_override; sys.exit(1 if looks_like_gameguard_dll_override(os.environ.get("WINEDLLOVERRIDES","")) else 0)' \
    || { echo "sw-compat-wrapper: refusing WINEDLLOVERRIDES that target GameGuard." >&2; exit 3; }
fi

exec "$@"
