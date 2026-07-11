#!/usr/bin/env python3
"""Inspect Steam AppOverview data in the SharedJSContext.

Two modes:
  * default — dump one real app's AppOverview fields (optionally filtered by a
    regex), for discovering obfuscated field names (per_client_data,
    is_available_on_current_platform, display_status, …).
  * --stats — aggregate install/platform state across the whole library
    (local / remote / remote-only / both + available-on-current-platform),
    which is exactly what the system-compatibility and Remote Play filters read.

Env: DECK_CDP_HOST, DECK_CDP_PORT.

Usage:
  python3 app_overview.py                       # first Steam app, all fields
  python3 app_overview.py --appid 730           # a specific app
  python3 app_overview.py --filter 'client|os'  # only matching fields
  python3 app_overview.py --stats               # library-wide per-client stats
"""
from __future__ import annotations

import argparse
import json
import runpy
import sys

_APPS = "var cs=window.collectionStore;var apps=(cs&&cs.allAppsCollection&&cs.allAppsCollection.allApps)||[];"

_STATS = (
    "(function(){%s var I=11;var s={total:0,steam:0,avail_true:0,avail_false:0,avail_undef:0,"
    "local:0,remote:0,remoteOnly:0,both:0};for(var i=0;i<apps.length;i++){var a=apps[i];if(!a)continue;s.total++;"
    "var pcd=Array.isArray(a.per_client_data)?a.per_client_data:[];var rem=Array.isArray(a.remote_per_client_data)?a.remote_per_client_data:[];"
    "if(pcd.length===0&&rem.length===0)continue;s.steam++;"
    "var loc=pcd.filter(function(c){return String(c.clientid)==='0';})[0];"
    "var av=loc&&typeof loc.is_available_on_current_platform==='boolean'?loc.is_available_on_current_platform:undefined;"
    "if(av===true)s.avail_true++;else if(av===false)s.avail_false++;else s.avail_undef++;"
    "var rl=rem.length?rem:pcd.filter(function(c){return String(c.clientid)!=='0';});"
    "var ir=rl.some(function(c){return Number(c.display_status)===I;});"
    "var il=a.installed===true||(loc&&Number(loc.display_status)===I);"
    "if(il)s.local++;if(ir)s.remote++;if(ir&&!il)s.remoteOnly++;if(il&&ir)s.both++;}"
    "return JSON.stringify(s);})()"
) % _APPS


def _dump_expr(appid: int | None, rx: str) -> str:
    pick = (
        ("for(var i=0;i<apps.length;i++){if(apps[i]&&Number(apps[i].appid)===%d){app=apps[i];break;}}" % appid)
        if appid is not None
        else "for(var i=0;i<apps.length;i++){var x=apps[i];if(x&&(x.per_client_data&&x.per_client_data.length)){app=x;break;}}if(!app)app=apps[0];"
    )
    flt = ("var re=new RegExp('%s','i');keys=keys.filter(function(k){return re.test(k);});" % rx) if rx else ""
    return (
        "(function(){%s var app=null;%s if(!app)return JSON.stringify({error:'no app'});"
        "var keys=[];for(var k in app)keys.push(k);%s"
        "var out={};keys.sort().forEach(function(k){try{var v=app[k];out[k]=(v&&typeof v==='object')?(Array.isArray(v)?('[array '+v.length+']'):'[obj]'):v;}catch(e){out[k]='<err>';}});"
        "return JSON.stringify({appid:app.appid,name:app.display_name,count:keys.length,fields:out});})()"
    ) % (_APPS, pick, flt)


def main() -> int:
    ap = argparse.ArgumentParser(description="Inspect Steam AppOverview data.")
    ap.add_argument("--appid", type=int, default=None, help="specific appid (default: first Steam app)")
    ap.add_argument("--filter", default="", help="case-insensitive regex to filter fields")
    ap.add_argument("--stats", action="store_true", help="library-wide per-client install/platform stats")
    args = ap.parse_args()

    g = runpy.run_path("deckprobe/tools/cdp_probe.py")
    fn = g.get("eval_in_shared")
    if not fn:
        print(json.dumps({"error": "eval_in_shared not available"}))
        return 2

    rx = args.filter.replace("\\", "\\\\").replace("'", "\\'")
    expr = _STATS if args.stats else _dump_expr(args.appid, rx)
    res = fn(expr)
    try:
        print(json.dumps(json.loads(res), ensure_ascii=False, indent=2))
    except Exception:
        print(res)
    return 0


if __name__ == "__main__":
    sys.exit(main())
