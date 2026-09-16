#!/usr/bin/env bash
# Install Summoners War Proton packaging helpers for a local Steam client.
# Does not modify GameGuard binaries or write WINEDLLOVERRIDES against them.

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
PREFIX="${SW_PROTON_PREFIX:-$HOME/.local}"
BIN_DIR="${PREFIX}/bin"
SHARE_DIR="${PREFIX}/share/sw-proton-compat"
CONFIG_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/sw-proton-compat"
LOCALFIX_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/protonfixes/localfixes"
SYSTEMD_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user"

usage() {
  cat <<'EOF'
install-sw-proton.sh — copy wrapper, watchdog, and docs into a user prefix

Options:
  --prefix DIR     Install prefix (default: ~/.local)
  --with-systemd   Install a user systemd unit for the watchdog (disabled until enabled)
  --dry-run        Print actions only
  -h, --help       Show this help

After install, set Steam launch options for Summoners War to:
  "$HOME/.local/bin/sw-compat-wrapper" %command%
and force Compatibility Tool "Proton 9.0-4".
EOF
}

DRY_RUN=0
WITH_SYSTEMD=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    --prefix)
      PREFIX="$2"
      BIN_DIR="${PREFIX}/bin"
      SHARE_DIR="${PREFIX}/share/sw-proton-compat"
      shift 2
      ;;
    --with-systemd)
      WITH_SYSTEMD=1
      shift
      ;;
    --dry-run)
      DRY_RUN=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "unknown option: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

run() {
  if [[ "$DRY_RUN" -eq 1 ]]; then
    printf 'dry-run:'
    printf ' %q' "$@"
    printf '\n'
  else
    "$@"
  fi
}

echo "== Summoners War Proton compat installer =="
echo "This package does not bypass nProtect GameGuard."
echo

find_steam_roots() {
  local -a roots=(
    "$HOME/.steam/steam"
    "$HOME/.steam/root"
    "$HOME/.local/share/Steam"
    "$HOME/.var/app/com.valvesoftware.Steam/.local/share/Steam"
  )
  local root
  for root in "${roots[@]}"; do
    if [[ -d "$root" ]]; then
      printf '%s\n' "$root"
    fi
  done
}

mapfile -t STEAM_ROOTS < <(find_steam_roots)
if [[ "${#STEAM_ROOTS[@]}" -eq 0 ]]; then
  echo "note: no Steam library found yet. Install Steam, then re-run to verify Proton 9.0-4."
else
  echo "Steam roots:"
  printf '  %s\n' "${STEAM_ROOTS[@]}"
  FOUND_PROTON9=0
  FOUND_GAME=0
  for root in "${STEAM_ROOTS[@]}"; do
    if [[ -d "${root}/steamapps/common/Proton 9.0" ]]; then
      FOUND_PROTON9=1
      echo "found Proton 9.0 at: ${root}/steamapps/common/Proton 9.0"
    fi
    if [[ -d "${root}/steamapps/common/Summoners War" ]]; then
      FOUND_GAME=1
      echo "found game install at: ${root}/steamapps/common/Summoners War"
    fi
    if [[ -d "${root}/steamapps/compatdata/2426960" ]]; then
      echo "found prefix at: ${root}/steamapps/compatdata/2426960"
    fi
  done
  if [[ "$FOUND_PROTON9" -eq 0 ]]; then
    echo "note: Proton 9.0 is not installed yet. In Steam: Summoners War → Properties → Compatibility → Proton 9.0-4."
  fi
  if [[ "$FOUND_GAME" -eq 0 ]]; then
    echo "note: Summoners War is not in a detected library. AppID 2426960 is free on Steam."
  fi
fi

run mkdir -p "$BIN_DIR" "$SHARE_DIR" "$CONFIG_DIR" "$LOCALFIX_DIR"
run install -m 0755 "${SCRIPT_DIR}/sw-compat-wrapper.sh" "${BIN_DIR}/sw-compat-wrapper"
if [[ "$DRY_RUN" -eq 1 ]]; then
  echo "dry-run: would sync package files into ${SHARE_DIR}"
else
  rm -rf "${SHARE_DIR}/sw_proton_compat" "${SHARE_DIR}/docs"
  cp -a "${REPO_ROOT}/sw_proton_compat" "${SHARE_DIR}/"
  cp -a "${REPO_ROOT}/docs" "${SHARE_DIR}/"
  install -m 0755 "${SCRIPT_DIR}/sw-watchdog.py" "${SHARE_DIR}/sw-watchdog.py"
  install -m 0644 "${REPO_ROOT}/share/recommended-launch-options.txt" "${SHARE_DIR}/recommended-launch-options.txt"
  install -m 0644 "${REPO_ROOT}/protonfixes/2426960.py" "${LOCALFIX_DIR}/2426960.py"
fi

if [[ ! -f "${CONFIG_DIR}/env" ]]; then
  if [[ "$DRY_RUN" -eq 1 ]]; then
    echo "dry-run: would write ${CONFIG_DIR}/env"
  else
    cat > "${CONFIG_DIR}/env" <<'EOF'
# Optional extra environment for sw-compat-wrapper.
# KEY=value lines only. Do not set WINEDLLOVERRIDES for GameGuard/GameMon.
# SW_PROTON_PROFILE is read from the wrapper environment, not this file.
EOF
  fi
fi

# Watchdog imports sw_proton_compat next to the installed script via PYTHONPATH.
if [[ "$DRY_RUN" -eq 0 ]]; then
  cat > "${BIN_DIR}/sw-watchdog" <<EOF
#!/usr/bin/env bash
set -euo pipefail
export PYTHONPATH="${SHARE_DIR}\${PYTHONPATH:+:\${PYTHONPATH}}"
exec python3 "${SHARE_DIR}/sw-watchdog.py" "\$@"
EOF
  chmod 0755 "${BIN_DIR}/sw-watchdog"
fi

if [[ "$WITH_SYSTEMD" -eq 1 ]]; then
  run mkdir -p "$SYSTEMD_DIR"
  if [[ "$DRY_RUN" -eq 1 ]]; then
    echo "dry-run: would install ${SYSTEMD_DIR}/sw-watchdog.service"
  else
    sed "s|@BIN@|${BIN_DIR}|g" "${REPO_ROOT}/share/systemd/sw-watchdog.service.in" \
      > "${SYSTEMD_DIR}/sw-watchdog.service"
    echo "installed ${SYSTEMD_DIR}/sw-watchdog.service (not enabled)"
    echo "enable with: systemctl --user enable --now sw-watchdog.service"
  fi
fi

WRAPPER="${BIN_DIR}/sw-compat-wrapper"
echo
echo "Install complete."
echo
echo "Steam → Summoners War → Properties → Compatibility"
echo "  Force the use of a specific Steam Play compatibility tool"
echo "  Proton 9.0-4   (do not use GE-Proton / Experimental for the login window)"
echo
echo "Steam → Properties → General → Launch Options:"
echo "  \"${WRAPPER}\" %command%"
echo
echo "Steam → Properties → General"
echo "  Disable 'Enable the Steam Overlay while in-game'"
echo
echo "After login, switch the game to windowed 16:9 or 4:3 (ProtonDB mouse-offset fix)."
echo "Log in with Hive, not Google."
echo
echo "Watchdog (opt-in relaunch, stops after a login/startup loop):"
echo "  ${BIN_DIR}/sw-watchdog --once"
echo "  ${BIN_DIR}/sw-watchdog --relaunch"
echo
echo "This is not a kernel-anti-cheat Proton. GameGuard still only has user-mode checks."
