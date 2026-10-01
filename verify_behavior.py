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

Service Worker scenarios run separately:  python3 verify_behavior.py --sw [--previous DIR]
(verify_release.py runs both).

One test while editing it:  python3 verify_behavior.py --only NAME
  NAME is a flow case, guard, state rule or validation row name, or priority_suite.
Browser jobs: --jobs 1 (default, one after another), 2 or 3 (in parallel). Parallel runs give the same
PASS/FAIL verdict, but a Back/Forward or language check may land in a different test, so use 2/3 only as a
quick look while editing; the handover check uses the default. The Service Worker suite always runs one by one.

Requires:  pip install playwright  &&  python -m playwright install chromium
"""
import asyncio, difflib, sys
sys.dont_write_bytecode = True  # keep the release tree free of __pycache__

import vb_core, vb_flows, vb_guards, vb_priority, vb_sw, vb_validation
globals().update({k: v for k, v in vars(vb_core).items() if not k.startswith("__")})
globals().update({k: v for k, v in vars(vb_flows).items() if not k.startswith("__")})
globals().update({k: v for k, v in vars(vb_guards).items() if not k.startswith("__")})


async def runtime():
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        ck("runtime: playwright installed (pip install playwright && python -m playwright install chromium)", False)
        return
    async with async_playwright() as p:
        try:
            browser = await launch_chromium(p)
        except Exception as ex:
            ck("runtime: Chromium available (Playwright-managed or /usr/bin/chromium)", False, str(ex)[:120])
            return
        async def guard(r, name): ck(f"guard implemented: {name}", await g(r, name))
        async def state_rule(r, name): ck(f"state rule implemented: {name}", await rule(r, name))
        jobs = [run_job(browser, name, fn) for name, fn in CASES]
        jobs += [run_job(browser, name, lambda r, name=name: guard(r, name)) for name in SPEC["guards"]]
        jobs += [run_job(browser, name, lambda r, name=name: state_rule(r, name)) for name in SPEC["state_rules"]]
        await run_jobs(jobs)
        await browser.close()

    ck("runtime: no transition outside the spec", not unexpected, " | ".join(sorted(set(unexpected))[:8]))
    miss = [k for k in EDGE_INDEX if k not in covered]
    ck(f"runtime: all {len(EDGE_INDEX)} spec branches executed ({len(covered)} hit)", not miss,
       " | ".join(f"{k[0]} '{k[1]}' {list(k[5])} --{k[2]}--> {k[3]} '{k[4]}'" for k in miss[:8]))
    nav = [k for k in covered if not k[3].startswith("external:")]
    ck(f"runtime: Back + Forward verified for all {len(nav)} in-app branches", all(k in back_verified for k in nav))
    tg = {(s, t) for s, ts in SPEC["toggles"].items() for t in ts}
    ck("runtime: every toggle control exercised", tg <= toggles_hit, str(sorted(tg - toggles_hit)))
    lm = [t for t in SPEC["preview_languages"] if t not in lang_checked]
    ck("runtime: language buttons checked on every preview type", not lm, str(lm))


async def only(name):
    """Run one named test; a mistyped name lists the closest names."""
    from playwright.async_api import async_playwright
    cases = dict(CASES)
    async def guard(r): ck(f"guard implemented: {name}", await g(r, name))
    async def state_rule(r): ck(f"state rule implemented: {name}", await rule(r, name))
    if name == "priority_suite":
        await vb_priority.priority_suite(); return
    fn = (cases.get(name) or (guard if name in SPEC["guards"] else None)
          or (state_rule if name in SPEC["state_rules"] else None)
          or ((lambda r: vb_validation.check_row(r, vb_validation.ROWS[name])) if name in vb_validation.ROWS else None))
    if fn is None:
        names = list(cases) + SPEC["guards"] + SPEC["state_rules"] + list(vb_validation.ROWS) + ["priority_suite"]
        ck(f"--only: no test named {name!r}", False, "closest: " + ", ".join(difflib.get_close_matches(name, names, 8, 0.3)))
        return
    async with async_playwright() as p:
        browser = await launch_chromium(p)
        r = await Run(browser, name).open(); await fn(r); await r.close()
        await browser.close()


if __name__ == "__main__":
    workers()  # reject a bad --jobs value before any test starts

if __name__ == "__main__" and "--only" in sys.argv:
    asyncio.run(only(sys.argv[sys.argv.index("--only") + 1]))
    print("PASS: --only" if not vb_core.failed else "FAIL: --only")
    sys.exit(1 if vb_core.failed else 0)

if __name__ == "__main__" and "--priority" in sys.argv:
    static_checks()
    asyncio.run(vb_priority.priority_gate())
    print("PASS: priority release gate" if not vb_core.failed else "FAIL: priority release gate")
    sys.exit(1 if vb_core.failed else 0)

if __name__ == "__main__" and "--sw" in sys.argv:
    prev = sys.argv[sys.argv.index("--previous") + 1] if "--previous" in sys.argv else None
    asyncio.run(vb_sw.sw_suite(prev))
    print("PASS: service worker scenarios" if not vb_core.failed else "FAIL: service worker scenarios")
    sys.exit(1 if vb_core.failed else 0)

if __name__ == "__main__":
    static_checks()
    asyncio.run(runtime())
    print("PASS: flow behaviour" if not vb_core.failed else "FAIL: flow behaviour")
    sys.exit(1 if vb_core.failed else 0)
