# DeckProbe — Changelog

> Support tooling. No releases, no semver. Entries are logged by date
> for traceability only.

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
