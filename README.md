# Summoners War Proton compat (Steam 2426960)

Packaging helpers for **Summoners War** on Linux via **Proton 9.0-4**.
The kit applies documented community launch defaults, optional Proton
runtime flags, and a watchdog that recovers a *zombie* Wine prefix.

It is **not** an nProtect GameGuard bypass and **not** a rebuilt Proton
that fakes kernel anti-cheat.

## Will not bypass GameGuard

GameGuard is only partially present under Proton: user-mode checks inside
the Wine prefix. Wine does not load Windows kernel drivers into the Linux
kernel. Are We Anti-Cheat Yet lists this title **Broken**.

This repo will not:

- Patch, disable, rename, or DLL-override `GameMon` / `GameGuard` / `npgg*`
- Ship kernel hooks that pretend to be GameGuard
- Rebuild Proton with unofficial anti-cheat shims
- Loop-relaunch when Hive login is down (`H:2101`)

See [docs/gameguard-limits.md](docs/gameguard-limits.md) for the full
boundary. Research citations live in [docs/research-brief.md](docs/research-brief.md).

## What you get

| Piece | Role |
| --- | --- |
| `scripts/sw-compat-wrapper.sh` | Steam launch wrapper: documented env, then `%command%` |
| `scripts/install-sw-proton.sh` | Copies wrapper, watchdog, and a GE local protonfix |
| `scripts/sw-watchdog.py` | Detects defunct `SummonersWar.exe`; optional clean relaunch |
| `protonfixes/2426960.py` | umu/GE localfix that **warns** 9.0-4 is preferred |
| `docs/` | ProtonDB / Proton-GE / protonfixes research |

Official Proton 9.0-4 does **not** load protonfixes. Use the wrapper there.
GE-Proton *does* load `~/.config/protonfixes/localfixes/2426960.py`, but
ProtonDB says GE hides the login window on this AppID — stay on 9.0-4.

## Install on Steam Linux

Dependencies: Steam, Python 3, Bash. No extra pip packages.

1. Install Summoners War (AppID **2426960**) in Steam.
2. Properties → Compatibility → force **Proton 9.0-4**.
   Do not use Proton-GE or Proton Experimental for the login UI.
3. From this checkout:

   ```bash
   ./scripts/install-sw-proton.sh
   ```

   Optional user systemd unit (not enabled automatically):

   ```bash
   ./scripts/install-sw-proton.sh --with-systemd
   ```

4. Properties → General → Launch Options:

   ```text
   "$HOME/.local/bin/sw-compat-wrapper" %command%
   ```

   Without the wrapper, ProtonDB’s minimum is still `%command%`.

5. Disable **Enable the Steam Overlay while in-game** for this title.
6. Start the game. Log in with **Hive**, not Google.
7. After you reach the island, set Resolution to **Window 16:9 or 4:3**.
   Do not pass a windowed launch flag; ProtonDB reporters said that crashed.

Flatpak Steam works the same if the game is in
`~/.var/app/com.valvesoftware.Steam/.local/share/Steam`. The watchdog
will try `flatpak run com.valvesoftware.Steam steam://rungameid/2426960`
when `steam` is not on `PATH`.

### Optional profiles

```text
SW_PROTON_PROFILE=diag "$HOME/.local/bin/sw-compat-wrapper" %command%
SW_PROTON_PROFILE=freeze-mitigation "$HOME/.local/bin/sw-compat-wrapper" %command%
```

`diag` turns on `PROTON_LOG=1`. `freeze-mitigation` disables esync/fsync
(Proton 9 README flags — unproven for this title). Details:
[docs/settings.md](docs/settings.md).

## Watchdog

Mid-session symptom this targets: UI frozen, window still painted,
`SummonersWar.exe` is `<defunct>`. The watchdog only acts on processes
tied to AppID 2426960.

```bash
# Report only
~/.local/bin/sw-watchdog --once --json

# Recover a wedged prefix, then ask Steam to start the store build
~/.local/bin/sw-watchdog --relaunch

# Refuse to loop if a Proton log already shows Hive H:2101
~/.local/bin/sw-watchdog --relaunch --login-log "$HOME/steam-2426960.log"
```

Safety brakes:

- `--relaunch` is required before any kill
- cooldown between recoveries (default 90s)
- at most 3 recoveries per 20 minutes
- 2 failed starts in a row → stop (login / GameGuard init / crash-on-start)
- `H:2101` in `--login-log` → stop

This relaunches **unmodified** `steam://rungameid/2426960`. It does not
start a patched executable.

From the checkout, without installing:

```bash
./scripts/sw-watchdog.py --once --dry-run
```

## How this differs from “better Proton that fakes kernel AC”

Valve Proton 9.0-4 is used as shipped. We add environment and a restart
helper. We do not add ntoskrnl stubs, syscall translators for GameGuard,
or a Linux `.ko` that pretends to be nProtect.

If GameGuard needs a real Windows kernel, this kit cannot provide one.
The honest extra value is: fewer overlay/login-window footguns, and a
way to unstick a zombie prefix without rebooting the box.

## Hive H:2101

Out of scope. That code is Hive/network (and sometimes a leftover
SWExporter proxy), not a missing Proton DLL. The watchdog will not keep
bouncing the game when login is broken. See the research brief.

## Development

```bash
python3 -m unittest discover -s tests -v
# or
make test
```

Scripts are stdlib-only. Tests use a fake `/proc` tree so they do not
need Steam or the game.

## License

MIT. Summoners War, Steam, Proton, and GameGuard are trademarks of their
owners. This project is unofficial.
