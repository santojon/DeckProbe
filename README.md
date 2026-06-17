# DeckProbe

Toolkit for developing Steam Deck plugins against a live device — CDP
probes, screenshot pipeline, perf bench, UI-test runner. The scaffold
is generic and can be dropped into any Decky plugin repo as a reference
or a git submodule.

> Support repo, not a published library. No releases, no semver.
> Changes are logged by date in `CHANGELOG.md` for traceability.

## What's in the box

- **`cli.py`** — single entry point for probes, screenshots, and diag
  scripts. Loads `.env` and `deckprobe.config.json` from the parent
  repo root so deck connection settings and selector overrides live in
  one place.
- **`cdp.py`** + **`cdp.cjs`** — minimal CDP session (`Runtime.evaluate`
  + `Page.captureScreenshot`). The `.cjs` mirror runs probe snippets
  through `applySelectors()` before sending to the device, so probes
  authored against the example selectors work for any project once the
  overrides are in place.
- **`tools/cdp_probe.py`** — DOM / state probes via Chrome DevTools
  Protocol. Every selector is overridable through env vars (see
  `lib/selectors.py`).
- **`tools/inject_classmap.py`** — push a runtime class-map snapshot to
  the deck so probes and overlays adapt when Steam bumps its
  CSS-Modules hashes.
- **`lib/selectors.py`** + **`lib/selectors.cjs`** — central selector
  registry. Defaults are example values for a typical Decky shelf
  plugin; override per-plugin via `DECKPROBE_*` env vars or a
  `deckprobe.config.json` file without forking the toolkit.
- **`diag/`** — library of `.cjs` probes that pipe through `cdp.cjs`
  and pick up env-driven selector substitution automatically. Some
  are template-style and clearly named; the rest are generic.
- **`screenshots/`** — modular screenshot pipeline scaffold. Honours
  `DECKPROBE_QAM_SCOPE_SEL`, `DECKPROBE_COLLAPSIBLE_HEADER_SEL`, and
  `DECKPROBE_ABOUT_ROUTE`.
- **`perf-bench.py`** — frame-time + memory snapshot harness.
- **`uitests/`** — UI walkthrough runner (`@suite("name").test("case")`
  decorators + a CDP-driven session).

## Quick start

```bash
# 1. From the parent repo root, create a .env with deck connection info
cat >> .env <<EOF
DECK_HOST=192.168.1.42
DECK_USER=deck
DECK_SUDO_PASS=...
DECK_CDP_PORT=8081
EOF

# 2. (Optional) Drop a deckprobe.config.json at the parent repo root
#    with selector overrides + extension paths for your project.
#    See "Convention file" below for the schema.

# 3. List diag probes (your project's + this repo's)
python3 deckprobe/cli.py diag list

# 4. Run a probe (target is auto-resolved from a substring of the title)
python3 deckprobe/cli.py diag run diag_layout

# 5. Smoke probe of the home (`mount`, `rows`, `smoke` modes)
python3 deckprobe/cli.py probe --mode smoke
```

See [`docs/`](docs/) for end-to-end usage examples + how to retarget
the toolkit against a different plugin.

## pnpm flows

The package ships its own pnpm scripts so consumers can reach every
entry point through a single delegate (`pnpm --filter deckprobe …`)
without depending on the toolkit's internal Python layout.

| Script | What it runs |
|---|---|
| `pnpm --filter deckprobe cli` | `python3 cli.py` — top-level CLI; subcommands are forwarded |
| `pnpm --filter deckprobe probe` | `python3 cli.py probe` — smoke / rows / mount probes |
| `pnpm --filter deckprobe screenshots` | `python3 cli.py screenshot` — runs the screenshot pipeline |
| `pnpm --filter deckprobe diag` | `python3 cli.py diag list` — lists every diag script in `diag/` and in every directory listed in `DECKPROBE_DIAG_DIRS` |
| `pnpm --filter deckprobe diag:run` | `python3 cli.py diag run` — run a single diag by name substring |
| `pnpm --filter deckprobe perf:bench` | `python3 perf-bench.py` — frame-time bench |
| `pnpm --filter deckprobe uitests` | `python3 -m uitests.run` — UI walkthrough |
| `pnpm --filter deckprobe uitests:list` | `python3 -m uitests.run --list` — list suites |

Project-level package.json scripts typically wrap these so the rest of
the repo doesn't have to remember the filter syntax:

