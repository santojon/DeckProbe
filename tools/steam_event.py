#!/usr/bin/env python3
"""Capture a SteamClient `RegisterFor*` event payload in the SharedJSContext.

Most SteamClient state (battery, dock, airplane mode, brightness, …) is exposed
only through `RegisterForXChanges(cb)` callbacks — there is no synchronous getter.
`cdp_eval` can't await a callback that fires after a delay, so this tool does the
reliable two-step dance: subscribe (stashing the event on a window global), wait,
then read it back and unregister. Values that are objects are shown as `[obj]`.

Env: DECK_CDP_HOST, DECK_CDP_PORT.

Usage:
  python3 steam_event.py System.RegisterForBatteryStateChanges
  python3 steam_event.py System.Dock.RegisterForStateChanges --wait 3
"""
import argparse
import json
import runpy
import sys
import time


def _eval():
    g = runpy.run_path("deckprobe/tools/cdp_probe.py")
    fn = g.get("eval_in_shared")
    if not fn:
        print(json.dumps({"error": "eval_in_shared not available"}))
        sys.exit(2)
    return fn


def main() -> int:
    ap = argparse.ArgumentParser(description="Capture a SteamClient RegisterFor* event payload.")
    ap.add_argument("path", help="registration method under SteamClient, e.g. System.RegisterForBatteryStateChanges")
    ap.add_argument("--wait", type=float, default=2.0, help="seconds to wait for an event (default: 2)")
    ap.add_argument("--root", default="SteamClient", help="root global (default: SteamClient)")
    args = ap.parse_args()

    ev = _eval()
    subscribe = (
        "(function(){try{window.__deckprobe_evt='pending';"
        "var reg=%s.%s(function(e){var out={};try{if(e&&typeof e==='object'){for(var k in e){var v=e[k];"
        "out[k]=(v&&typeof v==='object')?'[obj]':v;}}else{out={value:e};}}catch(x){out={err:String(x)};}"
        "window.__deckprobe_evt=out;});window.__deckprobe_reg=reg;"
        "return JSON.stringify({subscribed:true});}catch(e){return JSON.stringify({error:String(e)});}})()"
    ) % (args.root, args.path)

    sub = ev(subscribe)
    try:
        if json.loads(sub).get("error"):
            print(sub)
            return 2
    except Exception:
        print(sub)
        return 2

    time.sleep(max(0.2, args.wait))

    read = (
        "(function(){try{var r=window.__deckprobe_reg;if(r&&r.unregister)r.unregister();}catch(e){}"
        "var v=window.__deckprobe_evt;try{delete window.__deckprobe_evt;delete window.__deckprobe_reg;}catch(e){}"
        "return JSON.stringify(v);})()"
    )
    res = ev(read)
    try:
        payload = json.loads(res)
        print(json.dumps({"event": payload}, ensure_ascii=False, indent=2))
        if payload == "pending":
            print("(no event fired within the wait window — try a longer --wait or a state change)", file=sys.stderr)
    except Exception:
        print(res)
    return 0


if __name__ == "__main__":
    sys.exit(main())
