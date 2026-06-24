"""
Navigation primitives — actions that move the running Steam UI to a
specific state before a screenshot is taken.
"""
from __future__ import annotations

import os
import sys
import time
from typing import Any

from .cdp import Session, open_session

# Bridge to the central selectors module. deckprobe/lib is a sibling of
# deckprobe/screenshots — add deckprobe/ to sys.path so we can import lib.selectors
# without forcing the consumer to install the deckprobe as a package.
_DECKPROBE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if _DECKPROBE_DIR not in sys.path:
    sys.path.insert(0, _DECKPROBE_DIR)
from lib import selectors as S  # noqa: E402

_QAM_SCOPE = S.QAM_SCOPE_SEL
_COLLAPSIBLE_HEADER = S.COLLAPSIBLE_HEADER_SEL
_ABOUT_ROUTE = S.ABOUT_ROUTE


def _sub_sel(expr: str) -> str:
    return (expr
        .replace("__QAM_SCOPE__", _QAM_SCOPE)
        .replace("__COLLAPSIBLE_HEADER__", _COLLAPSIBLE_HEADER))


OPEN_QAM_EXPR = """
(function(){
  try {
    const w = SteamUIStore?.WindowStore?.GamepadUIMainWindowInstance;
    if (w?.OnQuickAccessButtonPressed) { w.OnQuickAccessButtonPressed(); return 'ok:OnQuickAccessButtonPressed'; }
    if (w?.ToggleQuickAccessMenu)       { w.ToggleQuickAccessMenu();       return 'ok:ToggleQuickAccessMenu'; }
    const store = SteamUIStore?.GamepadUIStore ?? SteamUIStore?.MainWindowStore;
    if (store?.OpenQuickAccess)          { store.OpenQuickAccess();         return 'ok:GamepadUIStore.OpenQuickAccess'; }
    if (store?.ToggleQuickAccessMenu)    { store.ToggleQuickAccessMenu();   return 'ok:GamepadUIStore.Toggle'; }
    if (SteamClient?.UI?.OpenQuickAccessMenu) {
      SteamClient.UI.OpenQuickAccessMenu(); return 'ok:SteamClient.UI';
    }
    if (SteamClient?.Overlay?.OpenQuickAccessMenu) {
      SteamClient.Overlay.OpenQuickAccessMenu(); return 'ok:SteamClient.Overlay';
    }
    window.dispatchEvent(new CustomEvent('gamepadbutton', { detail: { button: 'qam', pressed: true } }));
    return 'ok:event';
  } catch(e) { return 'error:' + String(e); }
})()
"""

CLOSE_QAM_EXPR = """
(function(){
  try {
    const w = SteamUIStore?.WindowStore?.GamepadUIMainWindowInstance;
    if (w?.OnQuickAccessButtonPressed) { w.OnQuickAccessButtonPressed(); return 'closed:OnQuickAccessButtonPressed'; }
    if (w?.ToggleQuickAccessMenu)       { w.ToggleQuickAccessMenu();       return 'closed:ToggleQuickAccessMenu'; }
    const store = SteamUIStore?.GamepadUIStore ?? SteamUIStore?.MainWindowStore;
    if (store?.CloseQuickAccess)         { store.CloseQuickAccess();        return 'closed:GamepadUIStore.Close'; }
    if (store?.ToggleQuickAccessMenu)    { store.ToggleQuickAccessMenu();   return 'closed:GamepadUIStore.Toggle'; }
    if (SteamClient?.UI?.CloseQuickAccessMenu)      { SteamClient.UI.CloseQuickAccessMenu();      return 'closed:SteamClient.UI'; }
    if (SteamClient?.Overlay?.CloseQuickAccessMenu) { SteamClient.Overlay.CloseQuickAccessMenu(); return 'closed:SteamClient.Overlay'; }
  } catch {}
  return 'no-op';
})()
"""

