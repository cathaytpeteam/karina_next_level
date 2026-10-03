#!/usr/bin/env python3
"""Find Pax — flow behaviour regression.

The other verifiers check that files are intact and that locked HTML/copy did not
change. This one drives the real app in headless Chromium and checks what staff
actually experience:

  1. Static route scan   – every go(...) route in index.html (button handlers and
                           the NEXT map) must match flow-behavior-spec.json, and every
                           step number in the spec must match FLOWS[].steps.
  2. Control inventory   – every screen and every button on a screen must be covered
                           by the spec (a new button without a spec entry fails).
  3. Branch execution    – every outgoing edge in the spec is executed in the browser:
                           screen, progress title, progress bar, Next enabled state.
                           Any transition NOT in the spec fails as "unexpected".
  4. Back / Forward      – after every in-app transition, Back must return to the
                           source screen/title and browser Forward must restore it.
  5. Guards              – invalid inputs keep Next disabled and show a red border.
  6. State rules         – mode switches clear inputs, Back keeps inputs, etc.
  7. Send                – the final WhatsApp / SMS / call URL has the right scheme,
                           phone number and the values typed in.

Moving a page or re-routing a button changes the static route set and the runtime
transitions, so the run fails until the spec lists every outgoing branch of that
screen - and then all of those branches are executed on every run.

Every test belongs to one layer (vb_core.LAYERS: 安全, 送出內容, 資料清除, 輸入規則, 流程, 能開能更新, 外觀);
vb_priority.py holds the plan. The safety layer runs first and stops the run if it fails.

  python3 verify_behavior.py --full          every test once (default)
  python3 verify_behavior.py --fast          the FAST selection; add --no-look to skip appearance
  python3 verify_behavior.py --sw [--previous DIR]   Service Worker scenarios (its two modes at once with --jobs 2/3)
  python3 verify_behavior.py --only NAME     one test while editing (flow case, guard, state rule,
                                             validation row or plan name such as "privacy at run time")
  --jobs 1|2|3   browser jobs at the same time (default 3 with --fast, otherwise 1)   --timing   list the slowest jobs
verify_release.py runs these for you and prints one summary per layer.

Requires:  pip install playwright  &&  python -m playwright install chromium
"""
import asyncio, sys
sys.dont_write_bytecode = True  # keep the release tree free of __pycache__

import vb_core, vb_priority, vb_sw
from vb_core import ck, static_checks, workers


def finish(label, skipped=()):
    if "--timing" in sys.argv:
        for t, name in sorted(vb_core.JOB_TIMES, reverse=True)[:15]:
            print(f"TIME {t:5.1f}s  {name}")
    vb_core.print_layer_counts(skipped)
    print(f"PASS: {label}" if not vb_core.failed else f"FAIL: {label}")
    sys.exit(1 if vb_core.failed else 0)


if __name__ == "__main__":
    workers()  # reject a bad --jobs value before any test starts
    if "--only" in sys.argv:
        asyncio.run(vb_priority.only(sys.argv[sys.argv.index("--only") + 1]))
        finish("--only")
    if "--sw" in sys.argv:
        vb_core._LAYER.set("open")
        prev = sys.argv[sys.argv.index("--previous") + 1] if "--previous" in sys.argv else None
        asyncio.run(vb_sw.sw_suite(prev))
        finish("service worker scenarios", set(vb_priority.LAYER_ORDER) - {"open"})
    fast = "--fast" in sys.argv
    static_checks()  # route scan and control inventory (flow layer)
    skipped = asyncio.run(vb_priority.run(fast, look="--no-look" not in sys.argv))
    finish("fast browser checks" if fast else "full browser checks", skipped)
