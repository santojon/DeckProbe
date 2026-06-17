# Contributing to DeckProbe

DeckProbe is a developer-only toolkit. It's not a published library and
doesn't ship to end users — every contribution touches the CLI / probe
scaffolds / screenshot pipeline / perf bench / UI test runner that
contributors use against a live Steam Deck (or a SteamOS VM).

This guide covers the basics: prerequisites, where to put what, how to
test changes, and how the toolkit stays project-agnostic.

## Prerequisites

- **Python 3.10+**
- **Node.js 18+** (for the `.cjs` probes)
- A **Steam Deck** reachable over SSH (or a SteamOS VM)
- Steam started with CDP enabled (`DECK_CDP_PORT=8081` by default)

## Repo layout

DeckProbe is designed to be either checked out standalone or dropped into
another project as a `git submodule`. The default consumer is the
[Deck Shelves](https://github.com/santojon/Deck-Shelves) plugin, which
includes this repo as a submodule at `deckprobe/` and supplies its own
selector overrides + extension probes through `deckprobe.config.json`.

```
deckprobe/
├── cli.py                 # single entry point (probe / screenshot / diag)
├── cdp.py / cdp.cjs       # CDP session helpers
├── perf-bench.py          # frame-time + memory bench
├── lib/
│   ├── config.py          # .env + deckprobe.config.json loader
│   ├── selectors.py       # selector registry (mirrored as selectors.cjs)
│   └── selectors.cjs
├── diag/                  # generic CDP probes
├── tools/                 # CDP probe + classmap injector
├── screenshots/           # screenshot pipeline (lib/ + scenarios/)
├── uitests/               # UI walkthrough runner + suites/
├── probes/                # auxiliary probes
└── docs/
    └── config.schema.json # JSON schema for deckprobe.config.json
```

## What does NOT belong here

DeckProbe stays project-agnostic. The following belong in the parent
project's `scripts/deckprobe-ext/` (or equivalent), NOT in this repo:

- Project-specific diag scripts (anything that references a particular
  plugin's selectors / state globals directly)
- Project-specific UI test suites
- Project-specific screenshot scenarios / driver scripts
- Project-specific perf-bench config files

Generic infrastructure that every consumer benefits from (CDP session
mechanics, selector substitution, screenshot capture primitives, perf
sampling, UI runner) stays here. When in doubt: **does this make sense
for a different plugin without rewriting it?** If no, push it to the
parent project.

## Convention file (`deckprobe.config.json`)

Selector overrides + extension paths flow in through a
`deckprobe.config.json` at the **parent repo root**. The loader in
[`lib/config.py`](lib/config.py) projects every entry into a matching
`DECKPROBE_*` env var; pre-existing env vars always win. See
[`README.md`](README.md) and the JSON schema at
[`docs/config.schema.json`](docs/config.schema.json) for the full shape.

## Selectors

Every DOM selector / global var / route the toolkit touches MUST go
through [`lib/selectors.py`](lib/selectors.py) (mirrored in
[`lib/selectors.cjs`](lib/selectors.cjs)). Defaults are example values
for a typical Decky shelf plugin; every consumer overrides them via
their `deckprobe.config.json`.

When a probe needs a new selector:

1. Add it to both `selectors.py` and `selectors.cjs` with a sensible
   default.
2. Document the env var in the file's docstring + in the
   `docs/config.schema.json`.
3. If the probe inlines the canonical default string (e.g. for
   readability), make sure `applySelectors(expr)` in `selectors.cjs`
   has a `.replace()` for it so consumers can swap it at runtime.

## Style

- **No eslint / prettier / vitest / tsup.** This is a tools repo — no
  TypeScript build step, no React, no large dependency footprint.
- **Python stdlib only** for new helpers (the `ws` Node dep is the only
  third-party piece the toolkit ships).
- **Keep helpers short.** If a probe grows past ~200 lines, extract the
  shared pieces into `lib/` or `screenshots/lib/`.
- **No comments restating the obvious.** Add a `# why:` line when the
  intent isn't visible from the code (a workaround for a known Steam
  quirk, a defensive guard against a CEF version change, etc.).

## Running things locally

```bash
# From the parent repo root:
python3 deckprobe/cli.py probe --mode smoke
python3 deckprobe/cli.py diag list
python3 deckprobe/cli.py diag run diag_layout
python3 deckprobe/cli.py screenshot --locale en-US
python3 deckprobe/perf-bench.py
python3 -m deckprobe.uitests.run --list
```

Or, when the consumer wires the toolkit as a `pnpm` workspace package,
through the pnpm flows:

```bash
pnpm --filter deckprobe cli -- probe --mode smoke
pnpm --filter deckprobe diag
pnpm --filter deckprobe screenshots
pnpm --filter deckprobe perf:bench
pnpm --filter deckprobe uitests
```

## Submitting changes

DeckProbe has no release cadence and no semver. PRs are reviewed by the
maintainer and merged when they're stable on at least one consumer. Keep
each PR focused on a single concern (one new probe, one selector swap,
one CLI subcommand) so changes can land independently.

When you add a probe / scenario / suite, update [`CHANGELOG.md`](CHANGELOG.md)
under the current date so the change is traceable.

## Code of Conduct

By participating you agree to follow the [Code of Conduct](CODE_OF_CONDUCT.md).
Security issues go through [`SECURITY.md`](SECURITY.md).
