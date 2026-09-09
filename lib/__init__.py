# Shared devtools library for CDP tooling against a Steam Deck plugin.
#
# Deliberately does NOT eagerly import `selectors` here (unlike `cdp`,
# which has no config-driven state): `selectors.py`'s module-level `_env()`
# calls read `os.environ` once, at import time, and importing any submodule
# of this package runs this file first — so an eager import here would
# evaluate every selector BEFORE `lib.config.bootstrap()` (which every real
# entry point calls first, specifically to project `deckprobe.config.json`
# into `DECKPROBE_*` env vars) ever gets a chance to run, silently making
# every config-file override a no-op. Every real consumer already does its
# own `from lib import selectors as S` after bootstrap, which resolves the
# submodule correctly regardless of this file not pre-importing it.
from .cdp import Session, open_session, list_targets, find_target  # noqa: F401
