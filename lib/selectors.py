"""DeckProbe selector & runtime-key registry.

Centralises every DOM selector / global var / route the toolkit pokes at
so they can be swapped per-project via env vars (or via a
``deckprobe.config.json`` file at the parent repo root) without forking
the toolkit.

The defaults below are placeholder values, not a real plugin's — this
toolkit stays agnostic to any one consumer, Deck Shelves included. Every
project overrides all of them, normally via its own ``deckprobe.config.json``
(projected into the matching ``DECKPROBE_<name>`` env var at bootstrap — see
``lib/config.py``); the env var itself is also settable directly as an
escape hatch. Legacy ``DEVKIT_<name>`` vars are also accepted as a fallback
so older ``.env`` files keep working through the rename.

  DECKPROBE_HOME_MOUNT_ID          # host page root mount id
  DECKPROBE_QAM_SCOPE_SEL          # QAM panel scope selector
  DECKPROBE_ROOT_SEL               # plugin root selector
  DECKPROBE_SHELF_SEL              # repeating shelf-container selector
  DECKPROBE_ROW_SEL                # horizontal row container selector
  DECKPROBE_CARD_SEL               # card selector inside a row
  DECKPROBE_FOCUS_CLASS            # focused-card class name
  DECKPROBE_VIEWPORT_SEL           # outer viewport container
  DECKPROBE_NEWS_SEL               # native promo/news container
  DECKPROBE_COLLAPSIBLE_HEADER_SEL # collapsible section header
  DECKPROBE_ABOUT_ROUTE            # about / docs route
  DECKPROBE_SETTINGS_ROUTE         # settings page route
  DECKPROBE_CLASS_MAP_GLOBAL       # runtime classmap global var
  DECKPROBE_CLASS_MAP_LS_KEY       # runtime classmap localStorage key
  DECKPROBE_QAM_SECTIONS           # comma-separated QAM CollapsibleSection ids to force-open
"""

import os


def _env(name: str, default: str) -> str:
    v = os.environ.get(f"DECKPROBE_{name}") or os.environ.get(f"DEVKIT_{name}")
    return v if v else default


HOME_MOUNT_ID          = _env("HOME_MOUNT_ID",          "plugin-home-root")
QAM_SCOPE_SEL          = _env("QAM_SCOPE_SEL",          ".plugin-qam-scope")
ROOT_SEL               = _env("ROOT_SEL",               ".plugin-root")
SHELF_SEL              = _env("SHELF_SEL",              ".plugin-shelf")
ROW_SEL                = _env("ROW_SEL",                ".plugin-row")
CARD_SEL               = _env("CARD_SEL",               ".plugin-card")
FOCUS_CLASS            = _env("FOCUS_CLASS",            "gpfocus")
VIEWPORT_SEL           = _env("VIEWPORT_SEL",           ".plugin-viewport")
NEWS_SEL               = _env("NEWS_SEL",               ".plugin-news")
COLLAPSIBLE_HEADER_SEL = _env("COLLAPSIBLE_HEADER_SEL", ".plugin-collapsible-header")
ABOUT_ROUTE            = _env("ABOUT_ROUTE",            "/plugin/about")
SETTINGS_ROUTE         = _env("SETTINGS_ROUTE",         "/plugin/settings")
CLASS_MAP_GLOBAL       = _env("CLASS_MAP_GLOBAL",       "__PLUGIN_CLASS_MAP")
CLASS_MAP_LS_KEY       = _env("CLASS_MAP_LS_KEY",       "plugin_class_map")
QAM_SECTIONS           = _env("QAM_SECTIONS",           "")