_NAVIGATE_HOME_EXPR = """
(function(){
  // Instance.Navigate is the only method that reliably leaves a sticky DS
  // full-page route (About / Settings) and lands on the home — must run in
  // SharedJSContext where SteamUIStore lives.
  try {
    var inst = SteamUIStore?.WindowStore?.GamepadUIMainWindowInstance;
    if (inst?.Navigate) { inst.Navigate('/library/home'); return 'instance.Navigate'; }
  } catch(e) {}
  try {
    var nav = SteamUIStore?.WindowStore?.GamepadUIMainWindowInstance?.m_Navigator;
    if (nav?.Home) { nav.Home(); return 'navigator.Home'; }
  } catch(e) {}
  try { SteamClient.Navigation.Navigate('/library/home'); return 'steamclient'; } catch(e) {}
  try { Router.Navigate('/library/home'); return 'router'; } catch(e) {}
  return 'failed';
})()
"""

_OPEN_MAINMENU_EXPR = """
(function(){
  try {
    var inst = SteamUIStore?.WindowStore?.GamepadUIMainWindowInstance;
    if (inst) {
      if (typeof inst.OpenMainMenu === 'function') { inst.OpenMainMenu(); return 'open-instance'; }
      if (typeof inst.OnMainMenuButtonPressed === 'function') { inst.OnMainMenuButtonPressed(); return 'open-button'; }
      if (typeof inst.OnSteamButtonPressed === 'function') { inst.OnSteamButtonPressed(); return 'open-steam'; }
    }
    return 'no-entrypoint';
  } catch(e) { return 'err'; }
})()
"""

_IS_QAM_OPEN_EXPR = """
(function(){
  var qam = document.querySelector('[class*="QuickAccessMenu"], [class*="quickaccessmenu"]');
  if (!qam) return false;
  var cs = getComputedStyle(qam);
  return cs.display !== 'none' && cs.visibility !== 'hidden' && cs.opacity !== '0';
})()
"""

_DS_SCOPE_CHECK = "!!document.querySelector('" + _QAM_SCOPE + "')"

_DECKY_TAB_CLICK = """
(function(){
  if (document.querySelector('__QAM_SCOPE__')) return 'already';
  var tabs = Array.from(document.querySelectorAll('[role=tab]'));
  for (var i = tabs.length - 1; i >= 0; i--) {
    var svg = tabs[i].querySelector('svg');
    if (svg && svg.innerHTML.indexOf('M320') !== -1) { tabs[i].click(); return 'decky'; }
  }
  if (tabs.length) { tabs[tabs.length - 1].click(); return 'last'; }
  return 'no-tabs';
})()
"""

_DS_PLUGIN_CLICK = """
(function(){
  var walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  var node;
  while (node = walker.nextNode()) {
    if ((node.textContent || '').trim() === 'Deck Shelves') {
      var el = node.parentElement;
      for (var i = 0; i < 5 && el; i++) {
        if (el.tagName === 'BUTTON' || el.getAttribute('role') === 'button') {
          el.click(); return 'button';
        }
        el = el.parentElement;
      }
      el = node.parentElement;
      for (var i = 0; i < 8 && el; i++) {
        if (el.classList && el.classList.contains('Focusable')) {
          el.click(); return 'focusable';
        }
        el = el.parentElement;
      }
      return 'found-no-click';
    }
  }
  return 'not-found';
})()
"""

_QAM_PLUGIN_SCROLL_DOWN = """
(function(){
  var ps = document.querySelectorAll('[class*=scroll],[style*=overflow]');
  for (var p of ps) { if (p.scrollHeight > p.clientHeight) { p.scrollTop += 200; return 'scrolled'; } }
  return 'no-scroll';
})()
"""

