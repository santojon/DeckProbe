# DeckProbe — Changelog

> Support tooling. No releases, no semver. Entries are logged by date
> for traceability only.

## [2026-09-02]

- **`diag/` had 161 scripts, of which 144 were one-off historical debugging
  artifacts, not a curated part of the toolkit.** Every one of the 144
  duplicated its own raw `require('ws')` CDP client (hand-rolled WebSocket
  framing, a hardcoded `8081` port ignoring `DECK_CDP_PORT`) instead of the
  shared `_lib/cdp.cjs` helper, and hardcoded non-overridable selectors
  (`deck-shelves-home-root`, `.ds-card`, …) straight into the expression —
  meaning `_lib/cdp.cjs`'s own selector-substitution mechanism (the thing
  that lets a probe "write once, run against any plugin") never applied to
  any of them. Names like `diag_events`/`diag_events2`/`diag_events3` or
  `_diag_v241_items.cjs` (pinned to a specific old Steam client version)
  confirm they were throwaway, not designed for reuse — and `diag list`
  surfaced all 161 to anyone using this toolkit on their own plugin, which
  is a genuinely bad first impression for something billed as generic.
  Removed 108 of the 144 outright, plus two further dead files with no
  callers anywhere (`diag_card_actions.py`, a same-pattern one-off;
  `index.js`, a `list`/`run` dispatcher fully superseded by `cli.py diag
  list`/`run`, which already supports `--extra-dir`/`DECKPROBE_DIAG_DIRS`
  and this one didn't). The other 36 genuinely investigated a Deck Shelves
  feature area with real, recurring bugs (composite/filter resolution,
  multi-key sort, badge overlay, recents-replace, QAM layout, …) rather
  than Steam/GamepadUI internals in general — moved to the consumer's own
  `scripts/deckprobe-ext/diag/` instead of deleted outright, since that's
  exactly the seam this toolkit already documents for project-specific
  probes. Kept the 17 in `deckprobe/diag/` itself that already use
  `_lib/cdp.cjs` properly — those *are* reusable, selector-substitution
  and all.
- **Docs and comments still called this toolkit `devkit/` throughout —
  a stale name from before its own rename to DeckProbe, and one of the
  bugs this tooling exists to catch elsewhere.** `docs/README.md` and
  `docs/EXAMPLES.md` had every code example pointing at `devkit/...`
  paths (which don't exist — the real folder is `deckprobe/`), several
  env vars documented under the old `DEVKIT_` prefix instead of the
  current `DECKPROBE_` one, a `pnpm --filter @steamdeck/devkit` command
  (wrong scope *and* wrong name — the package is plain `deckprobe`), and
  a screenshot-pipeline customization var (`DEVKIT_SCREENSHOT_SCRIPT`)
  that was never a real thing — the actual mechanism is `screenshots/run.py`'s
  own `--scenarios-dir` flag. `lib/cdp.py`'s docstring also branded
  itself "for Deck Shelves devtools" instead of describing itself as the
  generic module it is; `probes/__init__.py` had the same issue.
  `screenshots/README.md` still said "until the split" about a split
  that already happened. All fixed to match what the code actually does
  today ([`docs/README.md`](docs/README.md), [`docs/EXAMPLES.md`](docs/EXAMPLES.md),
  [`lib/cdp.py`](lib/cdp.py), [`probes/__init__.py`](probes/__init__.py),
  [`screenshots/README.md`](screenshots/README.md)).
- **`tools/` had 11 `tmp_*.js` one-off debug scripts and an unreferenced
  `deep_tree.js`, none of them documented or discoverable, several
  hardcoding a specific plugin's selectors or a third-party plugin's
  internal object names.** Kept and promoted the genuinely reusable ones
  to permanent names with a purpose comment: `compat_icon_probe.js`,
  `compat_visibility_probe.js`, `featured_size_probe.js`,
  `focus_ring_probe.js` (the best of three near-duplicate focus-ring
  iterations — the other two removed), `list_focusables.js`, and
  `tabs_probe.js` (generalized — dropped a hardcoded list of one
  third-party plugin's guessed method names, kept the fully generic
  window-object scan). Removed `tmp_shimmer_probe.js` (inspects this
  repo's own reference plugin's shimmer element specifically, not
  reusable) and `tmp_unifideck_probe.js` (fully superseded by the now-generic
  `tabs_probe.js`) and `deep_tree.js` (unreferenced anywhere, hardcoded
  a specific plugin's mount id).

## [2026-08-14]

- **Fixed: external screenshot scenarios using a relative import (`from ._locale
  import ...`) failed to load** — `run.py`'s `_load_external_scenarios` loaded
  each file via `importlib.util.spec_from_file_location` under a synthetic
  standalone module name, which has no package context, so any scenario file
  with a relative import to a local sibling helper silently produced zero
  captures. Now imported as a real (namespace) package instead, so scenario
  files in a project's `--scenarios-dir` can share local helpers via relative
  imports the same way any other Python package would.
- Generalized a one-off tab-click helper in `screenshots/lib/nav.py`
  (`click_element_after_text(host, port, anchor_text)`) — finds the tab-strip
  item after the one matching `anchor_text` and dispatches a real mouse click
  at its center via CDP. Useful whenever a target's own label can't be matched
  directly (collides with another element rendering the same text elsewhere on
  the page, or the label is CSS-transformed so `innerText`/`textContent`
  disagree) but a nearby, unique label can anchor the walk instead.

## [2026-07-05]

- **Cross-OS Python launcher (`scripts/py.mjs`)** — resolves a Python 3
  interpreter (`py -3` → `python` → `python3`, Windows-first `py -3` to dodge the
  Microsoft Store `python3.exe` stub) and forwards args to it. Every `pnpm`
  script now runs through it (`node scripts/py.mjs …` instead of `python3 …`), so
  `cli` / `probe` / `screenshots` / `diag` / `diag:run` / `perf:bench` / `uitests`
  / `uitests:list` work natively on **Windows, macOS, SteamOS, and Linux** —
  `python3` no longer needs to be on PATH.
- `CONTRIBUTING.md` notes the Windows interpreter fallback (`python` / `py -3`)
  and that the pnpm flows resolve it via the launcher.

## [2026-06-17]

- Generic-toolkit framing across all docs, comments, and examples.
  Selector defaults stay as widely-used Decky-plugin examples but are
  framed as overrideable from the start; every diag / probe / screenshot
  scenario calls through `applySelectors(expr)` so project-specific
  identifiers swap in via env vars without touching the toolkit source.
- `cli.py diag list` / `run` walk every directory listed in
  `DECKPROBE_DIAG_DIRS` (colon-separated) in addition to `deckprobe/diag/`, so
  plugin authors can keep app-specific probes outside the toolkit tree.
- `pnpm` scripts at the toolkit level: `cli`, `probe`, `screenshots`,
  `diag`, `diag:run`, `perf:bench`, `uitests`, `uitests:list`.

## [2026-06-12]

- **`diag_search_state.cjs`** — generic search-overlay state inspector.
  Reads diagnostic globals exposed by the host plugin (mount count,
  settings flags, pool + last query, BP input bridge).
- **`diag_search_pool.cjs`** — pool-content dump with optional substring
  filter; reads `[data-name]` attributes across `DECKPROBE_SHELF_SEL`
  containers.
- **`diag_sidenav_focus.cjs`** — side-nav open + focus diagnostics for
  host plugins that expose `__sidenav_open` / `__sidenav_focus` globals.
- **`diag_keyboard_state.cjs`** — Steam Deck on-screen keyboard
  inspector. Reports `document.activeElement` + every `Keyboard*` method
  the `SteamClient.Input` surface exposes.
- **`probe_theme_vars.cjs`** — parameterised theme variable probe via
  `PROBE_TARGET` / `PROBE_SELECTORS` / `PROBE_VARS` env vars.
- **`probe_slider_field.cjs`** — parameterised slider probe via
  `PROBE_TARGET` / `PROBE_SCOPE` / `PROBE_MAX`.
