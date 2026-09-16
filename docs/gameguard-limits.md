# Will not bypass GameGuard

This repository is a **Proton packaging and process-hygiene** kit for
Summoners War (Steam 2426960). It is not “better Proton that fakes kernel
anti-cheat.”

## What GameGuard is doing on Linux

On Windows, nProtect GameGuard includes kernel-mode components. SteamDB
lists the Steam build as using **nProtect GameGuard**.

On Proton/Wine:

- The game and GameGuard helpers (`GameMon.des`, `GameMon64.des`,
  `GameGuard.des`) run as **ordinary user processes** inside the Wine prefix.
- Wine’s `ntoskrnl` / `winedevice` path can map some Windows driver PEs
  and run them in **userspace**. That is still not a Windows kernel, and it
  is not a Linux kernel module.
- Are We Anti-Cheat Yet lists Summoners War as **Broken**. Partial
  user-mode checks can still let a session start; they are not a complete
  GameGuard implementation.

If GameGuard’s kernel-only checks fail, the honest outcomes are: the game
exits, the session freezes, or the client shows a GameGuard init error.
This package may **restart the official binary**. It will not make those
checks succeed by lying to them.

## Hard rules (enforced in code and tests)

We will not:

- Reverse-engineer, patch, disable, or replace GameGuard / GameMon.
- Ship `WINEDLLOVERRIDES` that target `GameMon`, `GameGuard`, `npgg*`.
- Invent Linux kernel hooks that pretend to be GameGuard.
- Rebuild Proton with unofficial anti-cheat shims.
- Loop-relaunch when Hive login is broken (`H:2101`).

The launch wrapper exits with status 3 if a user env file tries a GameGuard
DLL override. `tests/test_policy.py` fails the build if those kill-switches
appear in the tree.

## How this differs from a “fake kernel AC” Proton

| This package | A bypass / fake-kernel project |
| --- | --- |
| Uses Valve Proton 9.0-4 unchanged | Patches Wine/Proton to satisfy AC |
| Wrapper exports documented `PROTON_*` / `LD_PRELOAD` | Overrides GameGuard DLLs or syscalls |
| Watchdog kills a **zombie prefix** and runs `steam://rungameid/2426960` | Injects, stubs, or blocks GameMon |
| Documents that GameGuard is only partial under Wine | Claims “full AC support” |

If you need GameGuard to behave exactly as on Windows, use Windows (or wait
for Com2uS / nProtect / Valve to support the title the way Easy Anti-Cheat
and BattlEye have Linux user-mode clients). That work is out of scope.

## Legitimate recovery vs. disable

Allowed:

- Steam → Verify integrity of game files (re-downloads GameGuard if needed).
- Kill leftover **zombie** processes in *this* prefix so the next official
  launch can start (same idea as Windows Task Manager after error 110).
- Turn off *other* overlays that GameGuard or the client treat as
  interference.

Not allowed here:

- Deleting GameGuard and leaving it gone.
- Renaming `GameMon.des` so it does not load.
- Hosting a patched `npgg*.dll`.
