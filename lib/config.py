"""Shared `.env` + `deckprobe.config.json` loader.

Imported by `cli.py` (probe / screenshot / diag entry points) AND by
`uitests/run.py` (direct python -m invocation). The loader walks a few
likely parent-repo roots, picks up the first `.env` and the first
`deckprobe.config.json` it finds, and projects each entry into a
matching `DECKPROBE_*` environment variable.

Existing env vars always win — a one-off override on the command line
or in `.env` takes precedence over what the config file declares, so
the convention file is the default and the env var is the escape hatch.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Iterable


_THIS_DIR = Path(__file__).resolve().parent
_DECKPROBE_DIR = _THIS_DIR.parent

# Map of config.json top-level keys → env vars they populate. `selectors`
# is handled separately because every nested key becomes its own var.
CONFIG_ENV_MAP = {
    "diag_dirs":          "DECKPROBE_DIAG_DIRS",
    "uitests_suites_dir": "DECKPROBE_UITESTS_SUITES_DIR",
    "screenshots_scenarios_dir": "DECKPROBE_SCREENSHOTS_SCENARIOS_DIR",
    "screenshots_dir":    "DECKPROBE_SCREENSHOTS_DIR",
    "perf_bench_config":  "DECKPROBE_PERF_BENCH_CONFIG",
}


def _candidate_roots() -> Iterable[Path]:
    """Likely parent-repo-root candidates in priority order. Supports the
    default workspace layout (deckprobe at repo root) and submodule
    layouts (deckprobe one or two levels deeper)."""
    base = _DECKPROBE_DIR.parent
    return (base, base.parent, base.parent.parent)


def _load_dotenv(path: Path) -> None:
    try:
        with path.open() as f:
            for ln in f:
                ln = ln.strip()
                if not ln or ln.startswith("#") or "=" not in ln:
                    continue
                k, v = ln.split("=", 1)
                k = k.strip()
                v = v.strip().strip('"').strip("'")
                if k and k not in os.environ:
                    os.environ[k] = v
    except Exception:
        pass


def load_dotenv_from_repo() -> None:
    for root in _candidate_roots():
        env_path = root / ".env"
        if env_path.is_file():
            _load_dotenv(env_path)
            return


def _project_value(value) -> str:
    if isinstance(value, list):
        return ":".join(str(p) for p in value)
    return str(value)


def load_config_from_repo() -> None:
    """Project `deckprobe.config.json` (when present) into `DECKPROBE_*`
    env vars. Pre-existing env vars are not overwritten."""
    for root in _candidate_roots():
        path = root / "deckprobe.config.json"
        if not path.is_file():
            continue
        try:
            with path.open() as f:
                cfg = json.load(f)
        except Exception:
            return
        selectors = cfg.get("selectors") or {}
        if isinstance(selectors, dict):
            for k, v in selectors.items():
                key = f"DECKPROBE_{k}"
                if key not in os.environ and v is not None:
                    os.environ[key] = str(v)
        for k, env_key in CONFIG_ENV_MAP.items():
            if k in cfg and env_key not in os.environ:
                os.environ[env_key] = _project_value(cfg[k])
        return


def bootstrap() -> None:
    """Convenience: load .env, load the config file, ensure DECK_CDP_HOST
    falls back to DECK_HOST, ensure the screenshots dir exists.
    Idempotent — safe to call multiple times."""
    load_dotenv_from_repo()
    load_config_from_repo()
    if "DECK_CDP_HOST" not in os.environ and "DECK_HOST" in os.environ:
        os.environ["DECK_CDP_HOST"] = os.environ["DECK_HOST"]
    # Default the screenshots dir to `<parent-root>/screenshots/` and
    # create it on first use so the screenshot driver always has a
    # writable target. Project configs that set `screenshots_dir`
    # already win via CONFIG_ENV_MAP / load_config_from_repo above.
    if "DECKPROBE_SCREENSHOTS_DIR" not in os.environ:
        for root in _candidate_roots():
            if (root / "deckprobe.config.json").is_file() or (root / ".env").is_file():
                os.environ["DECKPROBE_SCREENSHOTS_DIR"] = "screenshots"
                break
    raw = os.environ.get("DECKPROBE_SCREENSHOTS_DIR")
    if raw:
        candidate = Path(raw)
        if not candidate.is_absolute():
            for root in _candidate_roots():
                if (root / "deckprobe.config.json").is_file() or (root / ".env").is_file():
                    candidate = root / candidate
                    break
        try:
            candidate.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass
