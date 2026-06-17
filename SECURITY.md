# Security Policy

DeckProbe is a developer-only toolkit. It runs entirely on a contributor's
workstation, connects to a Steam Deck (or a SteamOS VM) over SSH + Chrome
DevTools Protocol, and never ships inside the host plugin bundle. The
threat model is therefore narrower than a typical end-user package, but
the toolkit still touches a live device and reads / writes against its
runtime — so security reports are welcome.

## Supported Versions

DeckProbe has no semver and no releases. Every change lands on `main`
and is logged by date in `CHANGELOG.md`. Only the latest `main` is
supported for security fixes.

| Version            | Supported |
| ------------------ | --------- |
| Latest main branch | ✅         |
| Older commits      | ❌         |

---

## Reporting a Vulnerability

If you discover a security issue in DeckProbe (the CLI, probe scaffolds,
screenshot pipeline, perf bench, UI test runner, or the config / loader
infrastructure), please report it responsibly.

### Preferred Contact

Open a private security report through GitHub Security Advisories:

* GitHub: <https://github.com/santojon/Deck-Shelves/security/advisories>

If private advisories are unavailable, contact the maintainer directly
before publicly disclosing the issue.

---

## What to Include

Please include as much information as possible:

* Vulnerability type
* Steps to reproduce
* Expected vs actual behavior
* Impact assessment (does it affect contributors using the toolkit, the
  Steam Deck the toolkit connects to, or both?)
* Logs, screenshots, or CDP probe output (if applicable)
* Suggested mitigation or patch (optional)

A minimal reproduction — ideally as a small `.cjs` probe or shell
command — is highly appreciated.

---

## Disclosure Policy

To help protect contributors and the devices they connect to:

* Do not publicly disclose vulnerabilities before a fix is available.
* Security issues will be investigated as quickly as possible.
* Once resolved, fixes are noted in `CHANGELOG.md` (and in advisories
  when warranted).

Depending on severity, temporary mitigations (selector overrides,
disabling specific probes) may be recommended before a full patch
lands.

---

## Scope

The following areas are in scope:

* The CLI (`cli.py`) and subcommand dispatch
* The shared `.env` / `deckprobe.config.json` loader
* The CDP session helpers (`cdp.py`, `cdp.cjs`, `lib/cdp.py`)
* The screenshot pipeline scaffold and capture helpers
* The UI test runner and suite loader
* The perf bench harness
* Selector substitution logic in `lib/selectors.{py,cjs}`
* `tools/inject_classmap.py` (the only probe that writes to the device)
* Dependency vulnerabilities affecting the shipped Python helpers

Generally out of scope:

* Issues caused by a malicious / modified `deckprobe.config.json` placed
  at the parent repo root (the toolkit trusts its parent project — bad
  config can break your dev loop but isn't a vulnerability path)
* Denial of service against a Steam Deck you intentionally point the
  toolkit at (the toolkit is a debugging tool by design)
* Issues that require already-privileged shell access to the
  contributor's workstation
* Vulnerabilities caused exclusively by outdated third-party Python
  packages on the contributor's host
* Theoretical-only attacks without realistic exploitation paths

---

## Security Goals

DeckProbe aims to:

* Stay project-agnostic and **never** ship inside a user-facing plugin
  bundle
* Operate fully locally — no telemetry, no remote reporting, no
  background network calls
* Treat `.env` and SSH credentials as the only sensitive inputs and
  never log them
* Minimise what's written to the Steam Deck — only `inject_classmap.py`
  writes (a JSON snapshot of CSS-Modules hashes); every other probe is
  read-only
* Keep third-party dependencies minimal (stdlib + `ws` for the Node
  CDP helper) and auditable

---

## Dependency Management

DeckProbe's surface is small (Python stdlib + `node` for `.cjs` probes).
Direct dependencies are reviewed for:

* Known CVEs
* Supply-chain risks
* Unmaintained packages
* Excessive permissions or unsafe behaviors

---

## Hardening Recommendations for Contributors

* Keep DeckProbe checkouts current with the parent project's pinned
  reference (submodule SHA or workspace package version)
* Store SSH credentials and `DECK_SUDO_PASS` only in the gitignored
  `.env` at the parent repo root
* Don't run DeckProbe against devices you don't own or aren't authorised
  to debug
* When sharing CDP probe output for support, scrub `DECK_HOST`,
  `DECK_USER`, and any tokens that may have surfaced in console
  captures
* Keep SteamOS and Decky Loader updated on the target device

---

## Compatibility Notice

DeckProbe interacts with Steam (via CDP) and with the host's SSH
service. Security guarantees are limited by the security posture of
the target device's SteamOS / SSH stack and of the contributor's
network path to it.

---

## Acknowledgements

Responsible disclosures may be acknowledged in `CHANGELOG.md`, unless
anonymity is requested.