_CLICK_MAINMENU_HOME_EXPR = """
(function(){
  var candidates = Array.from(document.querySelectorAll(
    'button, [role="button"], .Focusable, [tabindex]:not([tabindex="-1"])'
  )).filter(function(el){
    try {
      var r = el.getBoundingClientRect();
      if (r.width < 40 || r.height < 20) return false;
      var cs = getComputedStyle(el);
      return cs.visibility !== 'hidden' && cs.display !== 'none' && cs.opacity !== '0';
    } catch(_){ return false; }
  });
  if (!candidates.length) return 'empty';
  candidates.sort(function(a, b){
    return a.getBoundingClientRect().top - b.getBoundingClientRect().top;
  });
  candidates[0].click();
  return 'clicked';
})()
"""


# ---------------------------------------------------------------------------
# Surface helpers — run JS in the correct target window.
# SJC (SharedJSContext) has no DOM; DOM manipulation targets BP or QAM.
# ---------------------------------------------------------------------------

def _bp_eval(host: str, port: int, expr: str) -> Any:
    """Run a JS expression in the Big Picture window."""
    try:
        sess = open_session(host, port, "Big Picture")
        try:
            return sess.evaluate(expr)
        finally:
            sess.close()
    except Exception:
        return None


def _qam_eval(host: str, port: int, expr: str) -> Any:
    """Run a JS expression in the QAM popup target."""
    try:
        sess = open_session(host, port, "QuickAccess")
        try:
            return sess.evaluate(expr)
        finally:
            sess.close()
    except Exception:
        return None


def _mainmenu_eval(host: str, port: int, expr: str) -> Any:
    """Run a JS expression in the Steam main-menu (Steam button) target."""
    try:
        sess = open_session(host, port, "MainMenu")
        try:
            return sess.evaluate(expr)
        finally:
            sess.close()
    except Exception:
        return None


def _escape_bp(host: str, port: int, count: int = 1) -> None:
    """Send `count` Escape keypresses to the Big Picture window."""
    try:
        sess = open_session(host, port, "Big Picture")
        try:
            for _ in range(count):
                sess.call("Input.dispatchKeyEvent", {
                    "type": "keyDown", "key": "Escape", "code": "Escape",
                    "windowsVirtualKeyCode": 27, "nativeVirtualKeyCode": 27,
                })
                time.sleep(0.08)
                sess.call("Input.dispatchKeyEvent", {
                    "type": "keyUp", "key": "Escape", "code": "Escape",
                    "windowsVirtualKeyCode": 27, "nativeVirtualKeyCode": 27,
                })
                time.sleep(0.12)
        finally:
            sess.close()
    except Exception:
        pass


def _is_qam_open(host: str, port: int) -> bool:
    """Check if the QAM panel is currently visible in the Big Picture DOM."""
    result = _bp_eval(host, port, _IS_QAM_OPEN_EXPR)
    return result is True


_MODAL_OPEN_CHECK = """
(function(){
  var els = document.querySelectorAll('[class*=Modal]');
  for (var i = 0; i < els.length; i++) {
    if (els[i].getBoundingClientRect().height > 50) return true;
  }
  return false;
})()
"""


def _dismiss_bp_modal(host: str, port: int, max_tries: int = 4) -> None:
    """Close any open Decky/Steam modal in Big Picture via Escape.

    Escape is only sent while a modal is actually present, so on a clean home
    (where Escape would pop the Steam menu) nothing is dispatched.
    """
    for _ in range(max_tries):
        if _bp_eval(host, port, _MODAL_OPEN_CHECK) is not True:
            return
        _escape_bp(host, port, 1)
        time.sleep(0.5)


def open_qam(sjc: Session, settle_ms: int = 1500) -> None:
    try:
        sjc.evaluate(OPEN_QAM_EXPR)
    except Exception:
        pass
    time.sleep(settle_ms / 1000.0)


def close_qam(sjc: Session, settle_ms: int = 800) -> None:
    try:
        sjc.evaluate(CLOSE_QAM_EXPR)
    except Exception:
        pass
    time.sleep(settle_ms / 1000.0)


