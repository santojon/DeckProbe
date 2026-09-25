#!/usr/bin/env python3
"""
Modular video-scenario runner. Iterates registered scenarios from the
project's `--scenarios-dir` and writes MP4s to the output dir. Mirrors
`deckprobe.screenshots.run` — same registry shape, same CLI surface — with
`--video-fps` added and a `tmp/` (gitignored) default output instead of a
committed assets dir, since recordings are large binary artifacts nobody
wants checked into the plugin repo.

Usage:
    python3 -m deckprobe.videos.run \
        --host <deck-host> [--port 8080] [--out tmp/videos] \
        --scenarios-dir scripts/deckprobe-ext/videos/scenarios \
        [--only home_scroll]

`--out` and `--scenarios-dir` both accept an absolute path pointing
anywhere on disk, including outside this repo entirely — relative paths
anchor at the repo root (see REPO_ROOT below), absolute ones are used
as-is. Both also read from `deckprobe.config.json` (`videos_dir` /
`videos_scenarios_dir`) or the `DECKPROBE_VIDEOS_DIR` /
`DECKPROBE_VIDEOS_SCENARIOS_DIR` env vars when the flag is omitted — an
env var always wins over the config file (see deckprobe/lib/config.py).

Surface dispatch:
    Each scenario decides whether to record `"Big Picture"` or
    `"QuickAccess"` via `deckprobe.videos.lib.capture.record(...)`. The
    runner itself is surface-agnostic.
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

THIS_DIR = Path(__file__).resolve().parent
if __name__ == "__main__" and __package__ is None:
    sys.path.insert(0, str(THIS_DIR.parent.parent))
    __package__ = "deckprobe.videos"

from .lib.registry import ALL_SCENARIOS  # noqa: E402
from deckprobe.screenshots.lib.cdp import open_session, list_targets  # noqa: E402
# Load .env + deckprobe.config.json so DECKPROBE_VIDEOS_DIR /
# DECKPROBE_VIDEOS_SCENARIOS_DIR (and every other convention entry) come
# in for free, same as uitests/run.py and screenshots/run.py.
from deckprobe.lib.config import bootstrap as _deckprobe_bootstrap  # noqa: E402
_deckprobe_bootstrap()

# uitests → deckprobe → parent repo root (two levels, same as uitests/run.py;
# NOT screenshots/run.py's REPO_ROOT, which assumes a deeper vendoring layout
# this file doesn't share).
REPO_ROOT = THIS_DIR.parent.parent
DEFAULT_OUT = REPO_ROOT / "tmp" / "videos"


def _anchor(p: str) -> Path:
    """A relative path anchors at the repo root, not the caller's CWD, so
    the same value means the same place regardless of invocation style. An
    absolute path — including one outside this repo — is used as-is."""
    path = Path(p)
    return path if path.is_absolute() else (REPO_ROOT / path)


def _load_external_scenarios(scenarios_dir: str) -> None:
    # Imported as a real (namespace) package — not via spec_from_file_location
    # with a synthetic standalone module name — so scenario files can use
    # relative imports for local siblings, same convention as the screenshot
    # scenarios' own loader.
    import importlib
    p = Path(scenarios_dir).resolve()
    if not p.is_dir():
        return
    parent = str(p.parent)
    if parent not in sys.path:
        sys.path.insert(0, parent)
    for f in sorted(p.glob("*.py")):
        if f.name.startswith("_"):
            continue
        try:
            importlib.import_module(f"{p.name}.{f.stem}")
        except Exception as e:
            print(f"[videos] failed to load {f.name}: {e}", file=sys.stderr)


def _load_env_host() -> tuple[str, int]:
    host = os.environ.get("DECK_CDP_HOST", "") or os.environ.get("DECK_HOST", "")
    port = int(os.environ.get("DECK_CDP_PORT", "8080") or "8080")
    env_path = REPO_ROOT / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            k, v = k.strip(), v.strip().strip('"').strip("'")
            if k in ("DECK_HOST", "DECK_CDP_HOST") and not host:
                host = v
            elif k == "DECK_CDP_PORT" and v:
                try:
                    port = int(v)
                except ValueError:
                    pass
    return host, port


def main() -> int:  # noqa: C901
    parser = argparse.ArgumentParser(description="Generic video-scenario runner. Loads project scenarios from --scenarios-dir.")
    parser.add_argument("--host", help="Deck host (defaults to DECK_HOST/DECK_CDP_HOST in .env or env)")
    parser.add_argument("--port", type=int, default=0, help="CDP port (default 8080)")
    parser.add_argument("--out", default=os.environ.get("DECKPROBE_VIDEOS_DIR", "") or str(DEFAULT_OUT),
                        help="Output directory for generated .mp4 files. Accepts an absolute path outside "
                             "this repo. Also read from DECKPROBE_VIDEOS_DIR / deckprobe.config.json `videos_dir`.")
    parser.add_argument("--only", default="", help="Comma-separated scenario names to run (default: all)")
    parser.add_argument("--list", action="store_true", help="List registered scenarios and exit")
    parser.add_argument("--scenarios-dir", default=os.environ.get("DECKPROBE_VIDEOS_SCENARIOS_DIR", ""),
                        help="Directory containing scenario *.py files using @register from "
                             "deckprobe.videos.lib.registry. Accepts an absolute path outside this repo. "
                             "Also read from deckprobe.config.json `videos_scenarios_dir`.")
    parser.add_argument("--video-fps", type=int, default=10, help="Frame rate for the MP4 encode (default 10).")
    parser.add_argument("--locale", default="",
                        help="Force the plugin UI to this locale before recording (e.g. pt-BR) — read by a "
                             "scenario's own locale helper via DECKPROBE_VIDEOS_LOCALE, same convention as "
                             "the screenshot scenarios' _locale.py. Default: unset — each scenario's own "
                             "existing behavior.")
    args = parser.parse_args()

    if args.locale:
        os.environ["DECKPROBE_VIDEOS_LOCALE"] = args.locale

    if args.scenarios_dir:
        _load_external_scenarios(str(_anchor(args.scenarios_dir)))

    if args.list:
        for name, _ in ALL_SCENARIOS:
            print(name)
        return 0

    env_host, env_port = _load_env_host()
    host = args.host or env_host
    port = args.port or env_port
    if not host:
        print("error: --host required (or set DECK_HOST)", file=sys.stderr)
        return 2

    out_dir = _anchor(args.out).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    only = {s.strip() for s in args.only.split(",") if s.strip()} if args.only else None

    print(f"Targeting {host}:{port} → {out_dir}")
    print(f"Available targets: {[t.get('title', '?') for t in list_targets(host, port)]}")

    captured: list[Path] = []
    failed: list[tuple[str, str]] = []
    skipped: list[str] = []
    sjc = open_session(host, port, "SharedJSContext")
    try:
        for name, fn in ALL_SCENARIOS:
            if only is not None and name not in only:
                continue
            print(f"[{name}] recording…")
            t0 = time.time()
            try:
                results = fn(sjc, host, port, out_dir)
                if not results:
                    skipped.append(name)
                    print(f"  – {name}: no output (skipped or precondition absent)")
                for fname, p in (results or {}).items():
                    if p and p.exists():
                        size_kb = p.stat().st_size // 1024
                        captured.append(p)
                        print(f"  → {fname} ({size_kb} KB) in {time.time()-t0:.1f}s")
                    else:
                        failed.append((name, f"no output for {fname}"))
            except Exception as e:
                failed.append((name, str(e)))
                print(f"  ✗ {name}: {e}")
    finally:
        sjc.close()

    print()
    print(f"Recorded {len(captured)} videos")
    if skipped:
        print(f"Skipped {len(skipped)} (no output — precondition absent on this device): {', '.join(skipped)}")
    if failed:
        print(f"Failed: {len(failed)}")
        for name, msg in failed:
            print(f"  - {name}: {msg}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
