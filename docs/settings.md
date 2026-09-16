# Compatibility settings (and why)

Nothing in this list patches GameGuard. Each row is either a ProtonDB
community default, a Valve Proton 9 runtime flag, or an overlay/process
hygiene setting.

## Required Steam UI steps

| Setting | Value | Why |
| --- | --- | --- |
| Compatibility tool | **Proton 9.0-4** | ProtonDB working reports cluster here. GE / Experimental hide the login window. |
| Launch options (minimum) | `%command%` | ProtonDB: this alone unblocks start for several reporters. |
| Launch options (this package) | `"$HOME/.local/bin/sw-compat-wrapper" %command%` | Same passthrough, plus documented env. |
| Steam Overlay | Off for this game | Overlay injection is a known hitch/login irritant; emptying `LD_PRELOAD` is the Linux equivalent. |
| Account | Hive, not Google | ProtonDB: Google login crashes. |
| Display | Windowed 16:9 or 4:3 **after** login | ProtonDB: fullscreen mouse offset / black screen after logo. Do not pass a windowed launch flag; that crashed for reporters. |

## Wrapper profiles (`SW_PROTON_PROFILE`)

| Profile | Exports | Why |
| --- | --- | --- |
| `default` | `SW_PROTON_COMPAT=1`, `LD_PRELOAD=` | Marker + drop Steam overlay preload. Closest to ProtonDB. |
| `diag` | default + `PROTON_LOG=1` | Valve Proton log at `~/steam-2426960.log` (or `$PROTON_LOG_DIR`). Use for freezes. |
| `freeze-mitigation` | default + `PROTON_NO_ESYNC=1` + `PROTON_NO_FSYNC=1` | Optional hang experiment from the Proton 9 README. **Unproven** for this title. Revert if worse. |

The wrapper also `source`s `~/.config/sw-proton-compat/env` if present, and
**refuses to start** if `WINEDLLOVERRIDES` names GameMon / GameGuard / npgg.

## Not enabled by default

| Setting | Why it is optional / unused |
| --- | --- | --- |
| `PROTON_USE_WINED3D=1` | Official DXVK fallback. RootGamer’s `PROTON_USE_WINED3D11` + `-dx12` is inconsistent with Proton 9 docs. Try only if DXVK is clearly at fault. |
| `PROTON_DISABLE_NVAPI=1` | Valid Proton flag; no SW-specific ProtonDB evidence. |
| Global `user_settings.py` | Would change every Proton 9 game. Use the wrapper. |
| MangoHud / gamescope / Discord hook | Extra injectors. Leave off until the session is stable. |
| `-window` / `-windowed` launch args | ProtonDB: crashed; use the in-game resolution menu instead. |

## Watchdog flags

| Flag | Why |
| --- | --- |
| `--once` | Safe check. No kill. |
| `--relaunch` | Required before any SIGTERM / `steam://rungameid/2426960`. |
| `--dry-run` | Print the plan. |
| `--login-log FILE` | If the file contains `H:2101` / Hive connection failed, stop. |
| `--max-restarts` / `--failed-start-limit` | Hard brakes against a login loop. |

Watchdog matching uses `SteamAppId=2426960` / `compatdata/2426960` so other
Steam games are left alone.