def navigate_home(sjc: Session, settle_ms: int = 2000) -> None:
    try:
        sjc.evaluate(_NAVIGATE_HOME_EXPR)
    except Exception:
        pass
    time.sleep(settle_ms / 1000.0)


def home_via_mainmenu(sjc: Session, host: str, port: int, settle_ms: int = 3000) -> bool:
    """Land on a clean Home via Steam's main menu — open it, then click its
    top item (the Home entry, language-agnostic), which forcibly navigates
    home and disposes overlays. Returns True when the menu path was used."""
    opened = sjc.evaluate(_OPEN_MAINMENU_EXPR)
    if not (isinstance(opened, str) and opened.startswith("open-")):
        return False
    time.sleep(1.5)
    clicked = _mainmenu_eval(host, port, _CLICK_MAINMENU_HOME_EXPR)
    if clicked == "clicked":
        time.sleep(max(settle_ms / 1000.0, 3.0))
        return True
    return False


def navigate(sjc: Session, route: str, settle_ms: int = 2000) -> None:
    if route in ("/library/home", "/library"):
        navigate_home(sjc, settle_ms=settle_ms)
        return
    expr = f"""(function(){{
      try {{
        var nav = SteamUIStore?.WindowStore?.GamepadUIMainWindowInstance?.m_Navigator;
        if (nav?.LibraryTab) {{ nav.LibraryTab(); return 'navigator.LibraryTab'; }}
      }} catch(e) {{}}
      try {{ Router.Navigate({route!r}); return 'router'; }} catch(e) {{}}
      return 'failed';
    }})()"""
    try:
        sjc.evaluate(expr)
    except Exception:
        pass
    time.sleep(settle_ms / 1000.0)


def navigate_about(sjc: Session, settle_ms: int = 2000) -> None:
    navigate(sjc, _ABOUT_ROUTE, settle_ms)


def click_qam_button(host: str, port: int, svg_hint: str, index: int = 0) -> bool:
    """Click a button in the QAM target whose SVG markup contains `svg_hint`.

    Used for the title-bar icons (book = About `M4 19.5A2.5`, gear = Settings
    `M19.4 15a1.65`) and toolbar actions, matching the legacy capturer.
    """
    expr = """
(function(){
  var btns = document.querySelectorAll('button');
  var m = [];
  for (var i = 0; i < btns.length; i++) {
    if ((btns[i].innerHTML || '').indexOf(%r) !== -1) m.push(btns[i]);
  }
  if (m[%d]) { m[%d].click(); return 'clicked'; }
  return 'not-found';
})()
""" % (svg_hint, index, index)
    return _qam_eval(host, port, expr) == "clicked"


def click_selector(sjc: Session, selector: str, settle_ms: int = 600) -> bool:
    """Click the first element matching the CSS selector in the SJC DOM."""
    expr = f"""
(function(){{
  const el = document.querySelector({selector!r});
  if (!el) return 'not found';
  el.click();
  return 'ok';
}})()
"""
    result = sjc.evaluate(expr)
    time.sleep(settle_ms / 1000.0)
    return result == "ok"


def await_selector(sjc: Session, selector: str, timeout_ms: int = 5000, interval_ms: int = 200) -> bool:
    """Poll until selector exists in the DOM or timeout. Returns True on found."""
    deadline = time.time() + (timeout_ms / 1000.0)
    expr = f"""(function(){{ return !!document.querySelector({selector!r}); }})()"""
    while time.time() < deadline:
        if sjc.evaluate(expr) is True:
            return True
        time.sleep(interval_ms / 1000.0)
    return False


def dismiss_bp_modals(host: str, port: int) -> None:
    """Navigate BP to home to dismiss any open Decky modal or overlay."""
    _bp_eval(host, port, _NAVIGATE_HOME_EXPR)
    time.sleep(1.0)


