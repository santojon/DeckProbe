#!/usr/bin/env python3
"""Generic element measurement probe.

Reports the bounding rect + chosen computed-style properties of every element
matching a CSS selector, in the live Steam home document (Big Picture window),
via the SharedJSContext. Read-only — never mutates the page.

Usage (run from the repo root):
  python3 deckprobe/tools/measure_elements.py "<css-selector>"
  python3 deckprobe/tools/measure_elements.py "<css-selector>" transform,transformOrigin,opacity
  python3 deckprobe/tools/measure_elements.py ".ds-per-shelf-hero-img" --chain 4
  python3 deckprobe/tools/measure_elements.py "<selector>" <props> --limit 30

Options:
  <props>      comma-separated computed-style property list (camelCase or kebab).
               Default: transform,transformOrigin,objectPosition,opacity,animationName
  --limit N    cap the number of matched elements (default 20).
  --chain N    also walk N ancestor levels of each match, reporting the same
               props for each (handy for finding which wrapper carries a
               transform/animation).

Env: DECK_CDP_HOST / DECK_CDP_PORT (see .env; defaults 127.0.0.1 / 8081).
"""
import json
import runpy
import sys

DEFAULT_PROPS = ["transform", "transformOrigin", "objectPosition", "opacity", "animationName"]


def build_expr(selector: str, props, limit: int, chain: int) -> str:
    sel = json.dumps(selector)
    pr = json.dumps(props)
    return f"""
(function(){{
  var win = SteamUIStore.WindowStore.GamepadUIMainWindowInstance.BrowserWindow;
  var doc = win.document, w = win;
  var props = {pr}, chain = {chain};
  function snap(el){{
    if(!el) return null;
    var cs = w.getComputedStyle(el), r = el.getBoundingClientRect(), o = {{
      tag: el.tagName.toLowerCase(),
      cls: (el.className || '').toString().slice(0, 80),
      top: Math.round(r.top*100)/100, left: Math.round(r.left*100)/100,
      width: Math.round(r.width*100)/100, height: Math.round(r.height*100)/100
    }};
    props.forEach(function(p){{ o[p] = cs[p]; }});
    return o;
  }}
  var els = [].slice.call(doc.querySelectorAll({sel})).slice(0, {limit});
  var out = els.map(function(el, i){{
    var m = snap(el); m.i = i;
    if(chain > 0){{
      var anc = [], p = el.parentElement, n = 0;
      while(p && n < chain){{ anc.push(snap(p)); p = p.parentElement; n++; }}
      m.ancestors = anc;
    }}
    return m;
  }});
  return JSON.stringify({{ selector: {sel}, count: els.length, elements: out }});
}})()
"""


def main():
    args = list(sys.argv[1:])
    if not args:
        sys.stderr.write(__doc__)
        print(json.dumps({"error": "missing-selector"}))
        sys.exit(2)

    selector = args[0]
    rest = args[1:]
    limit, chain = 20, 0

    def take_opt(name, cast):
        nonlocal rest
        if name in rest:
            i = rest.index(name)
            try:
                val = cast(rest[i + 1])
                del rest[i:i + 2]
                return val
            except (IndexError, ValueError):
                del rest[i:i + 1]
        return None

    v = take_opt("--limit", int)
    if v is not None:
        limit = v
    v = take_opt("--chain", int)
    if v is not None:
        chain = v

    props = [p.strip() for p in rest[0].split(",") if p.strip()] if rest else DEFAULT_PROPS

    g = runpy.run_path("deckprobe/tools/cdp_probe.py")
    eval_in_shared = g.get("eval_in_shared")
    if not eval_in_shared:
        print(json.dumps({"error": "eval_in_shared not available"}))
        sys.exit(2)

    try:
        res = eval_in_shared(build_expr(selector, props, limit, chain))
        data = json.loads(res) if isinstance(res, str) else res
        print(json.dumps(data, indent=2, ensure_ascii=False))
        sys.exit(0)
    except Exception as e:  # noqa: BLE001 - report any probe/connection failure verbatim
        print(json.dumps({"error": str(e)}))
        sys.exit(2)


if __name__ == "__main__":
    main()
