// DeckProbe selector & runtime-key registry (JS mirror of selectors.py).
//
// Centralises every DOM selector / global var / route the toolkit pokes
// at so they can be swapped per-project via env vars or via a
// `deckprobe.config.json` file at the parent repo root, without forking
// the toolkit. The defaults below are example values for a typical
// Decky shelf plugin; override every one for your project via the
// matching `DECKPROBE_*` environment variable.
//
//   DECKPROBE_HOME_MOUNT_ID          # host page root mount id
//   DECKPROBE_QAM_SCOPE_SEL          # QAM panel scope selector
//   DECKPROBE_ROOT_SEL               # plugin root selector
//   DECKPROBE_SHELF_SEL              # repeating shelf-container selector
//   DECKPROBE_ROW_SEL                # horizontal row container selector
//   DECKPROBE_CARD_SEL               # card selector inside a row
//   DECKPROBE_FOCUS_CLASS            # focused-card class name
//   DECKPROBE_VIEWPORT_SEL           # outer viewport container
//   DECKPROBE_NEWS_SEL               # native promo/news container
//   DECKPROBE_COLLAPSIBLE_HEADER_SEL # collapsible section header
//   DECKPROBE_ABOUT_ROUTE            # about / docs route
//   DECKPROBE_CLASS_MAP_GLOBAL       # runtime classmap global var
//   DECKPROBE_CLASS_MAP_LS_KEY       # runtime classmap localStorage key
//   DECKPROBE_PROJECT_LABEL          # console-filter label
//   DECKPROBE_SETTINGS_GLOBAL        # shared-settings global var
'use strict';

// Resolve `DECKPROBE_<name>` first, fall back to the legacy `DEVKIT_<name>`
// env var so older `.env` files keep working through the rename.
function envOr(name, fallback) {
  const v = process.env['DECKPROBE_' + name] || process.env['DEVKIT_' + name];
  return v && v.length ? v : fallback;
}

const SELECTORS = {
  HOME_MOUNT_ID:          envOr('HOME_MOUNT_ID',          'deck-shelves-home-root'),
  QAM_SCOPE_SEL:          envOr('QAM_SCOPE_SEL',          '.deck-shelves-qam-scope'),
  ROOT_SEL:               envOr('ROOT_SEL',               '.deck-shelves-root'),
  SHELF_SEL:              envOr('SHELF_SEL',              '.ds-shelf'),
  ROW_SEL:                envOr('ROW_SEL',                '.ds-row-scroll'),
  CARD_SEL:               envOr('CARD_SEL',               '.ds-card'),
  FOCUS_CLASS:            envOr('FOCUS_CLASS',            'gpfocus'),
  VIEWPORT_SEL:           envOr('VIEWPORT_SEL',           '._3PhGYbMWIcIaZCfllWN19N'),
  NEWS_SEL:               envOr('NEWS_SEL',               '.cE1SaW6jrVUDxcqRtyMo1'),
  COLLAPSIBLE_HEADER_SEL: envOr('COLLAPSIBLE_HEADER_SEL', '.ds-collapsible-header'),
  ABOUT_ROUTE:            envOr('ABOUT_ROUTE',            '/deck-shelves/about'),
  CLASS_MAP_GLOBAL:       envOr('CLASS_MAP_GLOBAL',       '__DS_CLASS_MAP'),
  CLASS_MAP_LS_KEY:       envOr('CLASS_MAP_LS_KEY',       'ds_class_map'),
  PROJECT_LABEL:          envOr('PROJECT_LABEL',          'deck-shelves'),
  SETTINGS_GLOBAL:        envOr('SETTINGS_GLOBAL',        '__DECK_SHELVES_SHARED_SETTINGS__'),
};

// Substitute the canonical default strings baked into raw probe
// snippets with the env-driven values. Idempotent — runs are no-ops when
// the snippet already uses the configured values.
function applySelectors(expr) {
  if (typeof expr !== 'string') return expr;
  return expr
    .replace(/deck-shelves-home-root/g, SELECTORS.HOME_MOUNT_ID)
    .replace(/\.deck-shelves-qam-scope/g, SELECTORS.QAM_SCOPE_SEL)
    .replace(/\.deck-shelves-root/g, SELECTORS.ROOT_SEL)
    .replace(/\.ds-shelf/g, SELECTORS.SHELF_SEL)
    .replace(/\.ds-row-scroll/g, SELECTORS.ROW_SEL)
    .replace(/\.ds-card/g, SELECTORS.CARD_SEL)
    .replace(/gpfocus/g, SELECTORS.FOCUS_CLASS)
    .replace(/\._3PhGYbMWIcIaZCfllWN19N/g, SELECTORS.VIEWPORT_SEL)
    .replace(/\.cE1SaW6jrVUDxcqRtyMo1/g, SELECTORS.NEWS_SEL)
    .replace(/\.ds-collapsible-header/g, SELECTORS.COLLAPSIBLE_HEADER_SEL)
    .replace(/__DECK_SHELVES_SHARED_SETTINGS__/g, SELECTORS.SETTINGS_GLOBAL)
    .replace(/__DS_CLASS_MAP/g, SELECTORS.CLASS_MAP_GLOBAL);
}

module.exports = { ...SELECTORS, applySelectors };
