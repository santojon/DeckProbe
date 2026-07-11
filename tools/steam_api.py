#!/usr/bin/env python3
"""Explore a SteamClient API surface in the SharedJSContext.

Lists the own-enumerable keys (methods / sub-namespaces) of a SteamClient path,
optionally filtered by a case-insensitive regex. Handy for discovering obfuscated
method names (e.g. dock / display / battery registrations) without guessing.

Env: DECK_CDP_HOST, DECK_CDP_PORT (like every deckprobe tool).

Usage:
  python3 steam_api.py                       # keys of SteamClient
  python3 steam_api.py System                # keys of SteamClient.System
  python3 steam_api.py System.Dock           # keys of SteamClient.System.Dock
  python3 steam_api.py System --filter dock  # keys of SteamClient.System matching /dock/i
  python3 steam_api.py --root window.appStore # any global, not just SteamClient
"""
import argparse
import json
import runpy
import sys


def _eval():
    g = runpy.run_path("deckprobe/tools/cdp_probe.py")
    fn = g.get("eval_in_shared")
    if not fn:
        print(json.dumps({"error": "eval_in_shared not available"}))
        sys.exit(2)
    return fn


def main() -> int:
    ap = argparse.ArgumentParser(description="Explore a SteamClient API surface.")
    ap.add_argument("path", nargs="?", default="", help="dotted path under the root, e.g. System.Dock")
    ap.add_argument("--root", default="SteamClient", help="root global (default: SteamClient)")
    ap.add_argument("--filter", default="", help="case-insensitive regex to filter keys")
    args = ap.parse_args()

    target = args.root + ("." + args.path if args.path else "")
    rx = args.filter.replace("\\", "\\\\").replace("'", "\\'")
    expr = (
        "(function(){try{var o=%s;if(o==null)return JSON.stringify({error:'undefined path'});"
        "var keys=[];for(var k in o){keys.push(k);}"
        "%s"
        "return JSON.stringify({path:%r,type:typeof o,count:keys.length,keys:keys.sort()});"
        "}catch(e){return JSON.stringify({error:String(e)});}})()"
    ) % (
        target,
        ("var re=new RegExp('%s','i');keys=keys.filter(function(k){return re.test(k);});" % rx) if args.filter else "",
        target,
    )
    res = _eval()(expr)
    try:
        print(json.dumps(json.loads(res), ensure_ascii=False, indent=2))
    except Exception:
        print(res)
    return 0


if __name__ == "__main__":
    sys.exit(main())
