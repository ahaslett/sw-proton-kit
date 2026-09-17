# Research brief: Summoners War on Proton (Steam 2426960)

Research date: 2026-09-16. This package follows public Proton/ProtonDB/protonfixes
documentation only. It does not reverse-engineer GameGuard.

## Title identity

| Field | Value | Source |
| --- | --- | --- |
| Steam AppID | `2426960` | [SteamDB](https://steamdb.info/app/2426960/) |
| Install directory | `Summoners War` | SteamDB |
| Launch executable | `SummonersWar.exe` (64-bit Windows) | SteamDB |
| Anti-cheat | nProtect GameGuard | SteamDB “Technologies / Anti-Cheat Software” |
| ProtonDB (official API) | Gold, 20 reports, confidence `good`, score `0.64`, trending Platinum | [summaries/2426960.json](https://www.protondb.com/api/v1/reports/summaries/2426960.json) |
| Are We Anti-Cheat Yet | **Broken** (no notes) | [areweanticheatyet.com/game/summoners-war](https://areweanticheatyet.com/game/summoners-war) |

SteamDB has also stored a Steam Deck “Compatible / Verified” snapshot (tested
2024-02-21, `recommended_runtime=proton-stable`). Treat that as a Valve Deck
label, not as “GameGuard is fully supported on Linux.” AWACY still lists the
title Broken, and ProtonDB Gold reports all include caveats.

## ProtonDB consensus (what actually works)

Public ProtonDB comments for [app/2426960](https://www.protondb.com/app/2426960)
repeat the same cluster of tweaks:

1. **Force Proton 9.0-4.** Several reports are titled around “will not run
   unless you use proton 9.0-4” and list tinker steps “Switch to older version:
   9.0-4” / “Custom Proton: Proton 9.0-4”.
2. **Launch options = `%command%`.** Multiple reporters say this alone made the
   game start or “work very well.” The user already has this.
3. **Do not use GE-Proton or Proton Experimental for login.** Quote: “Using
   GE-proton or Proton experimental will make the login window not show up.
   can be fixed by using regular proton.”
4. **Hive login, not Google.** Quote: “Don't login with google, the game will
   crash. Login via Hive.”
5. **Windowed after login, not a launch flag.** Fullscreen is “junky” with
   off-center clicks. In-game: profile picture → Options → Resolution → Window
   16:9 or 4:3. Launch-option windowed flags were reported to crash; changing
   the setting *after* login works. Stretching the window can “realign” hits.
6. **Native-looking “no compatibility layer” reports exist** but still mention
   `%command%` and first-load stutters. Do not treat those as “the game is a
   Linux binary.” Steam ships `SummonersWar.exe`.

[RootGamer](https://rootgamer.net/en/tests/summoners-war-sky-arena/) mirrors
the Gold rating and the GE/Experimental login-window warning. It also suggests
`PROTON_USE_WINED3D11=1 %command% -dx12` for the login issue. That string is
**not** adopted as a default here (see Discarded hypotheses).

## Proton-GE vs official Proton 9.0-4

[Proton-GE](https://github.com/GloriousEggroll/proton-ge-custom) is a community
Proton with a newer Wine tree, media patches, and bundled
[umu-protonfixes](https://github.com/Open-Wine-Components/umu-protonfixes).
[How-To Geek’s comparison](https://www.howtogeek.com/proton-vs-proton-ge-whats-the-difference-and-which-one-should-you-use/)
is accurate as a general rule: try Valve Proton first, then GE.

For **this AppID the general rule is inverted**. ProtonDB’s working set is
official **Proton 9.0-4**. GE and Experimental are the builds that hide the
login UI. This package therefore:

- Installs against **Proton 9.0-4**.
- Ships a protonfixes-style `protonfixes/2426960.py` for GE/UMU only, and that
  file’s first action is to **log a warning** that 9.0-4 is preferred.
- Does **not** recommend installing Proton-GE to “get better GameGuard.”

A GitHub code search of `Open-Wine-Components/umu-protonfixes` for `2426960`
returned **no existing gamefix**. The older
[simons-public/protonfixes](https://github.com/simons-public/protonfixes)
tree is unmaintained and also has no `2426960.py` (nearby IDs such as
`242640.py` are unrelated). There is no upstream fix to copy; this repo’s
module is a localfix that only sets a marker environment variable.

Official Proton 9.0-4 **does not load protonfixes**. The launch wrapper is the
path that actually applies defaults on Valve Proton.

## Proton runtime knobs (legitimate, documented)

From the [Proton 9.0 README](https://github.com/ValveSoftware/Proton/blob/proton_9.0/README.md)
and [`user_settings.sample.py`](https://github.com/ValveSoftware/Proton/blob/proton_9.0/user_settings.sample.py):

| Variable | Official meaning | Used here |
| --- | --- | --- |
| `PROTON_LOG=1` | Debug log to `$PROTON_LOG_DIR/steam-$APPID.log` | `diag` profile only |
| `PROTON_USE_WINED3D=1` | OpenGL wined3d instead of DXVK (d3d9/10/11) | documented optional; **not** default |
| `PROTON_NO_ESYNC=1` | Disable eventfd esync | `freeze-mitigation` profile only |
| `PROTON_NO_FSYNC=1` | Disable futex fsync | `freeze-mitigation` profile only |
| `PROTON_DISABLE_NVAPI=1` | Disable NVAPI | not enabled (no SW-specific report) |

How to apply them: per-game Steam launch options (`VAR=1 %command%`), or a
wrapper that exports them then `exec`s `%command%`. Global
`user_settings.py` would affect every Proton 9 title — this package does not
write that file.

umu-protonfixes helpers (`util.set_environment`, `util.disable_esync` which
sets `WINEESYNC=`, `util.winedll_override`) are the GE-side equivalents. We
do **not** call `winedll_override` on GameGuard binaries.

## Overlay and HUD notes

- Steam Overlay can be turned off per-game in Properties. On Linux, emptying
  `LD_PRELOAD` is a documented way to stop overlay injection
  (`LD_PRELOAD="" %command%` — Steam Community overlay threads).
- A 2026 r/summonerswar thread attributed a Steam login failure to
  **RivaTuner overlay** (Windows). The useful portable lesson: extra HUDs
  (MangoHud, RTSS, Discord hook) are the first thing to drop when login or
  mid-session hitching starts. That is not an anti-cheat bypass.
- GameGuard itself has historically treated foreign overlays as interference
  on Windows (Helldivers 2 GameGuard error 122 / “application interfering”
  threads). Disabling *our* overlay is the compatibility setting; disabling
  GameGuard is not.

## Freeze / zombie symptom

Reported on a Linux desk bot: mid-session UI freeze while GameGuard was
active; `SummonersWar.exe` became `<defunct>` (zombie) while the window
stayed painted.

Interpretation we kept:

- A Wine/Proton child exited without being reaped. The X11/Wayland surface
  can remain until `wineserver` for that prefix dies.
- This matches “process hygiene,” not a missing kernel GameGuard driver.
  On Windows, leftover GameGuard processes are a documented cause of
  **Gamemon Init Failed : 110**
  ([r/summonerswar](https://www.reddit.com/r/summonerswar/comments/1axf4nq/sw_steam_security_error_gamemon_init_failed_110/):
  “Needed to eliminate a process from GameGuard in the TaskManager”).
  Killing a leftover helper so the *next* official launch can start is the
  same class of fix as Task Manager; it is not a patch.

Interpretation we discarded:

- “Need to fake `ntoskrnl` so GameGuard thinks it has a Windows kernel.”
  Wine already hosts supported Windows driver PEs in the userspace
  `winedevice` process (Anastasius Focht, [Wine bug 37355](https://bugs.winehq.org/show_bug.cgi?id=37355):
  “Under Wine the kernel driver PE binaries are mapped in userspace into
  ‘winedevice’ … executed in user mode like any other Linux process.”).
  Proton-GE’s ntoskrnl patches are more API stubs in that same userspace
  host, not Linux kernel modules. Shipping extra stubs without an upstream
  Wine/Proton justification would be a Proton rebuild we are not doing, and
  would still not be a real kernel anti-cheat.

The watchdog therefore only:

1. Detects zombie/defunct `SummonersWar.exe` / public helper names
   (`GameMon.des`, `GameMon64.des`, `GameGuard.des`) in the `2426960` prefix.
2. Signals that prefix (not Steam).
3. Asks Steam to start the store build via `steam://rungameid/2426960`.
4. Stops if startup fails twice or a Hive `H:2101` string appears in a log.

Public helper names come from nProtect error-code headers (`GameMon.des` /
`GameGuard.des` not found / auth failed) and Steam GameGuard firewall
guides (Helldivers 2 lists the same filenames). They are identification
strings, not patch targets.

## Hive H:2101 (out of scope)

`HIVE login server connection failed (H:2101)` is a **network / Hive /
client** error, not a Proton packaging bug.

- Multiple platform-wide outages: [r/summonerswar](https://www.reddit.com/r/summonerswar/comments/1leedeb/is_the_steam_client_down_for_anyone_else/)
  (H:2101 on Steam and later mobile).
- Leftover **SWExporter HTTP proxy**: if the game was last quit with the
  proxy up, it may need that proxy again — or a clean quit with the proxy
  off ([thread](https://www.reddit.com/r/summonerswar/comments/1u9u14q/can_no_longer_login_via_steam_h2101_errors/)).
- “Can’t log in on Wi-Fi, only mobile data” reports point at routing/DNS,
  not Wine.

The watchdog must **not** relaunch in a tight loop when login is broken.
That is why failed-start and log-scan brakes exist.

## Discarded hypotheses

| Hypothesis | Why discarded |
| --- | --- |
| Default `PROTON_USE_WINED3D11=1 %command% -dx12` (RootGamer) | Official Proton 9 documents `PROTON_USE_WINED3D`, not `WINED3D11`. WineD3D is the D3D9/10/11 OpenGL path; `-dx12` asks for D3D12/vkd3d. ProtonDB’s working reports do not use this pair. Kept as a last-resort note only. |
| Switch to Proton-GE for “better GameGuard” | ProtonDB: GE hides the login window on this AppID. |
| Rebuild Proton with extra ntoskrnl stubs | No tiny, clearly justified upstream Wine/Proton patch unique to SW. Out of scope. |
| `WINEDLLOVERRIDES` to disable GameMon/npgg | That is an anti-cheat bypass. Forbidden. |
| Linux kernel module that pretends to be GameGuard | Forbidden. Wine does not load Windows `.sys` into the Linux kernel. |
| Delete the GameGuard folder as a standing fix | Steam community “delete folder + verify” only re-downloads GameGuard. Useful as a **repair**, not a disable. Documented in the README as verify-integrity, not as “remove AC.” |
| In-scope fix for H:2101 | Network/Hive; watchdog refuses to loop. |

## What this repo ships instead

1. Documented Proton 9.0-4 + `%command%` + overlay-off + windowed + Hive.
2. A wrapper that applies those defaults without DLL-killing GameGuard.
3. A local protonfix that warns GE users.
4. A watchdog that cleans a zombie prefix and relaunches the **unmodified**
   Steam game, with login-loop brakes.

See [gameguard-limits.md](gameguard-limits.md) and [settings.md](settings.md).