```json
{
  "scripts": {
    "devtools:cli":   "pnpm --filter deckprobe cli --",
    "devtools:diag":  "pnpm --filter deckprobe diag",
    "screenshots":    "pnpm --filter deckprobe screenshots",
    "perf:bench":     "pnpm --filter deckprobe perf:bench",
    "uitests":        "pnpm --filter deckprobe uitests",
    "uitests:list":   "pnpm --filter deckprobe uitests:list"
  }
}
```

Project-specific overrides (selector swaps, extension paths) flow into
the toolkit transparently through the convention file or env vars — see
the next section.

## Convention file (`deckprobe.config.json`)

Drop a `deckprobe.config.json` at the **parent repo root** to lock in
every override in one place. The CLI loads it before any subcommand
runs and exports each entry as a matching `DECKPROBE_*` env var. Keys
already present in the environment win, so a one-off override on the
command line still trumps the file.

```jsonc
{
  // Selectors — every one becomes DECKPROBE_<KEY> env var.
  "selectors": {
    "HOME_MOUNT_ID":          "my-plugin-root",
    "QAM_SCOPE_SEL":          ".my-plugin-qam",
    "ROOT_SEL":               ".my-plugin-root",
    "SHELF_SEL":              ".tile-row",
    "ROW_SEL":                ".tile-row__scroll",
    "CARD_SEL":               ".tile",
    "FOCUS_CLASS":            "is-focused",
    "ABOUT_ROUTE":            "/my-plugin/about",
    "CLASS_MAP_GLOBAL":       "__MY_PLUGIN_CLASS_MAP",
    "CLASS_MAP_LS_KEY":       "my_plugin_class_map",
    "PROJECT_LABEL":          "my-plugin",
    "SETTINGS_GLOBAL":        "__MY_PLUGIN_SHARED_SETTINGS__"
  },

  // Where to find project-specific diag scripts (colon-separated).
  "diag_dirs": [
    "scripts/deckprobe-ext/diag"
  ],

  // Default suites directory for `uitests`.
  "uitests_suites_dir": "scripts/deckprobe-ext/uitests/suites",

  // Default screenshots driver script.
  "screenshots_script": "scripts/deckprobe-ext/screenshots/screenshot.py",

  // Where captured screenshots land. Optional — defaults to
  // `<parent-root>/screenshots/` (created on first use). Override per
  // project (e.g. Deck Shelves uses "assets/screenshots").
  "screenshots_dir": "screenshots",

  // Default perf bench config file passed through to perf-bench.py.
  "perf_bench_config": "scripts/deckprobe-ext/perf-bench.config.json"
}
```

You can also put any of these under `DECKPROBE_*` in `.env` instead —
no separate file required.

## Retargeting to another plugin

Every default selector lives in `lib/selectors.py` (mirrored in
`lib/selectors.cjs`). Override any of them via environment variables:

```bash
DECKPROBE_HOME_MOUNT_ID=my-plugin-root \
DECKPROBE_CARD_SEL=.tile \
DECKPROBE_QAM_SCOPE_SEL=.my-plugin-qam \
python3 deckprobe/cli.py probe --mode rows
```

The cdp helper (`diag/_lib/cdp.cjs`) automatically substitutes every
default-project string in the probe source before sending it over CDP,
so most `.cjs` probes don't need per-project edits.

## Project-specific extras

`scripts/deckprobe-ext/` (in the parent repo) is the conventional
location for project-specific probes and overrides. The CLI looks for
diag scripts there in addition to the built-in `diag/` folder when
`deckprobe.config.json` sets `diag_dirs`, or when the
`DECKPROBE_DIAG_DIRS` env var points at it.

## Using as a submodule

```bash
git submodule add https://github.com/<your-org>/<this-repo> deckprobe
git config -f .gitmodules submodule.deckprobe.shallow true
git submodule update --init --recursive --depth 1
```

The `cli.py` + `cdp.py` + generic probes work out of the box once
`DECK_HOST` / `DECK_USER` are set. Template-style `diag_*` scripts
are starting points — copy, rename, swap selectors and globals for
your plugin.

## Requirements

- Python 3.10+
- Steam Deck reachable over SSH
- Steam started with CDP enabled (default port `DECK_CDP_PORT=8081`)
- For probes that issue privileged ops: `DECK_SUDO_PASS` in `.env`

## License

MIT. See [LICENSE](LICENSE).