def ensure_bp_clean(sjc: Session, host: str, port: int) -> None:
    """Navigate to a clean home screen without overlays.

    Preferred path is Steam's main menu (open → click the top/Home item),
    which lands on a clean Home regardless of language and disposes any open
    QAM / overlay. Falls back to a Big-Picture-window navigation when the
    main-menu entry points aren't available on this build.
    """
    # Close any leftover modal first (Escape only fires while one is open).
    _dismiss_bp_modal(host, port)
    # Reliable route change in SJC — leaves a sticky DS full-page route
    # (About / Settings) that the main menu can't dismiss, and lands home.
    navigate_home(sjc, settle_ms=2000)
    if _bp_eval(host, port, "!!document.getElementById('deck-shelves-home-root')") is True:
        return
    # Not home yet (an overlay / Steam menu is up) — use the main menu, then
    # fall back to a BP-window navigation.
    if home_via_mainmenu(sjc, host, port):
        return
    _bp_eval(host, port, _NAVIGATE_HOME_EXPR)
    time.sleep(3.0)


def expand_qam_sections(host: str, port: int) -> str:
    """Force-open all DS QAM CollapsibleSections.

    Sets localStorage so any newly-mounted section defaults to open, then
    dispatches a click event on every header whose innerHTML still contains ▼
    (the collapsed indicator). Uses dispatchEvent(MouseEvent) rather than
    .click() for reliable React synthetic event delivery.
    Scroll is reset to top first so sections render from the beginning.
    """
    expr = r"""
(function(){
  // Reset scroll to top so sections appear in order.
  var scope = document.querySelector('__QAM_SCOPE__');
  if (scope) scope.scrollTop = 0;

  // Pre-open all known sections in localStorage so unmounted ones default open.
  try {
    var KEY = 'ds-qam-sections';
    var state = {};
    try { state = JSON.parse(localStorage.getItem(KEY) || '{}'); } catch(e) {}
    ['behavior','shelves','smart','visual_global','saved_filters'].forEach(function(id){ state[id] = true; });
    localStorage.setItem(KEY, JSON.stringify(state));
  } catch(e) {}

  // Click any currently-collapsed headers (already-mounted components).
  var headers = Array.from(document.querySelectorAll('[data-ds-section]'));
  if (!headers.length) {
    headers = Array.from(document.querySelectorAll('__COLLAPSIBLE_HEADER__'));
  }
  var expanded = 0;
  headers.forEach(function(h) {
    if ((h.innerHTML || '').indexOf('▼') !== -1) {
      h.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true }));
      expanded++;
    }
  });
  return 'expanded:' + expanded + ' of ' + headers.length;
})()
"""
    result = _qam_eval(host, port, _sub_sel(expr)) or "no-result"
    time.sleep(0.8)
    return result


def click_context_menu_edit(host: str, port: int) -> str:
    """Click the 'Edit' item in a Decky context menu (runs in Big Picture target).

    Decky's showContextMenu renders in the Big Picture DOM, not the QAM popup.
    """
    expr = """
(function(){
  var items = document.querySelectorAll('[class*=_MenuItem], [class*=contextMenuItem], [role=menuitem]');
  for (var el of items) {
    var text = (el.textContent || '').trim();
    if (text.indexOf('Edit') !== -1 || text.indexOf('Editar') !== -1 ||
        text.indexOf('Modifier') !== -1 || text.indexOf('Bearbeiten') !== -1) {
      el.click(); return 'clicked:' + text;
    }
  }
  // Fallback: first visible menuitem
  var first = document.querySelector('[role=menuitem]');
  if (first) { first.click(); return 'first-menuitem'; }
  return 'not-found';
})()
"""
    result = _bp_eval(host, port, expr) or "no-result"
    time.sleep(0.3)
    return result


