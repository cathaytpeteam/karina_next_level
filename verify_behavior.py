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

Requires:  pip install playwright  &&  python -m playwright install chromium
"""
from pathlib import Path
import asyncio, json, re, sys, urllib.parse

R = Path(__file__).resolve().parent
N_ASSETS = len(re.findall(r'"\./[^"]*"', re.search(r'const ASSETS=\[(.*?)\];', (R / "sw.js").read_text(encoding="utf-8"), re.S).group(1)))
HTML = (R / "index.html").read_text(encoding="utf-8")
# Browser-flow tests use set_content() because managed Chromium may block file://.
# Inline modular local assets so set_content() matches the deployed app without file:// access.
_APP_CSS = (R / "app.css").read_text(encoding="utf-8")
_COPY_JS = (R / "copy.js").read_text(encoding="utf-8")
_APP_JS = (R / "app.js").read_text(encoding="utf-8")
HTML = HTML.replace('<link rel="stylesheet" href="./app.css">', '<style>'+_APP_CSS+'</style>')
HTML = HTML.replace('<script src="./copy.js"></script>', '<script>'+_COPY_JS+'</script>')
HTML = HTML.replace('<script src="./app.js"></script>', '<script>'+_APP_JS+'</script>')
_COPY_MATCH = re.search(r'window\.FIND_PAX_COPY\s*=\s*Object\.freeze\((\{.*\})\);', _COPY_JS, re.S)
COPY = json.loads(_COPY_MATCH.group(1)) if _COPY_MATCH else {}
SPEC = json.loads((R / "flow-behavior-spec.json").read_text(encoding="utf-8"))
PHONE = "886983952902"

failed = False

async def launch_chromium(p):
    try:
        return await p.chromium.launch(headless=True)
    except Exception:
        return await p.chromium.launch(executable_path="/usr/bin/chromium", headless=True, args=["--no-sandbox","--disable-dev-shm-usage"])

def ck(name, ok, detail=""):
    global failed
    print(("PASS " if ok else "FAIL ") + name + ("" if ok or not detail else "  -> " + detail))
    if not ok:
        failed = True
    return ok

# ---------------------------------------------------------------------------
# 1 + 2. Static checks
# ---------------------------------------------------------------------------
def fn_body(name):
    L = HTML.splitlines()
    for i, x in enumerate(L):
        if re.match(r"\s*function " + re.escape(name) + r"\(", x):
            ind = len(x) - len(x.lstrip())
            for j in range(i, len(L)):
                if j > i and L[j].startswith(" " * ind + "}") and len(L[j]) - len(L[j].lstrip()) == ind:
                    return "\n".join(L[i:j + 1])
            return x
    return ""

def go_targets(body, depth=0, seen=None):
    seen = seen or set()
    out = set(re.findall(r'\bgo\("(\w+)"\)', body))
    if re.search(r"\bsend\(\)", body):
        out.add("external")
    if depth < 3:
        for f in set(re.findall(r"\b([A-Za-z_]\w*)\(", body)):
            if f in seen or f in ("go", "send", "if", "for", "while", "catch", "function", "setOrder"):
                continue
            b = fn_body(f)
            if b:
                seen.add(f)
                out |= go_targets(b, depth + 1, seen)
    return out

def static_checks():
    sections = re.findall(r'<section\b[^>]*\bid="s-([a-z0-9]+)"[^>]*>(.*?)</section>', HTML, re.S)
    screens = [s for s, _ in sections]
    ck("static: every screen in index.html is in the behaviour spec",
       set(screens) == set(SPEC["screens"]),
       f"html-only={sorted(set(screens)-set(SPEC['screens']))} spec-only={sorted(set(SPEC['screens'])-set(screens))}")

    btn_screen = {}
    for sid, body in sections:
        for bid in re.findall(r'<button\b[^>]*\bid="([A-Za-z0-9]+)"', body):
            btn_screen[bid] = sid

    triggers = {(e["from"], e["trigger"]) for e in SPEC["edges"]}
    toggles = {(s, t) for s, ts in SPEC["toggles"].items() for t in ts}
    untested = sorted(f"{s}:{b}" for b, s in btn_screen.items() if (s, b) not in triggers | toggles)
    ck("static: every button on every screen has a spec branch or toggle", not untested, ", ".join(untested))

    # Routes from button handlers
    static = set()
    for bid, rest in re.findall(r'\$\("(\w+)"\)\.onclick=(.*)', HTML):
        if bid in btn_screen:
            for t in go_targets(rest):
                static.add((btn_screen[bid], bid, t))
    # Routes from the NEXT map (the Next / Send button)
    m = re.search(r"\n  const NEXT=\{\n(.*?)\n  \};", HTML, re.S)
    ck("static: NEXT map found", bool(m))
    if m:
        block = m.group(1)
        keys = list(re.finditer(r"\b(\w+):\(\)=>", block))
        for i, k in enumerate(keys):
            body = block[k.end(): keys[i + 1].start() if i + 1 < len(keys) else len(block)]
            for t in go_targets(body):
                static.add((k.group(1), "cta", t))

    spec_routes = set()
    for e in SPEC["edges"]:
        to = "external" if e["to"].startswith("external:") else e["to"]
        spec_routes.add((e["from"], e["trigger"], to))
    missing = sorted(static - spec_routes)
    extra = sorted(spec_routes - static)
    moved = sorted({x[0] for x in missing + extra})
    ck("static: routes in index.html == routes in spec", not missing and not extra,
       f"moved/changed screens={moved}; in code but not spec={missing}; in spec but not code={extra}")

    # FLOWS step order vs spec progress titles
    flows = {k: (n, [x.strip().strip('"') for x in st.split(",")])
             for k, n, st in re.findall(r'(\w+):\{name:"([^"]+)",steps:\[([^\]]*)\]\}', HTML)}
    by_name = {}
    for _, (n, steps) in flows.items():
        by_name.setdefault(n, []).append(steps)
    bad = []
    for e in SPEC["edges"]:
        for scr, title in ((e["from"], e["from_title"]), (e["to"], e["to_title"])):
            mm = re.match(r"(.+?) - (\d+)/(\d+)", title or "")
            if not mm or "Call Directly" in title:
                continue
            name, i, n = mm.group(1), int(mm.group(2)), int(mm.group(3))
            steps = next((x for x in by_name.get(name, []) if len(x) == n), None)
            if not steps:
                bad.append(f"{title}: FLOWS has {by_name.get(name)}")
                continue
            if scr == "preview" and name == "漏查":
                continue  # 漏查 preview is the completed 3/3 result
            if steps[i - 1] != scr:
                bad.append(f"{scr} shown as {i}/{n} but FLOWS step {i} is {steps[i-1]}")
    ck("static: spec progress numbers match FLOWS step order", not bad, "; ".join(sorted(set(bad))))

# ---------------------------------------------------------------------------
# 3-7. Runtime
# ---------------------------------------------------------------------------
EDGE_INDEX = {}
for e in SPEC["edges"]:
    EDGE_INDEX[(e["from"], e["from_title"], e["trigger"], e["to"], e["to_title"], tuple(e.get("from_state", [])))] = e
covered, back_verified, toggles_hit, unexpected = set(), set(), set(), []
lang_checked = {}

STATE_JS = """() => {
  const scr = document.querySelector('.screen:not([hidden])');
  const id = scr ? scr.id.replace(/^s-/, '') : '';
  const q = s => document.querySelector(s);
  return {
    screen: id,
    title: (q('#step').textContent || '').replace(/\\s+/g, ' ').trim(),
    cta_disabled: q('#cta').disabled,
    foot_hidden: q('#foot').hidden,
    back_hidden: q('#back').hidden,
    bar_hidden: q('#bar').hidden,
    bar: q('#barFill').style.width,
    pressed: scr ? [...scr.querySelectorAll('button[aria-pressed="true"]')].map(b => b.id) : [],
    langs: [...document.querySelectorAll('#previewLangSeg button')].filter(b => !b.hidden).map(b => b.id),
    bad: [...document.querySelectorAll('.screen:not([hidden]) .field.bad input, .screen:not([hidden]) .field.bad select')].map(i => i.id),
  };
}"""

class Run:
    def __init__(self, browser, name):
        self.browser, self.name, self.nav = browser, name, []

    async def open(self):
        self.ctx = await self.browser.new_context(viewport={"width": 390, "height": 844})
        self.pg = await self.ctx.new_page()
        self.errors = []
        self.pg.on("pageerror", lambda e: self.errors.append(str(e)))
        cdp = await self.ctx.new_cdp_session(self.pg)
        cdp.on("Page.frameRequestedNavigation", lambda ev: self.nav.append(ev["url"]))
        await cdp.send("Page.enable")
        # Load the exact app document without relying on file://, which is blocked by some
        # managed Chromium policies. The bundled phone library is inlined only in the test page.
        lib = (R / "libphonenumber-max.js").read_text(encoding="utf-8")
        doc = HTML.replace('</head>', '<script>' + lib + '</script></head>')
        await self.pg.set_content(doc, wait_until="domcontentloaded")
        await self.pg.wait_for_selector("#s-phone:not([hidden])")
        return self

    async def close(self):
        ck(f"[{self.name}] no JavaScript errors", not self.errors, "; ".join(self.errors[:3]))
        await self.ctx.close()

    async def st(self):
        return await self.pg.evaluate(STATE_JS)

    async def wait(self, pred, ms=3000):
        for _ in range(ms // 50):
            s = await self.st()
            if pred(s):
                return s
            await self.pg.wait_for_timeout(50)
        return await self.st()

    async def fill(self, id_, val):
        loc = self.pg.locator("#" + id_)
        if await loc.evaluate("e => e.tagName") == "SELECT":
            await loc.select_option(val)
        else:
            await loc.fill(val)
        await self.pg.wait_for_timeout(30)

    async def blur(self, id_):
        await self.pg.locator("#" + id_).evaluate("e => e.blur()")
        await self.pg.wait_for_timeout(60)

    async def val(self, id_):
        return await self.pg.locator("#" + id_).input_value()

    def state_sig(self, s):
        ctl = SPEC["state_controls"].get(s["screen"], [])
        return tuple(x for x in s["pressed"] if x in ctl)

    def check_screen(self, s, where):
        m = re.match(r".+? - (\d+)/(\d+)", s["title"])
        if m and not s["bar_hidden"]:
            want = int(m.group(1)) / int(m.group(2)) * 100
            got = float((s["bar"] or "0").rstrip("%") or 0)
            if abs(want - got) > 0.6:
                ck(f"[{self.name}] progress bar matches '{s['title']}' at {where}", False, f"bar={s['bar']}")
        if s["screen"] == "preview" and s["title"] in SPEC["preview_languages"] and s["title"] not in lang_checked:
            want = SPEC["preview_languages"][s["title"]]
            lang_checked[s["title"]] = ck(f"preview '{s['title']}' language buttons", s["langs"] == want, f"got {s['langs']}")

    async def act(self, trigger, expect_to=None, text_has=(), text_not=(), exact=None):
        """Click a control, record the transition and verify it against the spec."""
        before = await self.st()
        sel = "#cta" if trigger == "cta" else "#" + trigger
        if trigger == "cta" and before["cta_disabled"]:
            ck(f"[{self.name}] Next enabled on {before['screen']} ({before['title']})", False)
            return before
        n0 = len(self.nav)
        await self.pg.click(sel)
        if before["screen"] == "preview" and trigger == "cta":
            for _ in range(40):
                if len(self.nav) > n0:
                    break
                await self.pg.wait_for_timeout(50)
            urls = self.nav[n0:]
            url = urls[0] if urls else ""
            if url.startswith("whatsapp://send") and "&text=" in url:
                to = "external:whatsapp"
            elif url.startswith("whatsapp://send"):
                to = "external:whatsapp-call"
            elif url.startswith("sms:"):
                to = "external:sms"
            else:
                to = "external:none"
            self._record(before, trigger, to, "")
            ok = PHONE in url
            text = urllib.parse.unquote(url)
            miss = [t for t in text_has if t not in text]
            extra = [t for t in text_not if t in text]
            ck(f"[{self.name}] send URL has phone and typed values", ok and not miss and not extra, f"url={url[:90]} missing={miss} unexpected={extra}")
            if expect_to:
                ck(f"[{self.name}] send goes to {expect_to}", to == expect_to, f"got {to}")
            if exact is not None:
                key = "body=" if url.startswith("sms:") else "text="
                body = urllib.parse.unquote(url.split(key, 1)[1]) if key in url else ""
                rx, limit = exact
                ck(f"[{self.name}] message text is exactly the locked copy", re.fullmatch(rx, body) is not None, body[:160])
                ck(f"[{self.name}] message fits {limit} chars ({'1' if limit == 67 else '2'} SMS)", len(body) <= limit, f"{len(body)} chars")
            return None
        after = await self.wait(lambda s: s["screen"] != before["screen"] or trigger in SPEC["toggles"].get(before["screen"], []), 1500)
        self.check_screen(after, f"after {trigger}")
        if after["screen"] == before["screen"] and trigger in SPEC["toggles"].get(before["screen"], []):
            toggles_hit.add((before["screen"], trigger))
            return after
        key = self._record(before, trigger, after["screen"], after["title"])
        if expect_to:
            ck(f"[{self.name}] {before['screen']} --{trigger}--> {expect_to}", after["screen"] == expect_to, f"got {after['screen']}")
        if key and key not in back_verified and after["screen"] != before["screen"]:
            back_verified.add(key)
            await self.pg.click("#back")
            b = await self.wait(lambda s: s["screen"] == before["screen"])
            ck(f"Back: {after['screen']} '{after['title']}' -> {before['screen']} '{before['title']}'",
               b["screen"] == before["screen"] and b["title"] == before["title"], f"got {b['screen']} '{b['title']}'")
            self.check_screen(b, "after Back")
            await self.pg.go_forward()
            f = await self.wait(lambda s: s["screen"] == after["screen"])
            ck(f"Forward: {before['screen']} -> {after['screen']} '{after['title']}'",
               f["screen"] == after["screen"] and f["title"] == after["title"], f"got {f['screen']} '{f['title']}'")
            after = f
        return after

    def _record(self, before, trigger, to, to_title):
        key = (before["screen"], before["title"], trigger, to, to_title, self.state_sig(before))
        if key in EDGE_INDEX:
            covered.add(key)
            return key
        unexpected.append(f"{before['screen']} '{before['title']}' {list(key[5])} --{trigger}--> {to} '{to_title}'")
        return None

    async def back(self, to):
        await self.pg.click("#back")
        return await self.wait(lambda s: s["screen"] == to)

    async def phone(self, num=PHONE):
        await self.fill("phoneInput", num)
        return await self.act("cta", "scenario")

    async def expect(self, label, cta_enabled=None, bad=None, not_bad=None):
        s = await self.st()
        ok, why = True, []
        if cta_enabled is not None and s["cta_disabled"] == cta_enabled:
            ok = False; why.append(f"Next {'disabled' if s['cta_disabled'] else 'enabled'}")
        for f in bad or []:
            if f not in s["bad"]:
                ok = False; why.append(f"{f} has no red border")
        for f in not_bad or []:
            if f in s["bad"]:
                ok = False; why.append(f"{f} unexpectedly red")
        ck(f"[{self.name}] {label}", ok, ", ".join(why))
        return s

# ---- helpers to reach screens ----------------------------------------------
async def to_s1(r, mode, flight):
    await r.phone(); await r.act("goMiss", "misstype"); await r.act(mode, "mflight")
    await r.fill("mFlight", flight)

async def to_s2(r, mode, flight):
    await r.phone(); await r.act("goCall", "calltype"); await r.act(mode, "callflight")
    await r.fill("callFlight", flight)

async def to_s4(r, status, flight="407", delay="1800"):
    await r.phone(); await r.act("goDp", "dstatus"); await r.act(status, "dflight")
    await r.fill("dFlight", flight)
    if status == "stDelayed" and delay:
        await r.fill("delayTime", delay)

async def to_s4_gate(r, flight="407", status=None, delay="1830"):
    await r.phone(); await r.act("goDp", "dstatus"); await r.act("stGate", "dflight")
    await r.fill("dFlight", flight)
    if status:
        await r.act(status)
        if status == "gsDelayed":
            await r.fill("delayTime", delay)
        await r.act("cta", "dnew")

async def fill_protect(r, n="401", zone="B", gate="5", dep="1945"):
    # Fills Protect to (3/5) only. Proceed to Gate is its own page (4/5): callers that need it
    # continue with r.act("cta", "dgateaction") and select there.
    await r.fill("gNewN", n); await r.fill("gGateZone", zone); await r.fill("gGate", gate); await r.fill("gDepTime", dep); await r.blur("gDepTime")

# ---- priority release gate -----------------------------------------------------
async def _simple_click(r, id_, screen=None):
    await r.pg.locator("#" + id_).click()
    if screen:
        st = await r.wait(lambda x: x["screen"] == screen, 2000)
        ck(f"[priority] {id_} opens {screen}", st["screen"] == screen, st["screen"])
        return st
    await r.pg.wait_for_timeout(60)
    return await r.st()

async def _priority_phone_to_scenario(r):
    st = await r.st()
    ck("[priority] Phone starts with Next disabled", st["screen"] == "phone" and st["cta_disabled"])
    ck("[priority] Phone starts without a stale red border", "phoneInput" not in st["bad"])
    ck("[priority] Phone country badge starts hidden", await r.pg.locator("#badge").is_hidden())
    await r.fill("phoneInput", PHONE)
    await r.pg.wait_for_timeout(100)
    st = await r.st()
    badge_visible = await r.pg.locator("#badge").is_visible()
    badge_text = (await r.pg.locator("#badge").inner_text()).strip() if badge_visible else ""
    ck("[priority] valid Taiwan phone shows country badge", badge_visible and "TW" in badge_text, badge_text)
    ck("[priority] valid Taiwan phone enables Next", not st["cta_disabled"], str(st))
    await _simple_click(r, "cta", "scenario")

async def priority_suite():
    from playwright.async_api import async_playwright
    global failed
    async with async_playwright() as p:
        browser = await launch_chromium(p)

        # Phone + Home visual geometry on the three locked phone widths.
        r = await Run(browser, "priority-home").open()
        await _priority_phone_to_scenario(r)
        for width, want_gap in ((390, 14), (360, 12), (320, 12)):
            await r.pg.set_viewport_size({"width": width, "height": 844})
            await r.pg.wait_for_timeout(80)
            g = await r.pg.evaluate("""() => [...document.querySelectorAll('#s-scenario .choice')].map(b => {
              const i=b.querySelector('.ico').getBoundingClientRect(), t=b.querySelector('.ctext').getBoundingClientRect(), c=b.querySelector('.chev').getBoundingClientRect(), r=b.getBoundingClientRect();
              return {left:r.left,right:r.right,top:r.top,bottom:r.bottom,iconL:i.left,iconR:i.right,textL:t.left,textR:t.right,chevL:c.left,chevR:c.right};
            })""")
            ck(f"[priority] Home {width}px has five Scenario cards", len(g) == 5, str(len(g)))
            if len(g) == 5:
                gaps=[round(x['textL']-x['iconR'],1) for x in g]
                arrows=[round(x['chevR'],1) for x in g]
                overlap=all(x['textR'] <= x['chevL'] + 0.5 for x in g)
                widths=[round(x['right']-x['left'],1) for x in g]
                ck(f"[priority] Home {width}px icon/text spacing is locked", all(abs(x-want_gap)<=1.5 for x in gaps), str(gaps))
                ck(f"[priority] Home {width}px arrows align in one column", max(arrows)-min(arrows)<=1.5, str(arrows))
                ck(f"[priority] Home {width}px text never overlaps arrow", overlap)
                ck(f"[priority] Home {width}px card widths align", max(widths)-min(widths)<=1.5, str(widths))
        await r.close()

        # Scenario 1 happy path + Joining Passenger label + unchanged progress wording.
        r = await Run(browser, "priority-s1").open(); await _priority_phone_to_scenario(r)
        await _simple_click(r, "goMiss", "misstype")
        ck("[priority] S1 Passenger Type says Joining Passenger", (await r.pg.locator("#missJoin .ctext").inner_text()).strip() == "Joining Passenger")
        await _simple_click(r, "missJoin", "mflight")
        ck("[priority] S1 progress wording uses Joining Passenger", " ".join((await r.pg.locator("#step").inner_text()).split()) == "漏查 - Joining Passenger 2/3", (await r.pg.locator("#step").inner_text()).strip())
        await r.fill("mFlight", "407"); await r.expect("S1 valid CX407 enables Next", True, not_bad=["mFlight"])
        await _simple_click(r, "cta", "msec"); await r.fill("mSec", "123"); await r.expect("S1 valid SEC enables Next", True, not_bad=["mSec"])
        await _simple_click(r, "cta", "preview")
        ck("[priority] S1 reaches Confirm details", (await r.st())["screen"] == "preview")
        await r.close()

        # Scenario 2 happy path.
        r = await Run(browser, "priority-s2").open(); await _priority_phone_to_scenario(r)
        await _simple_click(r, "goCall", "calltype")
        ck("[priority] S2 Passenger Type says Joining Passenger", (await r.pg.locator("#callJoin .ctext").inner_text()).strip() == "Joining Passenger")
        await _simple_click(r, "callJoin", "callflight")
        ck("[priority] S2 progress wording uses Joining Passenger", "Joining Passenger" in (await r.pg.locator("#step").inner_text()))
        await r.fill("callFlight", "407"); await r.expect("S2 valid CX407 enables Next", True, not_bad=["callFlight"])
        await _simple_click(r, "cta", "callgate"); await r.fill("callGate", "5"); await r.expect("S2 valid gate enables Next", True, not_bad=["callGate"])
        await _simple_click(r, "cta", "preview"); ck("[priority] S2 reaches Confirm details", (await r.st())["screen"] == "preview")
        await r.close()

        # Scenario 3 happy path + Confirm details completeness.
        r = await Run(browser, "priority-s3").open(); await _priority_phone_to_scenario(r)
        await _simple_click(r, "goWpp", "wflight"); await r.fill("wFlight", "123"); await r.expect("S3 arrival flight enables Next", True, not_bad=["wFlight"])
        await _simple_click(r, "cta", "bag1"); await r.fill("b1n", "123456"); await r.expect("S3 Bag Tag 1 enables Next", True)
        await _simple_click(r, "cta", "bag2"); await r.fill("b2a", "BR"); await r.fill("b2n", "654321"); await r.expect("S3 Bag Tag 2 enables Next", True)
        await _simple_click(r, "cta", "preview")
        rows = await r.pg.evaluate("[...document.querySelectorAll('#sum div')].map(d => d.querySelector('dt').textContent.trim())")
        ck("[priority] S3 Confirm details has all three summary rows", rows == ["Arrival Flight", "Bag Tag 1", "Bag Tag 2"], str(rows))
        a = await r.pg.locator("#msgToggle>span:first-child").bounding_box(); b = await r.pg.locator("#previewOrderLabel").bounding_box()
        ck("[priority] Message Preview order label has visual separation", bool(a and b) and b["x"] > a["x"] + 110)
        await r.close()

        # Scenario 4: blank is neutral; inbound transit flights rejected; TPE departures accepted.
        r = await Run(browser, "priority-s4").open(); await _priority_phone_to_scenario(r)
        await _simple_click(r, "goDp", "dstatus"); await _simple_click(r, "stGate", "dflight")
        st = await r.st(); ck("[priority] S4 Flight from TPE blank stays neutral", "dFlight" not in st["bad"] and st["cta_disabled"], str(st))
        for n in ("450", "530", "564"):
            await r.fill("dFlight", n); await r.expect(f"S4 CX{n} is not a TPE departure", False, ["dFlight"])
        for n in ("451", "531", "565", "407"):
            await r.fill("dFlight", n); await r.expect(f"S4 CX{n} is accepted as TPE departure", False, not_bad=["dFlight"])
        await r.fill("dFlight", "451"); await _simple_click(r, "gsCancelled")
        await r.expect("S4 CX451 + Cancelled enables Next", True, not_bad=["dFlight"])
        await _simple_click(r, "cta", "dnew")
        st=await r.st(); ck("[priority] S4 Protect to starts neutral", "gNewN" not in st["bad"] and st["cta_disabled"], str(st))
        for n in ("450", "530", "564"):
            await r.fill("gNewN", n); await r.expect(f"S4 Protect to rejects CX{n}", False, ["gNewN"])
        await r.fill("gNewN", "407"); await r.expect("S4 Protect to accepts CX407", False, not_bad=["gNewN"])
        await r.fill("gGate", "9"); await r.fill("gDepTime", "1955"); await r.blur("gDepTime")
        await r.expect("S4 valid Protect to fields enable Next", True, not_bad=["gNewN","gDepTime"])
        await _simple_click(r, "cta", "dgateaction")
        await _simple_click(r, "gProtectedFlight"); await _simple_click(r, "gpAsap")
        await r.expect("S4 Proceed to Gate selection enables Next", True)
        await _simple_click(r, "cta", "preview"); ck("[priority] S4 reaches Confirm details", (await r.st())["screen"] == "preview")
        await r.close()

        # Scenario 4 non-gate happy path: every page with valid input must enable Next.
        r = await Run(browser, "priority-s4-flow").open(); await _priority_phone_to_scenario(r)
        await _simple_click(r, "goDp", "dstatus"); await _simple_click(r, "stPossible", "dflight")
        await r.fill("dFlight", "451"); await r.expect("S4 Tight Connection flight enables Next", True, not_bad=["dFlight"])
        await _simple_click(r, "cta", "dtransfer")
        await r.fill("tA", "BR"); await r.fill("tN", "123"); await r.expect("S4 Connecting flight enables Next", True, not_bad=["tN"])
        await _simple_click(r, "cta", "darrange"); await _simple_click(r, "arUnknown")
        await r.expect("S4 arrangement choice enables Next", True)
        await _simple_click(r, "cta", "darrive"); await r.fill("arriveTime", "1400"); await r.expect("S4 arrival time enables Next", True, not_bad=["arriveTime"])
        await _simple_click(r, "cta", "preview"); ck("[priority] S4 non-gate flow reaches Confirm details", (await r.st())["screen"] == "preview")
        await r.close()

        await browser.close()

# ---- locked Japanese SMS copy (copy.js) -----------------------------------
def ja_expected(scen, mode, flight=None, gate=None):
    if scen == "s1":
        t = COPY[f"s1.{mode}.ja"]
        return re.escape(t), (134 if mode == "join" else 67)
    t = COPY[f"s2.{mode}.ja"]
    rx = re.escape(t).replace(re.escape("{Flight}"), re.escape(flight)).replace(re.escape("{Gate}"), re.escape(gate))
    if mode == "transit":
        rt = COPY["rules.transit.smsRouteJa"][flight[2:]]
        rx = rx.replace(re.escape("{OriginJa}"), re.escape(rt["from"])).replace(re.escape("{DestinationJaShort}"), re.escape(rt["to"]))
        rx = rx.replace(re.escape("{TaipeiTime}"), r"(?:[01]\d|2[0-3]):[0-5]\d")
        return rx, 134
    return rx, 67

# ---- forward branch cases ----------------------------------------------------
async def case_s1(r, mode, flight, lang):
    await to_s1(r, mode, flight); await r.act("cta", "msec")
    await r.fill("mSec", "123"); await r.act("cta", "preview")
    if lang != "ordZh": await r.act(lang)
    # Join copy carries the bag tag "flight/SEC"; approved Transit copy carries no typed values.
    # (the approved Japanese SMS copy has no tag either).
    has = (f"{flight}/123",) if mode == "missJoin" and lang != "ordJa" else ()
    exact = ja_expected("s1", "join" if mode == "missJoin" else "transit") if lang == "ordJa" else None
    await r.act("cta", "external:sms" if lang == "ordJa" else "external:whatsapp", has, exact=exact)

async def case_s2(r, mode, flight, lang):
    await to_s2(r, mode, flight); await r.act("cta", "callgate")
    await r.fill("callGateZone", "C"); await r.fill("callGate", "5"); await r.act("cta", "preview")
    if lang != "ordZh": await r.act(lang)
    has = ["CX" + flight, "C5"]
    exact = ja_expected("s2", "join" if mode == "callJoin" else "transit", "CX" + flight, "C5") if lang == "ordJa" else None
    await r.act("cta", "external:sms" if lang == "ordJa" else "external:whatsapp", tuple(has), exact=exact)

async def case_direct(r):
    # Call Directly is its own entry on the Scenario page.
    await r.phone(); await r.act("goDirect", "preview")
    ck(f"[{r.name}] call-only preview hides message preview", not await r.pg.locator("#msgToggle").is_visible())
    await r.act("cta", "external:whatsapp-call")

async def case_s3(r, lang):
    await r.phone(); await r.act("goWpp", "wflight"); await r.fill("wFlight", "123"); await r.act("cta", "bag1")
    await r.fill("b1n", "123456"); await r.act("cta", "bag2")
    await r.fill("b2a", "BR"); await r.fill("b2n", "654321"); await r.act("cta", "preview")
    await r.act("ordEn"); await r.act("msgToggle"); await r.act("msgToggle")
    if lang == "ordZh": await r.act("ordZh")
    await r.act("cta", "external:whatsapp", ("CX123", "CX123456", "BR654321"))

async def case_s4(r, status, arrange, lang):
    await to_s4(r, status); await r.act("cta", "dtransfer")
    await r.fill("tN", "888"); await r.act("cta", "darrange")
    has = ["CX407", "CX888"]
    if arrange == "arKnown":
        await r.act("arUnknown"); await r.act("arKnown")
        await r.fill("altN", "401"); await r.fill("altTime", "1530"); has += ["CX401", "15:30"]
    else:
        await r.act("arKnown"); await r.act("arUnknown")
    await r.act("cta", "darrive"); await r.fill("arriveTime", "1400"); await r.act("cta", "preview")
    await r.act("ordZh" if lang == "ordZh" else "ordEn")
    if status == "stDelayed": has.append("18:00")
    await r.act("cta", "external:whatsapp", tuple(has))

S4_BRANCHES = {k[3:]: v for k, v in COPY.items() if k.startswith("s4.")}

S4_DEST = {"450": ("東京成田", "Tokyo Narita"), "564": ("大阪關西", "Osaka Kansai"), "530": ("名古屋中部", "Nagoya Chubu")}

async def case_s4_gate(r, status, target, go, lang, new="531"):
    await r.phone(); await r.act("goDp", "dstatus"); await r.act("stGate", "dflight"); await r.fill("dFlight", "451")
    other = "gsCancelled" if status == "gsDelayed" else "gsDelayed"
    await r.act(other); await r.act(status)
    st = "delayed" if status == "gsDelayed" else "cancelled"
    if st == "delayed":
        await r.fill("delayTime", "2100")
    await r.act("cta", "dnew")
    other_t = "gOriginalFlight" if target == "gProtectedFlight" else "gProtectedFlight"
    other_go = "gpWait" if go == "gpAsap" else "gpAsap"
    await fill_protect(r, new, "B", "9", "1955")
    await r.act("cta", "dgateaction")
    await r.act(other_t); await r.act(other_go); await r.act(target); await r.act(go)
    ck(f"[{r.name}] gate target buttons show both flights", [await r.pg.locator(f"#{b}").inner_text() for b in ("gOriginalFlight", "gProtectedFlight")] == ["CX451", "CX" + new])
    await r.act("cta", "preview"); await r.act(lang)
    g = "asap" if go == "gpAsap" else "wait"; tg = "original" if target == "gOriginalFlight" else "new"
    dz, de = S4_DEST.get(new, ("香港", "Hong Kong"))
    fill = lambda t: (t.replace("{Disrupted Flight}", "CX451").replace("{Delay Time}", "21:00").replace("{New Flight}", "CX" + new)
                      .replace("{Gate}", "B9").replace("{Dep Time}", "19:55").replace("{DestinationZh}", dz).replace("{DestinationEn}", de))
    zh, en = fill(S4_BRANCHES[f"zh.gate.{st}.{tg}.{g}"]), fill(S4_BRANCHES[f"en.gate.{st}.{tg}.{g}"])
    want = zh + "\n\n" + en if lang == "ordZh" else en + "\n\n" + zh
    got = await r.pg.locator("#msg").input_value()
    ck(f"[{r.name}] message is exactly the approved Already-at-Gate copy", got == want, got[:200])
    rows = await r.pg.evaluate("[...document.querySelectorAll('#sum div')].map(d => d.querySelector('dt').textContent + '=' + d.querySelector('dd').textContent)")
    want_rows = ["Disrupted flight=CX451", "Protect to=CX" + new + " / dep 19:55",
                 "Proceed to Gate=" + ("CX451" if tg == "original" else "CX" + new + " / B9")]
    ck(f"[{r.name}] confirm details rows", rows == want_rows, str(rows))
    who = await r.pg.locator("#whoNum").inner_text()
    ck(f"[{r.name}] Confirm details shows the grouped number top-right", await r.pg.locator("#who").is_visible() and " " in who and who.replace(" ", "") == "+" + PHONE, who)
    await r.act("cta", "external:whatsapp", ("CX451", "CX" + new, "19:55") + (("21:00",) if st == "delayed" else ()) + (("B9",) if tg == "new" else ()))

async def case_b1r(r, gate_path):
    iid, bid, zid = ("gGate", "gGateR", "gGateZone") if gate_path else ("callGate", "callGateR", "callGateZone")
    if gate_path:
        await to_s4_gate(r, "407", "gsCancelled")
        await fill_protect(r, "401", "B", "", "1945")
    else:
        await to_s2(r, "callJoin", "407"); await r.act("cta", "callgate")
    pg=r.pg
    ck(f"[{bid}] numeric keyboard", await pg.locator('#'+iid).get_attribute('inputmode') == 'numeric')
    await r.fill(iid, "")
    y=(await pg.locator('#cta').bounding_box())['y']
    for value in ("", "2", "3", "4", "5", "6", "7", "8", "9"):
        await r.fill(iid,value)
        ck(f"[{bid}] hidden for {value or 'empty'}", not await pg.locator('#'+bid).is_visible())
    await r.fill(iid,"1")
    ck(f"[{bid}] B1R suggestion", await pg.locator('#'+bid).is_visible() and await pg.locator('#'+bid).inner_text() == 'B1R?')
    ck(f"[{bid}] reveal does not move Next", abs((await pg.locator('#cta').bounding_box())['y']-y)<1)
    await r.act(bid)
    ck(f"[{bid}] selected", await r.val(iid)=='1R' and await pg.locator('#'+bid).get_attribute('aria-pressed')=='true' and await pg.locator('#'+bid).inner_text()=='B1R')
    ck(f"[{bid}] focus retained", await pg.evaluate('document.activeElement.id')==iid)
    await r.act(bid)
    ck(f"[{bid}] toggles back to 1", await r.val(iid)=='1' and await pg.locator('#'+bid).get_attribute('aria-pressed')=='false')
    await r.act(bid); await r.fill(zid,'C')
    ck(f"[{bid}] switching to C yields C1", await r.val(iid)=='1' and not await pg.locator('#'+bid).is_visible())
    await r.fill(iid,'1R')
    ck(f"[{bid}] pasted C1R cannot remain", await r.val(iid)=='1')
    await r.fill(iid,'')
    ck(f"[{bid}] hide does not move Next", abs((await pg.locator('#cta').bounding_box())['y']-y)<1)
    await r.fill(zid,'B'); await r.fill(iid,'1'); await r.act(bid)
    if gate_path:
        await pg.set_viewport_size({'width':320,'height':844})
        await pg.wait_for_timeout(300)
        fits=await pg.locator('#gGate').evaluate('''e=>{const c=getComputedStyle(e),cv=document.createElement('canvas').getContext('2d');cv.font=c.font;return e.value==='1R'&&cv.measureText(e.value).width<=e.clientWidth-parseFloat(c.paddingLeft)-parseFloat(c.paddingRight);}''')
        ck('[gGateR] 320px input fits 1R',fits)
        await r.act('cta','dgateaction'); await r.act('gProtectedFlight'); await r.act('gpAsap')
    await r.act('cta','preview')
    ck(f'[{bid}] message includes B1R', 'B1R' in await pg.locator('#msg').input_value())

CASES = [("Final Call B1R", lambda r: case_b1r(r,False)), ("Protect to B1R", lambda r: case_b1r(r,True))]
for m, f in (("missJoin", "407"), ("missTransit", "450")):
    for l in ("ordZh", "ordEn", "ordJa"):
        CASES.append((f"S1 {m} {l}", lambda r, m=m, f=f, l=l: case_s1(r, m, f, l)))
for m, f in (("callJoin", "407"), ("callTransit", "451")):
    for l in ("ordZh", "ordEn", "ordJa"):
        CASES.append((f"S2 {m} {l}", lambda r, m=m, f=f, l=l: case_s2(r, m, f, l)))
CASES.append(("Call Directly", lambda r: case_direct(r)))
for l in ("ordZh", "ordEn"):
    CASES.append((f"S3 {l}", lambda r, l=l: case_s3(r, l)))
for i, s in enumerate(("stPossible", "stDelayed", "stUnknown")):
    for j, a in enumerate(("arKnown", "arUnknown")):
        l = ("ordEn", "ordZh")[(i + j) % 2]
        CASES.append((f"S4 {s} {a} {l}", lambda r, s=s, a=a, l=l: case_s4(r, s, a, l)))

for s_, t_, g_, l_, n_ in (("gsDelayed", "gProtectedFlight", "gpAsap", "ordZh", "531"), ("gsDelayed", "gOriginalFlight", "gpWait", "ordEn", "403"),
                            ("gsCancelled", "gOriginalFlight", "gpAsap", "ordEn", "565"), ("gsCancelled", "gProtectedFlight", "gpWait", "ordZh", "479")):
    CASES.append((f"S4 Already at Gate {s_} {t_} {g_} {l_} CX{n_}", lambda r, s_=s_, t_=t_, g_=g_, l_=l_, n_=n_: case_s4_gate(r, s_, t_, g_, l_, n_)))

# ---- guards -------------------------------------------------------------------
async def g(r, name):
    if name == "phone_invalid_blocks_next":
        await r.fill("phoneInput", "123"); await r.expect("short phone keeps Next disabled", cta_enabled=False)
    elif name == "phone_canned_number_blocked":
        await r.fill("phoneInput", "85289648964")
        await r.expect("canned number blocked with red border", cta_enabled=False, bad=["phoneInput"])
    elif name == "s1_join_rejects_non_whitelist":
        await to_s1(r, "missJoin", "888"); await r.expect("S1 Join CX888 rejected", False, ["mFlight"])
        await r.fill("mFlight", "407"); await r.expect("S1 Join CX407 accepted", True, not_bad=["mFlight"])
    elif name == "s1_transit_rejects_join_only_flight":
        await to_s1(r, "missTransit", "407"); await r.expect("S1 Transit CX407 rejected", False, ["mFlight"])
        await r.fill("mFlight", "450"); await r.expect("S1 Transit CX450 accepted", True, not_bad=["mFlight"])
    elif name == "s1_sec_over_580":
        await to_s1(r, "missJoin", "407"); await r.act("cta", "msec")
        await r.fill("mSec", "600"); await r.expect("SEC 600 rejected", False, ["mSec"])
        await r.fill("mSec", "580"); await r.expect("SEC 580 accepted", True, not_bad=["mSec"])
    elif name == "s2_join_rejects_non_whitelist":
        await to_s2(r, "callJoin", "888"); await r.expect("S2 Join CX888 rejected", False, ["callFlight"])
        await r.fill("callFlight", "407"); await r.expect("S2 Join CX407 accepted", True, not_bad=["callFlight"])
    elif name == "s2_transit_rejects_join_only_flight":
        await to_s2(r, "callTransit", "407"); await r.expect("S2 Transit CX407 rejected", False, ["callFlight"])
        await r.fill("callFlight", "565"); await r.expect("S2 Transit CX565 accepted", True, not_bad=["callFlight"])
    elif name == "s2_gate_requires_valid_number":
        await to_s2(r, "callJoin", "407"); await r.act("cta", "callgate")
        await r.expect("gate empty keeps Next disabled", False)
        await r.fill("callGate", "0"); await r.expect("gate 0 rejected", False)
        await r.fill("callGate", "1R"); await r.expect("gate 1R accepted", True)
    elif name == "s3_bag_requires_six_digits":
        await r.phone(); await r.act("goWpp", "wflight"); await r.fill("wFlight", "123"); await r.act("cta", "bag1")
        await r.fill("b1n", "12345"); await r.expect("bag tag 5 digits rejected", False)
        await r.fill("b1n", "123456"); await r.expect("bag tag 6 digits accepted", True)
    elif name == "s3_bag_airline_letters_only":
        await r.phone(); await r.act("goWpp", "wflight"); await r.fill("wFlight", "123"); await r.act("cta", "bag1")
        await r.fill("b1n", "123456"); await r.fill("b1a", "1X"); await r.expect("bag airline '1X' rejected", False)
    elif name == "s4_flight_from_tpe_rejects_non_whitelist":
        await to_s4(r, "stPossible", "888"); await r.expect("Flight from TPE CX888 rejected", False, ["dFlight"])
        await r.fill("dFlight", "407"); await r.expect("Flight from TPE CX407 accepted", True, not_bad=["dFlight"])
    elif name == "s4_delayed_requires_time":
        await to_s4(r, "stDelayed", delay=None)
        vis = await r.pg.locator("#delayWrap").is_visible()
        ck("[guard] Delayed shows Delayed-to field", vis)
        await r.expect("Delayed without time keeps Next disabled", False)
        await r.fill("delayTime", "1800"); await r.expect("Delayed 18:00 accepted", True)
        ck("[guard] Delayed-to shows full 18:00", await r.val("delayTime") == "18:00", await r.val("delayTime"))
    elif name == "s4_delayed_time_display":
        await to_s4(r, "stDelayed", delay=None)
        info = await r.pg.locator("#delayTime").evaluate("""e => ({ph: e.placeholder, icon: getComputedStyle(e.parentElement, '::before').content,
            color: getComputedStyle(e).color, align: getComputedStyle(e).textAlign})""")
        ck("[guard] Delayed-to has no icon and no placeholder", info["ph"] == "" and info["icon"] in ("none", "normal", ""), str(info))
        await r.fill("delayTime", "1800"); await r.blur("delayTime")
        fit = await r.pg.locator("#delayTime").evaluate("e => e.scrollWidth <= e.clientWidth + 1")
        info = await r.pg.locator("#delayTime").evaluate("e => getComputedStyle(e).color")
        ck("[guard] 18:00 fully visible (not clipped to 8:00)", fit and await r.val("delayTime") == "18:00")
        want = await r.pg.evaluate("""() => { const d = document.createElement('i'); d.style.color = 'var(--delay-ink)';
            document.body.appendChild(d); const c = getComputedStyle(d).color; d.remove(); return c; }""")
        ck("[guard] Delayed-to time uses the delay colour (--delay-ink), not the error red", info == want and info != "rgb(198, 40, 40)", f"{info} vs {want}")
        hint = await r.pg.locator("#hint").text_content()
        ck("[guard] no HHMM hint on Delayed-to", "HHMM" not in (hint or ""), hint)
    elif name == "s4_protect_fields_side_by_side":
        # CX flight and DEP time sit side by side inside the card, and typed values
        # are never clipped, down to a 320px-wide phone.
        for W in (390, 360, 320):
            await r.pg.set_viewport_size({"width": W, "height": 844})
            if W == 390:
                await to_s4(r, "stDelayed"); await r.act("cta", "dtransfer"); await r.fill("tN", "888"); await r.act("cta", "darrange")
                await r.act("arKnown"); await r.fill("altN", "401"); await r.fill("altTime", "1530"); await r.blur("altTime")
            await r.pg.wait_for_timeout(300)
            a = await r.pg.locator("#altN").evaluate("e => e.closest('.field').getBoundingClientRect().toJSON()")
            t = await r.pg.locator("#altTime").evaluate("e => e.closest('.field').getBoundingClientRect().toJSON()")
            clip = await r.pg.evaluate("[...document.querySelectorAll('#altWrap input')].filter(e => e.scrollWidth > e.clientWidth + 1).map(e => e.id)")
            ck(f"[guard] {W}px: CX flight and DEP time side by side", abs(a["top"] - t["top"]) < 1 and t["left"] > a["right"], f"{a} {t}")
            ck(f"[guard] {W}px: CX401 / 15:30 not clipped", not clip, str(clip))
    elif name == "s2_transit_ja_all_flights":
        # Every transit flight gets the right origin/destination and stays within 2 SMS,
        # using the longest supported gate form (B1R).
        first = True
        for f in ("450", "451", "530", "531", "564", "565"):
            rr = r if first else await Run(r.browser, f"{name} CX{f}").open()
            await to_s2(rr, "callTransit", f); await rr.act("cta", "callgate")
            await rr.fill("callGateZone", "B"); await rr.fill("callGate", "1R"); await rr.act("cta", "preview")
            await rr.act("ordJa"); await rr.act("cta", "external:sms", exact=ja_expected("s2", "transit", "CX" + f, "B1R"))
            if not first: await rr.close()
            first = False
        # Join, longest gate form: still one SMS (<=67)
        rr = await Run(r.browser, f"{name} Join B1R").open()
        await to_s2(rr, "callJoin", "407"); await rr.act("cta", "callgate")
        await rr.fill("callGateZone", "B"); await rr.fill("callGate", "1R"); await rr.act("cta", "preview")
        await rr.act("ordJa"); await rr.act("cta", "external:sms", exact=ja_expected("s2", "join", "CX407", "B1R")); await rr.close()
    elif name == "layout_does_not_jump":
        # Keyboard open/close must not move or resize the title and fields, and the header
        # must keep the same height on every page. Keyboard mode is forced via the
        # same .kb class the app applies when the on-screen keyboard is up.
        M = """() => { const s = document.querySelector('.screen:not([hidden])'); const h = s.querySelector('h1');
          const f = s.querySelector('.field'); const r = e => e ? Math.round(e.getBoundingClientRect().top) : null;
          return [s.id, r(h), h ? getComputedStyle(h).fontSize : '', r(f), f ? Math.round(f.getBoundingClientRect().height) : null,
                  Math.round(document.querySelector('.head').getBoundingClientRect().height)]; }"""
        K = "on => { const a = document.getElementById('app'); a.classList.toggle('kb', on); a.style.setProperty('--vh', on ? '470px' : '100%'); }"
        heads, jumps = set(), []
        async def probe():
            n = await r.pg.evaluate(M); await r.pg.evaluate(K, True); k = await r.pg.evaluate(M); await r.pg.evaluate(K, False)
            heads.add(n[5]); heads.add(k[5])
            if n[1:5] != k[1:5]: jumps.append(f"{n[0]}: {n[1:5]} -> {k[1:5]}")
        await probe(); await r.phone(); await r.act("goDp", "dstatus"); await r.act("stDelayed", "dflight"); await probe()
        await r.fill("dFlight", "407"); await r.fill("delayTime", "1800"); await r.act("cta", "dtransfer"); await probe()
        await r.fill("tN", "888"); await r.act("cta", "darrange"); await r.act("arKnown"); await r.pg.wait_for_timeout(350); await probe()
        await r.fill("altN", "401"); await r.fill("altTime", "1530"); await r.act("cta", "darrive"); await probe()
        ck("[guard] title and fields do not move or resize when the keyboard opens", not jumps, "; ".join(jumps))
        ck("[guard] header height identical on every page", max(heads) - min(heads) <= 1, str(sorted(heads)))
    elif name == "s4_delayed_rejects_invalid_time":
        await to_s4(r, "stDelayed", delay="2575"); await r.expect("Delayed 25:75 rejected", False, ["delayTime"])
    elif name == "s4_non_delayed_hides_time":
        for st in ("stPossible", "stUnknown"):
            rr = await Run(r.browser, name + " " + st).open()
            await to_s4(rr, st)
            ck(f"[guard] {st} hides Delayed-to field", not await rr.pg.locator("#delayWrap").is_visible())
            await rr.expect(f"{st} needs no time", True); await rr.close()
    elif name == "s4_connecting_rejects_tpe_departure":
        await to_s4(r, "stPossible"); await r.act("cta", "dtransfer")
        await r.fill("tN", "401"); await r.expect("connecting CX401 (TPE departure) rejected", False, ["tN"])
        await r.fill("tN", "888"); await r.expect("connecting CX888 accepted", True, not_bad=["tN"])
    elif name == "s4_connecting_allows_non_cx":
        await to_s4(r, "stPossible"); await r.act("cta", "dtransfer")
        await r.fill("tA", "KA"); await r.fill("tN", "401"); await r.expect("connecting KA401 accepted", True, not_bad=["tN"])
    elif name == "s4_connecting_rejects_bad_airline":
        await to_s4(r, "stPossible"); await r.act("cta", "dtransfer")
        await r.fill("tN", "888"); await r.fill("tA", "K")
        await r.expect("airline 'K' neutral while still typing", False, not_bad=["tN"])
        await r.blur("tA"); await r.expect("airline 'K' red after leaving the field", False, ["tN"])
    elif name == "partial_flight_not_red_while_typing":
        await to_s4(r, "stPossible", "4"); await r.expect("CX4 (could become 407) neutral", False, not_bad=["dFlight"])
        await r.fill("dFlight", "40"); await r.expect("CX40 (could become 407) neutral", False, not_bad=["dFlight"])
        await r.blur("dFlight"); await r.expect("CX40 red after leaving the field", False, ["dFlight"])
    elif name == "impossible_prefix_red_immediately":
        await to_s4(r, "stPossible", "8"); await r.expect("CX8 (no allowed flight starts with 8) red at once", False, ["dFlight"])
        rr = await Run(r.browser, name + " S1 transit").open()
        await to_s1(rr, "missTransit", "45"); await rr.expect("S1 Transit CX45 neutral while typing", False, not_bad=["mFlight"])
        await rr.fill("mFlight", "47"); await rr.expect("S1 Transit CX47 red at once", False, ["mFlight"]); await rr.close()
    elif name == "s4_protect_panel_attached_to_option":
        await to_s4(r, "stDelayed"); await r.act("cta", "dtransfer"); await r.fill("tN", "888"); await r.act("cta", "darrange")
        await r.act("arKnown"); await r.pg.wait_for_timeout(350)
        box = {i: await r.pg.locator("#" + i).bounding_box() for i in ("arKnown", "altWrap", "arUnknown")}
        k, w, u = box["arKnown"], box["altWrap"], box["arUnknown"]
        ck("[guard] protect fields sit directly under 'Will protect to' and above 'Arrange in airport'",
           abs(w["y"] - (k["y"] + k["height"])) < 2 and u["y"] >= w["y"] + w["height"] and abs(w["x"] - k["x"]) < 1 and abs(w["width"] - k["width"]) < 1,
           str(box))
    elif name == "s4_arrange_requires_choice":
        await to_s4(r, "stPossible"); await r.act("cta", "dtransfer"); await r.fill("tN", "888"); await r.act("cta", "darrange")
        await r.expect("no arrangement chosen keeps Next disabled", False)
        await r.act("arUnknown"); await r.expect("Arrange in airport enables Next", True)
    elif name == "s4_protect_requires_valid_flight_and_time":
        await to_s4(r, "stPossible"); await r.act("cta", "dtransfer"); await r.fill("tN", "888"); await r.act("cta", "darrange")
        await r.act("arKnown"); await r.expect("Will protect to without details disabled", False)
        await r.fill("altN", "401"); await r.fill("altTime", "1530"); await r.expect("CX401 15:30 accepted", True)
        await r.fill("altTime", "2599"); await r.expect("protect time 25:99 rejected", False, ["altTime"])
    elif name == "s4_protect_cx_requires_tpe_whitelist":
        await to_s4(r, "stPossible", "407"); await r.act("cta", "dtransfer"); await r.fill("tN", "888"); await r.act("cta", "darrange")
        await r.act("arKnown"); await r.fill("altN", "888"); await r.fill("altTime", "1530")
        await r.expect("protect CX888 (not TPE whitelist) rejected", False, ["altN"])
        ck("[guard] CX non-whitelist protect hint is red", (await r.pg.locator("#hint").inner_text()) == "CX flight must depart TPE" and await r.pg.locator("#hint").evaluate("e=>e.classList.contains('bad')"))
    elif name == "s4_protect_rejects_same_tpe_flight":
        await to_s4(r, "stPossible", "407"); await r.act("cta", "dtransfer"); await r.fill("tN", "888"); await r.act("cta", "darrange")
        await r.act("arKnown"); await r.fill("altN", "407"); await r.fill("altTime", "1530")
        await r.expect("protect same CX407 rejected", False, ["altN"])
        ck("[guard] same-flight protect hint is red", (await r.pg.locator("#hint").inner_text()) == "Same as Flight from TPE — not allowed" and await r.pg.locator("#hint").evaluate("e=>e.classList.contains('bad')"))
    elif name == "s4_protect_allows_non_cx":
        await to_s4(r, "stPossible", "407"); await r.act("cta", "dtransfer"); await r.fill("tN", "888"); await r.act("cta", "darrange")
        await r.act("arKnown"); await r.fill("altA", "KA"); await r.fill("altN", "888"); await r.fill("altTime", "1530")
        await r.expect("protect KA888 remains allowed", True, not_bad=["altN"])
    elif name == "s4_gate_status_required":
        await to_s4_gate(r)
        ck("[guard] Already at Gate step 2 shows Flight status", await r.pg.locator("#gStatusWrap").is_visible())
        await r.expect("Already at Gate without Flight status keeps Next disabled", False)
        ck("[guard] no status: Delayed to hidden", not await r.pg.locator("#delayWrap").is_visible())
        await r.act("gsCancelled"); await r.expect("CX407 + Cancelled enables Next", True)
        await r.back("dstatus"); await r.act("stPossible", "dflight")
        ck("[guard] Tight Connection step 2 has no Flight status", not await r.pg.locator("#gStatusWrap").is_visible())
    elif name == "s4_gate_delayed_requires_time":
        await to_s4_gate(r); await r.act("gsDelayed")
        await r.pg.wait_for_timeout(400)  # Delayed to slides open (0.23 s) in the Already at Gate branch
        ck("[guard] gate Delayed shows Delayed to", (await r.pg.locator('#delayWrap').evaluate('e => e.getBoundingClientRect().height')) > 40 and await r.pg.locator("#delayWrap").evaluate("e => e.classList.contains('gateDelayOpen')"))
        await r.expect("gate Delayed without time keeps Next disabled", False)
        await r.fill("delayTime", "2575"); await r.expect("gate Delayed 25:75 rejected", False, ["delayTime"])
        await r.fill("delayTime", "2100"); await r.expect("gate Delayed 21:00 accepted", True, not_bad=["delayTime"])
        await r.act("gsCancelled")
        await r.pg.wait_for_timeout(400)
        ck("[guard] Cancelled hides and clears Delayed to", (await r.pg.locator('#delayWrap').evaluate('e => e.getBoundingClientRect().height')) < 2 and await r.val("delayTime") == "" and not await r.pg.locator("#delayWrap").evaluate("e => e.classList.contains('gateDelayOpen')"))
    elif name == "s4_gate_protect_rules":
        await to_s4_gate(r, "407", "gsCancelled"); await fill_protect(r, "407")
        await r.expect("gate protect same CX407 rejected", False, ["gNewN"])
        ck("[guard] gate same-flight hint is red", (await r.pg.locator("#hint").inner_text()) == "Same as Flight from TPE — not allowed" and await r.pg.locator("#hint").evaluate("e=>e.classList.contains('bad')"))
        await r.fill("gNewN", "888"); await r.expect("gate protect CX888 (not TPE whitelist) rejected", False, ["gNewN"])
        ck("[guard] gate non-whitelist hint is red", (await r.pg.locator("#hint").inner_text()) == "CX flight must depart TPE" and await r.pg.locator("#hint").evaluate("e=>e.classList.contains('bad')"))
        for n in ("401", "451", "531", "565"):
            await r.fill("gNewN", n); await r.expect(f"gate protect CX{n} (TPE departure) accepted", True, not_bad=["gNewN"])
        for n in ("450", "530", "564"):
            await r.fill("gNewN", n); await r.expect(f"gate protect CX{n} (not TPE departure) rejected", False, ["gNewN"])
    elif name == "s4_gate_requires_valid_gate":
        await to_s4_gate(r, "407", "gsCancelled"); await fill_protect(r, "401", "B", "", "1945")
        await r.expect("gate empty keeps Next disabled", False)
        await r.fill("gGate", "0"); await r.expect("gate 0 rejected", False)
        await r.fill("gGateZone", "C"); await r.fill("gGate", "1R"); await r.expect("gate C1R normalizes to C1", True)
        ck("[guard] C1R is not retained", await r.val("gGate") == "1")
    elif name == "s4_gate_dep_and_proceed_required":
        await to_s4_gate(r, "407", "gsCancelled"); await fill_protect(r, "401", "B", "9", "")
        await r.expect("no Dep and no Proceed choice keeps Next disabled", False)
        await r.fill("gDepTime", "2575"); await r.expect("Dep 25:75 rejected", False, ["gDepTime"])
        await r.fill("gDepTime", "1955"); await r.expect("Protect to complete enables Next (Proceed to Gate is step 4/5)", True, not_bad=["gDepTime"])
        await r.act("cta", "dgateaction"); await r.expect("no Proceed choice keeps Next disabled", False)
        await r.act("gpWait"); await r.expect("Wait for Staff without a gate target keeps Next disabled", False)
        await r.act("gOriginalFlight"); await r.expect("original-flight target + Wait for Staff enables Next", True)
    elif name == "s4_gate_fields_side_by_side":
        for W in (390, 360, 320):
            await r.pg.set_viewport_size({"width": W, "height": 844})
            if W == 390:
                await to_s4_gate(r, "451", "gsDelayed", "2100"); await fill_protect(r, "531", "B", "1R", "1955")
            await r.pg.wait_for_timeout(300)
            a = await r.pg.locator("#gNewN").evaluate("e => e.closest('.field').getBoundingClientRect().toJSON()")
            t = await r.pg.locator("#gGate").evaluate("e => e.closest('.field').getBoundingClientRect().toJSON()")
            dp = await r.pg.locator("#gDepTime").evaluate("e => e.closest('.field').getBoundingClientRect().toJSON()")
            clip = await r.pg.evaluate("[...document.querySelectorAll('#s-dnew input, #s-dnew .opt')].filter(e => e.offsetParent && e.scrollWidth > e.clientWidth + 1).map(e => e.id)")
            ck(f"[guard] {W}px: CX flight and gate side by side, Dep below", abs(a["top"] - t["top"]) < 1 and t["left"] > a["right"] and dp["top"] >= a["bottom"], f"{a} {t} {dp}")
            ck(f"[guard] {W}px: Protect to fields not clipped", not clip, str(clip))
    elif name == "s4_arrive_rejects_invalid_time":
        await to_s4(r, "stPossible"); await r.act("cta", "dtransfer"); await r.fill("tN", "888"); await r.act("cta", "darrange")
        await r.act("arUnknown"); await r.act("cta", "darrive")
        await r.fill("arriveTime", "2400"); await r.expect("arrive 24:00 rejected", False, ["arriveTime"])
        await r.fill("arriveTime", "1400"); await r.expect("arrive 14:00 accepted", True)
    else:
        return False
    return True

async def rule(r, name):
    if name == "s1_mode_switch_clears_inputs":
        await to_s1(r, "missJoin", "407"); await r.back("misstype"); await r.act("missTransit", "mflight")
        ck("[rule] S1 Join -> Transit clears flight", await r.val("mFlight") == "")
    elif name == "s1_same_mode_keeps_inputs":
        await to_s1(r, "missJoin", "407"); await r.back("misstype"); await r.act("missJoin", "mflight")
        ck("[rule] S1 re-selecting Join keeps flight", await r.val("mFlight") == "407")
    elif name == "s2_mode_switch_clears_inputs":
        await to_s2(r, "callJoin", "407"); await r.back("calltype"); await r.act("callTransit", "callflight")
        ck("[rule] S2 Join -> Transit clears flight", await r.val("callFlight") == "")
    elif name == "s4_flight_type_switch_clears_delay_time":
        await to_s4(r, "stDelayed"); await r.back("dstatus"); await r.act("stPossible", "dflight")
        await r.back("dstatus"); await r.act("stDelayed", "dflight")
        ck("[rule] S4 Delayed -> Tight -> Delayed clears delay time", await r.val("delayTime") == "")
    elif name == "s4_same_flight_type_keeps_delay_time":
        await to_s4(r, "stDelayed"); await r.back("dstatus"); await r.act("stDelayed", "dflight")
        ck("[rule] S4 re-selecting Delayed keeps 18:00", await r.val("delayTime") == "18:00", await r.val("delayTime"))
    elif name == "s4_leaving_gate_branch_clears_fields":
        await to_s4_gate(r, "407", "gsDelayed"); await fill_protect(r, "401"); await r.act("cta", "dgateaction"); await r.act("gProtectedFlight"); await r.act("gpAsap")
        await r.back("dnew"); await r.back("dflight"); await r.back("dstatus"); await r.act("stPossible", "dflight")
        await r.back("dstatus"); await r.act("stGate", "dflight")
        s_ = await r.st()
        ck("[rule] Already at Gate -> Tight -> Already at Gate clears Flight status", not s_["pressed"] and await r.val("delayTime") == "", str(s_["pressed"]))
        await r.act("gsCancelled"); await r.act("cta", "dnew"); s_ = await r.st()
        ck("[rule] ... and clears Protect to", [await r.val(x) for x in ("gNewN", "gGate", "gDepTime")] == ["", "", ""] and not s_["pressed"], str(s_["pressed"]))
    elif name == "s4_same_gate_branch_keeps_fields":
        await to_s4_gate(r, "407", "gsDelayed"); await fill_protect(r, "401"); await r.act("cta", "dgateaction"); await r.act("gProtectedFlight"); await r.act("gpWait")
        await r.back("dnew"); await r.back("dflight"); await r.back("dstatus"); await r.act("stGate", "dflight")
        s_ = await r.st()
        ck("[rule] re-selecting Already at Gate keeps Flight status", s_["pressed"] == ["gsDelayed"] and await r.val("delayTime") == "18:30", str(s_["pressed"]))
        await r.act("cta", "dnew"); s_ = await r.st()
        ck("[rule] ... and keeps Protect to", [await r.val(x) for x in ("gNewN", "gGate", "gDepTime")] == ["401", "5", "19:45"], str(s_["pressed"]))
        await r.act("cta", "dgateaction"); s_ = await r.st()
        ck("[rule] ... and keeps Proceed to Gate selection", s_["pressed"] == ["gProtectedFlight", "gpWait"], str(s_["pressed"]))
    elif name == "enter_key_advances":
        await to_s1(r, "missJoin", "407"); await r.pg.press("#mFlight", "Enter")
        s = await r.wait(lambda s: s["screen"] == "msec")
        ck("[rule] Enter on a valid field goes to the next step", s["screen"] == "msec")
    elif name == "back_preserves_inputs":
        await r.phone(); await r.act("goWpp", "wflight"); await r.fill("wFlight", "123"); await r.act("cta", "bag1")
        await r.back("wflight"); ck("[rule] Back keeps typed flight", await r.val("wFlight") == "123")
    elif name == "scenario_reentry_starts_clean":
        await r.phone(); await r.act("goWpp", "wflight"); await r.fill("wFlight", "123")
        await r.back("scenario"); await r.act("goWpp", "wflight")
        ck("[rule] Re-entering a scenario starts clean", await r.val("wFlight") == "")
    else:
        return False
    return True

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
        for name, fn in CASES:
            r = await Run(browser, name).open(); await fn(r); await r.close()
        for name in SPEC["guards"]:
            r = await Run(browser, name).open()
            ck(f"guard implemented: {name}", await g(r, name)); await r.close()
        for name in SPEC["state_rules"]:
            r = await Run(browser, name).open()
            ck(f"state rule implemented: {name}", await rule(r, name)); await r.close()
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

# ---------------------------------------------------------------------------
# Service Worker scenarios  (python3 verify_behavior.py --sw [--previous DIR])
# ---------------------------------------------------------------------------
# Served over http://localhost by a GitHub-Pages-like server (ETag + max-age=600).
# Each scenario runs twice: with Chrome's Static Routing (Android path) and with
# InstallEvent.addRoutes hidden in the served sw.js (iOS Safari / older Chrome path).
# "--previous DIR" adds an upgrade test from an older unpacked build in DIR.
import hashlib, http.server, io, os, shutil, tempfile, threading

class _SwServer:
    PRE = b'try{delete InstallEvent.prototype.addRoutes;}catch(e){}\n'
    def __init__(self, port, root, noroutes):
        self.port, self.root, self.noroutes = port, root, noroutes
        self.hits, self.fail404, self.httpd = [], set(), None
    def start(self):
        srv = self
        class H(http.server.SimpleHTTPRequestHandler):
            def __init__(h, *a, **k): super().__init__(*a, directory=srv.root, **k)
            def log_message(h, *a): pass
            def send_head(h):
                p = h.path.split("?")[0]
                srv.hits.append(p)
                if p in srv.fail404:
                    h.send_response(404); h.send_header("Content-Length", "0"); h.end_headers(); return io.BytesIO(b"")
                path = h.translate_path(h.path)
                if os.path.isdir(path): path = os.path.join(path, "index.html")
                if not os.path.isfile(path): return super().send_head()
                data = open(path, "rb").read()
                if srv.noroutes and p.endswith("/sw.js"): data = _SwServer.PRE + data
                tag = '"%s"' % hashlib.md5(data).hexdigest()
                if h.headers.get("If-None-Match") == tag:
                    h.send_response(304); h.send_header("ETag", tag); h.send_header("Cache-Control", "max-age=600"); h.end_headers(); return None
                h.send_response(200); h.send_header("Content-Type", h.guess_type(path)); h.send_header("Content-Length", str(len(data)))
                h.send_header("ETag", tag); h.send_header("Cache-Control", "max-age=600"); h.end_headers()
                return io.BytesIO(data)
        http.server.ThreadingHTTPServer.allow_reuse_address = True
        self.httpd = http.server.ThreadingHTTPServer(("127.0.0.1", self.port), H)
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()
    def stop(self):
        if self.httpd:
            self.httpd.shutdown(); self.httpd.server_close(); self.httpd = None
    @property
    def url(self): return f"http://localhost:{self.port}/"

def _copy_build(src, dst):
    shutil.rmtree(dst, ignore_errors=True)
    shutil.copytree(src, dst, ignore=shutil.ignore_patterns(".git", ".github", "__pycache__"))

async def _sw_launch(ctx, srv, settle=3000):
    n = len(srv.hits); pg = await ctx.new_page(); errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    try: await pg.goto(srv.url)
    except Exception as e: errs.append("goto: " + str(e)[:80])
    await pg.wait_for_timeout(500)
    early = len(srv.hits) - n if srv.httpd else 0
    await pg.wait_for_timeout(settle)
    return pg, early, errs

async def _sw_flow(pg):
    await pg.fill("#phoneInput", PHONE); await pg.wait_for_timeout(150)
    for sel in ("#cta", "#goMiss", "#missJoin"):
        await pg.click(sel); await pg.wait_for_timeout(200)
    await pg.fill("#mFlight", "451"); await pg.wait_for_timeout(150); await pg.click("#cta"); await pg.wait_for_timeout(200)
    await pg.fill("#mSec", "123"); await pg.wait_for_timeout(150); await pg.click("#cta"); await pg.wait_for_timeout(300)
    return await pg.eval_on_selector("#msg", "e=>e.value")

_CACHE_JS = """async()=>{const o={};for(const k of await caches.keys()){const c=await caches.open(k);o[k]=(await c.keys()).length;}return o}"""
async def _cached_text(pg, path):
    return await pg.evaluate("async p=>{const r=await caches.match(new URL(p,location).href);return r?await r.text():null}", path)
async def _has(pg, marker):
    return await pg.evaluate("m=>new XMLSerializer().serializeToString(document).includes(m)", marker)
async def _expire_http_cache(ctx):
    pg = await ctx.new_page(); cdp = await ctx.new_cdp_session(pg)
    await cdp.send("Network.enable"); await cdp.send("Network.clearBrowserCache"); await pg.close()
async def _until(ctx, srv, marker, maxn=4, expire=False):
    if expire: await _expire_http_cache(ctx)
    for i in range(1, maxn + 1):
        pg, _, _ = await _sw_launch(ctx, srv); ok = await _has(pg, marker); await pg.close()
        if ok: return i
    return None

async def _sw_mode(p, tag, noroutes, port, previous, tmp):
    T = f"[SW {tag}] "
    exp = " after HTTP cache expiry" if noroutes else ""
    root = os.path.join(tmp, tag.replace(" ", "_")); _copy_build(R, root)
    srv = _SwServer(port, root, noroutes); srv.start()
    b = await launch_chromium(p)
    ctx = await b.new_context(viewport={"width": 390, "height": 800}, is_mobile=True, has_touch=True)
    # 1 first visit
    pg = await ctx.new_page(); errs = []; pg.on("pageerror", lambda e: errs.append(str(e)))
    await pg.goto(srv.url, wait_until="domcontentloaded")
    ck(T + "1 first visit: SW not registered during first paint", not await pg.evaluate("navigator.serviceWorker.getRegistration().then(r=>!!r)"))
    await pg.wait_for_timeout(4000)
    ck(T + "1 first visit: SW registered and active in the phone-input idle window", await pg.evaluate("navigator.serviceWorker.getRegistration().then(r=>!!(r&&r.active))"))
    cs = await pg.evaluate(_CACHE_JS)
    ck(T + f"1 first visit: one cache with all {N_ASSETS} assets", len(cs) == 1 and list(cs.values()) == [N_ASSETS], str(cs))
    ck(T + "1 first visit: no JavaScript errors", not errs, "; ".join(errs[:3])); await pg.close()
    # 2 controlled launch
    if noroutes: await _expire_http_cache(ctx)
    n0 = len(srv.hits)
    pg, early, errs = await _sw_launch(ctx, srv)
    ck(T + "2 launch: page controlled by the SW", await pg.evaluate("!!navigator.serviceWorker.controller"))
    # Slow company network: no network request during launch in either mode;
    # every cached file is revalidated afterwards, in parallel, inside the phone-input window.
    ck(T + "2 launch: zero network requests during launch", early == 0, f"{early} requests")
    assets = {"/" + a[2:] for a in re.findall(r'"(\./[^"]*)"', open(os.path.join(root, "sw.js"), encoding="utf-8").read().split("const ASSETS=[")[1].split("];")[0])}
    seen = set(srv.hits[n0:])
    ck(T + "2 launch: every cached file revalidated in the phone-input window", assets <= seen, str(sorted(assets - seen)))
    msg = await _sw_flow(pg)
    ck(T + "2 launch: S1 Join flow reaches preview with current copy", "CX451" in msg and "451/123" in msg and "\u2981 Have passed immigration" in msg, msg[:80])
    ck(T + "2 launch: no JavaScript errors", not errs, "; ".join(errs[:3])); await pg.close()
    # 3 offline
    srv.stop()
    pg, _, errs = await _sw_launch(ctx, srv)
    ck(T + "3 offline: app opens with the phone library loaded", await pg.evaluate("!!window.libphonenumber"))
    ck(T + "3 offline: every image renders", await pg.evaluate("[...document.images].every(i=>i.complete&&i.naturalWidth>0)"))
    msg = await _sw_flow(pg)
    ck(T + "3 offline: full flow reaches preview", "CX451" in msg and "451/123" in msg)
    ck(T + "3 offline: failed background refresh raises no JavaScript errors", not errs, "; ".join(errs[:3]))
    ck(T + "3 offline: cache intact", sum((await pg.evaluate(_CACHE_JS)).values()) == N_ASSETS); await pg.close()
    srv.start()
    # 4 update: index.html only
    open(os.path.join(root, "index.html"), "a").write("\n<!-- UPD-A -->\n")
    n = await _until(ctx, srv, "UPD-A", expire=noroutes)
    ck(T + "4 update (index.html only): new version on 2nd launch" + exp, n is not None and n <= 2, f"launch {n}")
    pg, _, _ = await _sw_launch(ctx, srv, settle=300)
    idx = await _cached_text(pg, "./index.html"); root_ = await _cached_text(pg, "./")
    if noroutes: ck(T + "4 update: ./index.html cache entry refreshed", idx and "UPD-A" in idx)
    else: ck(T + "4 update: ./ and ./index.html cache entries both refreshed", idx and root_ and "UPD-A" in idx and "UPD-A" in root_)
    await pg.close()
    # 5 update: sw.js + index.html
    open(os.path.join(root, "sw.js"), "a").write('\nself.addEventListener("message",e=>{if(e.data==="ver")e.source.postMessage("UPD-B");});\n')
    open(os.path.join(root, "index.html"), "a").write("\n<!-- UPD-B -->\n")
    n = await _until(ctx, srv, "UPD-B", expire=noroutes)
    ck(T + "5 update (sw.js + index.html): new version by 3rd launch" + exp, n is not None and n <= 3, f"launch {n}")
    pg, early, _ = await _sw_launch(ctx, srv)
    ver = await pg.evaluate("""()=>new Promise(res=>{const c=navigator.serviceWorker.controller;if(!c)return res(null);
      navigator.serviceWorker.addEventListener("message",e=>res(e.data),{once:true});c.postMessage("ver");setTimeout(()=>res("timeout"),2000)})""")
    ck(T + "5 update: new SW controls the page", ver == "UPD-B", str(ver))
    ck(T + "5 update: old caches removed", len(await pg.evaluate(_CACHE_JS)) == 1)
    if not noroutes: ck(T + "5 update: launch still makes zero network requests", early == 0, f"{early}")
    await pg.close()
    # 6 broken deploy
    srv.fail404 = {"/scenario-icon-4.png"}
    open(os.path.join(root, "index.html"), "a").write("\n<!-- UPD-C -->\n")
    await _until(ctx, srv, "UPD-C", expire=noroutes)
    pg, _, _ = await _sw_launch(ctx, srv)
    st = await pg.evaluate("async()=>{const r=await caches.match(new URL('./scenario-icon-4.png',location).href);return r?r.status:null}")
    ck(T + "6 deploy with a 404 file: cached good copy is kept", st == 200, str(st)); await pg.close()
    srv.fail404 = set()
    # 7 cache miss
    pg, _, _ = await _sw_launch(ctx, srv, settle=300)
    await pg.evaluate("async()=>{for(const k of await caches.keys()){const c=await caches.open(k);await c.delete(new URL('./libphonenumber-max.js',location).href);}}")
    await pg.close()
    pg, _, errs = await _sw_launch(ctx, srv)
    ck(T + "7 cache miss: asset fetched from network, app works", await pg.evaluate("!!window.libphonenumber") and not errs, "; ".join(errs[:3]))
    await pg.wait_for_timeout(1500)
    ck(T + "7 cache miss: asset written back to cache", (await _cached_text(pg, "./libphonenumber-max.js")) is not None)
    await pg.close(); await ctx.close()
    # 8 upgrade from a previous build
    if previous:
        up = os.path.join(tmp, tag.replace(" ", "_") + "_up"); _copy_build(previous, up); srv.stop(); srv.root = up; srv.start()
        ctx = await b.new_context(viewport={"width": 390, "height": 800}, is_mobile=True, has_touch=True)
        for _ in range(2):
            pg, _, _ = await _sw_launch(ctx, srv, settle=2500); await pg.close()
        for f in os.listdir(R):
            if (R / f).is_file(): shutil.copy(R / f, os.path.join(up, f))
        n = await _until(ctx, srv, "phone-input idle window", expire=noroutes)
        ck(T + "8 upgrade from previous build: new version by 3rd launch" + exp, n is not None and n <= 3, f"launch {n}")
        pg, early, errs = await _sw_launch(ctx, srv)
        if not noroutes: ck(T + "8 upgrade: launch makes zero network requests", early == 0, f"{early}")
        msg = await _sw_flow(pg)
        ck(T + "8 upgrade: current copy in effect", "\u2981 Have passed immigration: Please go to the CX451 gate" in msg)
        ck(T + "8 upgrade: no JavaScript errors", not errs, "; ".join(errs[:3])); await pg.close()
        srv.stop()
        pg, _, _ = await _sw_launch(ctx, srv, settle=2500)
        ck(T + "8 upgrade: offline flow works", "\u2981 Have passed immigration" in await _sw_flow(pg)); await pg.close()
    srv.stop(); await b.close()

async def sw_suite(previous):
    from playwright.async_api import async_playwright
    with tempfile.TemporaryDirectory() as tmp:
        async with async_playwright() as p:
            await _sw_mode(p, "static-routing", False, 8931, previous, tmp)
            await _sw_mode(p, "no-static-routing", True, 8932, previous, tmp)
    if not previous:
        print("SKIP [SW] 8 upgrade from a previous build (run with --previous DIR to include)")

if __name__ == "__main__" and "--priority" in sys.argv:
    static_checks()
    asyncio.run(priority_suite())
    print("PASS: priority release gate" if not failed else "FAIL: priority release gate")
    sys.exit(1 if failed else 0)

if __name__ == "__main__" and "--sw" in sys.argv:
    prev = sys.argv[sys.argv.index("--previous") + 1] if "--previous" in sys.argv else None
    asyncio.run(sw_suite(prev))
    print("PASS: service worker scenarios" if not failed else "FAIL: service worker scenarios")
    sys.exit(1 if failed else 0)

if __name__ == "__main__":
    static_checks()
    asyncio.run(runtime())
    print("PASS: flow behaviour" if not failed else "FAIL: flow behaviour")
    sys.exit(1 if failed else 0)
