<!-- PR title format: `[area] short summary` — e.g. `[cli] resolve relative screenshot script paths` or `[diag] add Quick Search keyboard probe`. -->

## Summary

<!-- 1-3 sentences. What does this change do? Why? -->

## Scope check

- [ ] This stays project-agnostic (no plugin-specific selectors / state
      globals; new selectors flow through `lib/selectors.{py,cjs}` with a
      sensible default and a `DECKPROBE_*` override).
- [ ] No new third-party dependencies (Python stdlib only; `ws` is the
      only Node dep DeckProbe ships).
- [ ] Updates [`CHANGELOG.md`](../CHANGELOG.md) under today's date.
- [ ] Updates [`README.md`](../README.md) when adding a new public CLI
      flag / pnpm script / convention-file key.

## Testing

<!-- How was this verified? Local CLI run, probe against a real Deck,
     UI-test suite, etc. Paste the command + relevant output. -->

```
$ python3 deckprobe/cli.py …
```

## Compatibility

- [ ] Works against the Deck Shelves consumer's setup.
- [ ] No silent breaking changes for other consumers (env var rename,
      removed CLI flag, dropped selector default).