def click_context_menu_delete(host: str, port: int) -> str:
    """Click the 'Delete' item in a Decky context menu (runs in Big Picture target)."""
    expr = """
(function(){
  var items = document.querySelectorAll('[class*=_MenuItem], [class*=contextMenuItem], [role=menuitem]');
  for (var el of items) {
    var text = (el.textContent || '').trim();
    // Contains-match — the item reads "Apagar prateleira" / "Delete shelf" etc.
    if (text.indexOf('Delete') !== -1 || text.indexOf('Apagar') !== -1 ||
        text.indexOf('Deletar') !== -1 || text.indexOf('Remov') !== -1 ||
        text.indexOf('Exclu') !== -1 || text.indexOf('Supprim') !== -1 ||
        text.indexOf('Löschen') !== -1) {
      el.click(); return 'clicked:' + text;
    }
  }
  return 'not-found';
})()
"""
    result = _bp_eval(host, port, expr) or "no-result"
    time.sleep(0.3)
    return result


def _try_navigate_ds_tab(host: str, port: int) -> bool:
    """Single attempt to navigate to Deck Shelves tab in the open QAM.

    Opens a fresh QuickAccess session, clicks the Decky tab, then searches
    for the 'Deck Shelves' plugin entry (with scroll retry). Returns True
    when .deck-shelves-qam-scope is confirmed visible.
    """
    try:
        qam = open_session(host, port, "QuickAccess")
    except Exception:
        return False
    try:
        if qam.evaluate(_DS_SCOPE_CHECK) is True:
            return True
        qam.evaluate(_sub_sel(_DECKY_TAB_CLICK))
        time.sleep(2.0)
        if qam.evaluate(_DS_SCOPE_CHECK) is True:
            return True
        for _ in range(3):
            result = qam.evaluate(_DS_PLUGIN_CLICK)
            if result == "not-found":
                qam.evaluate("""(function(){
  var ps = document.querySelectorAll('[class*=scroll],[style*=overflow]');
  for (var p of ps) { if (p.scrollHeight > p.clientHeight) { p.scrollTop += 200; return; } }
})()""")
                time.sleep(1.0)
                continue
            time.sleep(1.5)
            if qam.evaluate(_DS_SCOPE_CHECK) is True:
                return True
        return False
    finally:
        qam.close()


def navigate_to_ds_qam(sjc: Session, host: str, port: int, settle_ms: int = 2000) -> bool:
    """Open the QAM and ensure the Deck Shelves plugin tab is active.

    The QAM open/closed state is not reliably observable on current Steam
    builds — the QuickAccess CDP target keeps its DOM (7 tab nodes) whether
    the panel is shown or hidden — so a toggle-based open/close desyncs and
    silently closes the panel. Instead we verify the `.deck-shelves-qam-scope`
    after each action and retry, flipping the QAM toggle between attempts so
    that within a couple of passes a tab click lands while the panel is open.
    Home nav runs in the Big Picture window (SJC nav would pop the Steam menu
    overlay); any leftover modal is closed first.
    """
    _dismiss_bp_modal(host, port)
    _bp_eval(host, port, _NAVIGATE_HOME_EXPR)
    time.sleep(1.5)

    for _attempt in range(5):
        if _qam_eval(host, port, _DS_SCOPE_CHECK) is True:
            return True
        # Try to reach DS inside the (possibly open) QAM: Decky tab first.
        _qam_eval(host, port, _sub_sel(_DECKY_TAB_CLICK))
        time.sleep(1.2)
        if _qam_eval(host, port, _DS_SCOPE_CHECK) is True:
            return True
        # Then the "Deck Shelves" plugin-list entry, with a scroll retry.
        for _ in range(2):
            res = _qam_eval(host, port, _DS_PLUGIN_CLICK)
            time.sleep(1.0)
            if _qam_eval(host, port, _DS_SCOPE_CHECK) is True:
                return True
            if res == "not-found":
                _qam_eval(host, port, _QAM_PLUGIN_SCROLL_DOWN)
                time.sleep(0.6)
        # Not reached — flip the QAM toggle (handles a closed panel) and retry.
        sjc.evaluate(OPEN_QAM_EXPR)
        time.sleep(1.6)
    return False
