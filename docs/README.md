# DeckProbe — usage docs

End-to-end examples for using the toolkit against a live Steam Deck.

## Table of contents

- [Connection setup](#connection-setup)
- [Running CDP probes](#running-cdp-probes)
- [Writing a custom probe](#writing-a-custom-probe)
- [Retargeting to your plugin](#retargeting-to-your-plugin)
- [Screenshot pipeline](#screenshot-pipeline)
- [Video capture (uitests --record)](#video-capture-uitests---record)
- [Video scenarios (deliberate recordings, not test byproducts)](#video-scenarios-deliberate-recordings-not-test-byproducts)
- [Perf bench](#perf-bench)
- [Class-map injection](#class-map-injection)
- [CDP target conventions](#cdp-target-conventions)
- [Common pitfalls](#common-pitfalls)

## Connection setup

DeckProbe expects an `.env` file at the parent repo root (the repo that
contains the `deckprobe/` folder). The CLI auto-loads it before invoking
any subcommand, so individual scripts never need to know about it.

Minimum `.env`:

```bash
DECK_HOST=192.168.1.42       # IP or hostname of the deck
DECK_USER=deck               # SSH user (almost always `deck`)
DECK_SUDO_PASS=...           # SteamOS password, used for `sudo -S`
DECK_CDP_PORT=8081           # default CDP port
# DECK_CDP_HOST=...          # only if you tunnel CDP; defaults to DECK_HOST
```

Make sure Steam is launched with CEF remote debugging enabled on the
target device — how, depends on its OS:

- **SteamOS / Steam Deck** — enabled automatically once Decky Loader is
  installed; no manual step needed.
- **Linux (desktop)** — `touch ~/.steam/steam/.cef-enable-remote-debugging`,
  then restart Steam.
- **macOS** — `open -a Steam --args -cef-enable-remote-debugging`.
- **Windows** — launch Steam with `steam.exe -cef-enable-remote-debugging`.

DeckProbe itself runs the same way regardless of which OS is hosting it —
point `DECK_HOST`/`DECK_CDP_PORT` at whichever of the above you enabled
(`127.0.0.1` for a local desktop client, the device's IP for a Deck or a
remote machine).

Verify connectivity:

```bash
curl -s http://$DECK_HOST:$DECK_CDP_PORT/json | python3 -m json.tool
```

You should see a list of CDP targets — at minimum SharedJSContext and
Steam — Big Picture.

## Running CDP probes

```bash
# List every diag script available (built-in + your project's)
python3 deckprobe/cli.py diag list

# Run a probe (target auto-resolved from a substring of its title)
python3 deckprobe/cli.py diag run diag_layout

# Smoke probe of the home: ensures mount + rows + cards are present
python3 deckprobe/cli.py probe --mode smoke

# Inspect every row's title + card count + cards in the home mount
python3 deckprobe/cli.py probe --mode rows
```

The `cli.py` script forwards arguments straight to the chosen probe and
inherits the `.env`-loaded environment.

## Writing a custom probe

The simplest probe is a `.cjs` file that imports `runAndPrint` from the
shared CDP helper, builds a JS expression as a string, and pipes the
result to stdout:

```js
// deckprobe/diag/diag_card_count.cjs
'use strict';
const { runAndPrint } = require('./_lib/cdp');

const expr = `(function(){
  const mount = document.getElementById('deck-shelves-home-root');
  if (!mount) return { error: 'no mount' };
  return {
    cards: mount.querySelectorAll('.ds-card').length,
    rows:  mount.querySelectorAll('.ds-row-scroll').length,
  };
})()`;

runAndPrint('bp', expr);
```

Run it:

```bash
node deckprobe/diag/diag_card_count.cjs
```

When this exact expression runs against a plugin OTHER than the default
project, `_lib/cdp.cjs` automatically swaps every default selector for
the configured one (`DECKPROBE_HOME_MOUNT_ID`, `DECKPROBE_CARD_SEL`, …). No
edits required — write the probe once, run it everywhere.

## Retargeting to your plugin

DeckProbe ships with selector defaults that match the Deck Shelves home
mount — its own reference project — but every one is overridable via env
var (or a `deckprobe.config.json` at the parent repo root). To target a
different plugin's DOM:

```bash
DECKPROBE_HOME_MOUNT_ID=my-plugin-home-root \
DECKPROBE_CARD_SEL='.card-grid > .card' \
DECKPROBE_ROW_SEL='.card-grid' \
DECKPROBE_QAM_SCOPE_SEL='.my-plugin-qam' \
DECKPROBE_ABOUT_ROUTE='/my-plugin/about' \
python3 deckprobe/cli.py probe --mode smoke
```

The full list lives in `deckprobe/lib/selectors.py` (Python) and
`deckprobe/lib/selectors.cjs` (Node). Both files document every env var;
legacy `DEVKIT_<name>` vars are also still accepted, from before the
toolkit's own rename to DeckProbe.

For project-specific diag scripts that don't fit the generic pattern,
point `DECKPROBE_DIAG_DIRS=...` at any folder hierarchy you prefer
(`os.pathsep`-separated, like `PATH` — `:` on macOS/Linux/SteamOS, `;` on
Windows) and the CLI picks them up automatically alongside the built-in
ones — no fixed directory name required:

```
my-plugin/
├── deckprobe/                 # this toolkit (submodule or copy)
├── scripts/
│   └── deckprobe-ext/         # matches the screenshot pipeline's own
│       └── diag/              # --scenarios-dir convention below
│           └── my_custom_probe.cjs
└── .env                       # DECKPROBE_DIAG_DIRS=scripts/deckprobe-ext/diag
```

## Screenshot pipeline

```bash
# Default: whatever each scenario already does today (several force en-US
# for deterministic label matching; others follow the device's own locale).
python3 deckprobe/cli.py screenshot

# Force one locale across every scenario instead.
python3 deckprobe/cli.py screenshot --locale pt-BR
```

`--locale` is read by the project's own scenario files via
`scripts/deckprobe-ext/screenshots/scenarios/_locale.py`'s `force_locale()` —
the generic runner itself never assumes a particular plugin's locale hook
exists; it only passes the value through as `DECKPROBE_SCREENSHOTS_LOCALE`.

The runner underneath (`deckprobe/screenshots/run.py`) is surface-agnostic
and knows nothing about any specific plugin's scenarios — point
`--scenarios-dir` at your own project's scenario module (see
`scripts/deckprobe-ext/` above) to customise which states get captured:

```bash
python3 -m deckprobe.screenshots.run \
  --host <deck-host> --out assets/screenshots \
  --scenarios-dir scripts/deckprobe-ext/screenshots/scenarios
```

## Video capture (uitests --record)

`deckprobe/uitests/run.py` can record every test it runs as an MP4 —
`Page.startScreencast` frames saved locally, then encoded with a LOCAL
`ffmpeg` (never installed on the Deck; install it on the machine running
this tool). Requires no changes to existing suite files:

```bash
python3 -m deckprobe.uitests.run --host <deck-host> --record bp
# or record the QAM popup instead of Big Picture:
python3 -m deckprobe.uitests.run --host <deck-host> --record qam
# choose the locale forced before recording (default: en-US — pass '' to
# leave the device's own locale alone) and where videos land:
python3 -m deckprobe.uitests.run --host <deck-host> --record bp \
  --locale en-US --out tmp/my-videos
```

Each test's video lands at `<out>/<suite>.<test>.mp4` (default out dir:
`tmp/uitest-out/`, resolved against the repo root even when `--out` is a
relative path — same place whether invoked via `pnpm run uitests:record`
from the `deckprobe/` workspace or directly from the repo root).
`--locale` forces the plugin UI to a known language before the run — the
same `globalThis.__dsSetLocale` hook `_locale.py` uses for screenshots —
so a recorded flow reads consistently regardless of the device's own
locale; defaults to `en-US`, matching the screenshot pipeline's own
default.

Verified live against a real Steam Deck over Wi-Fi (see the `profiles`
suite). Recording is real per-test overhead on top of the flow itself: CDP
screencast frame delivery competes with the CDP calls that drive the flow
(clicks, evals) for the same device's attention, and was observed to
noticeably slow both down — a suite meant to be recorded should poll for
DOM state with a generous timeout rather than a fixed short sleep, and treat
a single click as possibly dropped (poll-and-retry, not fire-and-forget) —
see `profiles.py`'s `_add_charging_trigger` for the pattern. `--video-fps`
and (for finer control) `Context.start_recording()`/`.stop_recording()` in a
suite file are there to tune frame rate/quality. Host-agnostic by
construction — this talks to whatever CDP target `DECK_CDP_HOST`/
`DECK_CDP_PORT` exposes, the same regardless of whether the app under test
is currently loaded via Decky Loader or a standalone host.

## Video scenarios (deliberate recordings, not test byproducts)

`uitests --record` above ties a recording to a test run — useful for
debugging a failure visually, one MP4 per test. `deckprobe/videos/` is a
separate, lighter pipeline for the opposite case: no assertions, just a
named flow you deliberately want captured (a feature demo, a content-script
source clip) — same `@register` shape as the screenshot scenarios above, so
a scenario author who already knows that pattern needs nothing new:

```python
# scripts/deckprobe-ext/videos/scenarios/example.py
from deckprobe.videos.lib.registry import register
from deckprobe.videos.lib.capture import record

@register("home_scroll")
def home_scroll(sjc, host, port, out_dir):
    with record(host, port, "Big Picture", out_dir, "home_scroll.mp4"):
        ...  # drive the flow on sjc, or open a fresh session
    return {"home_scroll.mp4": out_dir / "home_scroll.mp4"}
```

```bash
python3 deckprobe/cli.py video --only home_scroll
# or the module directly, same flags as screenshots.run plus --video-fps:
python3 -m deckprobe.videos.run --host <deck-host> \
  --scenarios-dir scripts/deckprobe-ext/videos/scenarios \
  --out tmp/videos --video-fps 10
```

Both `--scenarios-dir` (where scenario `*.py` files live) and `--out`
(where the generated `.mp4` files land) accept an absolute path outside
this repo entirely — handy since recordings are large binaries nobody
wants committed. Relative paths anchor at the repo root either way. Same
convention-file wiring as everything else here: `deckprobe.config.json`'s
`videos_scenarios_dir` / `videos_dir` project a default, `DECKPROBE_VIDEOS_SCENARIOS_DIR`
/ `DECKPROBE_VIDEOS_DIR` env vars (e.g. in a personal, gitignored `.env`)
override it — an env var always wins. `videos_dir` is intentionally unset
in this project's own `deckprobe.config.json` (falls back to a gitignored
`tmp/videos/`); point `DECKPROBE_VIDEOS_DIR` at wherever you actually want
finished recordings to land.

## Perf bench

```bash
pnpm --filter deckprobe perf:bench
# or
python3 deckprobe/perf-bench.py
```

Captures frame-time + memory snapshots over a configurable window. The
output goes to `perf-output/` as JSON. Use as a regression gate when
changing the home rendering path.

## Class-map injection

Steam re-randomises its CSS-Modules class hashes on every minor update.
DeckProbe ships a class-map injector so probes / overlays survive those
updates without code changes.

```bash
CLASS_MAP='{"viewport":"_3PhG...","row":"ds-row-scroll","card":"ds-card"}' \
DECKPROBE_CLASS_MAP_GLOBAL=__MY_PLUGIN_CLASS_MAP \
DECKPROBE_CLASS_MAP_LS_KEY=my_plugin_class_map \
python3 deckprobe/tools/inject_classmap.py
```

The injector writes the map to both `window[...GLOBAL]` (live) and
`localStorage[...LS_KEY]` (persistent across reloads).

## CDP target conventions

Probes accept a short target alias resolved by `_lib/cdp.cjs` /
`lib/cdp.py`:

| Alias       | Resolves to (title substring) |
| ----------- | ----------------------------- |
| `bp`        | Big Picture                   |
| `qam`       | QuickAccess                   |
| `shared`    | SharedJSContext               |
| `mainmenu`  | MainMenu                      |
| `<prefix>`  | Any CDP target id prefix      |

You can also pass the full 32-char target id directly.

## Common pitfalls

- **Probe runs but returns `{}`** — most often the wrong target. The
  home mount lives in `bp`, the QAM scope in `qam`, plugin-module state
  in `shared`. Try `--target` or use the alias table above.
- **CDP returns the wrong target** — Steam reuses target ids across
  reloads. Pass the full id if a prefix matches more than one target.
- **`offsetHeight === 0`** — Steam often renders hidden containers as
  zero-height shells. Use `getBoundingClientRect()` AND check for
  visible focusable descendants instead of trusting `offsetHeight`.
- **Promise hangs forever** — wrap any backend RPC in a timeout. Decky
  RPCs occasionally stall and the CDP probe never returns.
- **Stale classes** — re-run `inject_classmap.py` after a Steam update,
  or your selectors will miss everything Steam now hashes differently.
