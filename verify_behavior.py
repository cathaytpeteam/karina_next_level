#!/usr/bin/env python3
"""Find Pax — flow behaviour regression (r21).

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

Requires:  pip install playwright  &&  python -m playwright install chromium
"""
from pathlib import Path
import asyncio, json, re, sys, urllib.parse

R = Path(__file__).resolve().parent
HTML = (R / "index.html").read_text(encoding="utf-8")
SPEC = json.loads((R / "flow-behavior-spec.json").read_text(encoding="utf-8"))
PHONE = "886983952602"

failed = False
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
    by_name = {n: steps for _, (n, steps) in flows.items()}
    bad = []
    for e in SPEC["edges"]:
        for scr, title in ((e["from"], e["from_title"]), (e["to"], e["to_title"])):
            mm = re.match(r"(.+?) - (\d+)/(\d+)", title or "")
            if not mm or "Call Directly" in title:
                continue
            name, i, n = mm.group(1), int(mm.group(2)), int(mm.group(3))
            steps = by_name.get(name)
            if not steps or len(steps) != n:
                bad.append(f"{title}: FLOWS has {steps}")
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

# ---- locked Japanese SMS copy (message-master.json) ---------------------------
MASTER = json.loads((R / "message-master.json").read_text(encoding="utf-8"))["scenarios"]
def ja_expected(scen, mode, flight=None, gate=None):
    if scen == "s1":
        t = MASTER["scenario1_missing_baggage_xray"][mode]["ja"]
        return re.escape(t), (134 if mode == "join" else 67)
    t = MASTER["scenario2_call_passenger"][mode]["ja"]
    rx = re.escape(t).replace(re.escape("{Flight}"), re.escape(flight)).replace(re.escape("{Gate}"), re.escape(gate))
    if mode == "transit":
        rt = MASTER["scenario2_call_passenger"]["transit"]["ja_route"][flight]
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

async def case_direct(r, scen, typ, btn):
    await r.phone(); await r.act(scen, typ); await r.act(btn, "preview")
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

CASES = []
for m, f in (("missJoin", "407"), ("missTransit", "450")):
    for l in ("ordZh", "ordEn", "ordJa"):
        CASES.append((f"S1 {m} {l}", lambda r, m=m, f=f, l=l: case_s1(r, m, f, l)))
for m, f in (("callJoin", "407"), ("callTransit", "451")):
    for l in ("ordZh", "ordEn", "ordJa"):
        CASES.append((f"S2 {m} {l}", lambda r, m=m, f=f, l=l: case_s2(r, m, f, l)))
CASES.append(("S1 Call Directly", lambda r: case_direct(r, "goMiss", "misstype", "missDirect")))
CASES.append(("S2 Call Directly", lambda r: case_direct(r, "goCall", "calltype", "callDirect")))
for l in ("ordZh", "ordEn"):
    CASES.append((f"S3 {l}", lambda r, l=l: case_s3(r, l)))
for i, s in enumerate(("stPossible", "stDelayed", "stUnknown")):
    for j, a in enumerate(("arKnown", "arUnknown")):
        l = ("ordEn", "ordZh")[(i + j) % 2]
        CASES.append((f"S4 {s} {a} {l}", lambda r, s=s, a=a, l=l: case_s4(r, s, a, l)))

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
        # r27 design: CX flight and DEP time sit side by side inside the card, and typed values
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
        # using the longest gate form (C1R).
        first = True
        for f in ("450", "451", "530", "531", "564", "565"):
            rr = r if first else await Run(r.browser, f"{name} CX{f}").open()
            await to_s2(rr, "callTransit", f); await rr.act("cta", "callgate")
            await rr.fill("callGateZone", "C"); await rr.fill("callGate", "1R"); await rr.act("cta", "preview")
            await rr.act("ordJa"); await rr.act("cta", "external:sms", exact=ja_expected("s2", "transit", "CX" + f, "C1R"))
            if not first: await rr.close()
            first = False
        # Join, longest gate form: still one SMS (<=67)
        rr = await Run(r.browser, f"{name} Join C1R").open()
        await to_s2(rr, "callJoin", "407"); await rr.act("cta", "callgate")
        await rr.fill("callGateZone", "C"); await rr.fill("callGate", "1R"); await rr.act("cta", "preview")
        await rr.act("ordJa"); await rr.act("cta", "external:sms", exact=ja_expected("s2", "join", "CX407", "C1R")); await rr.close()
    elif name == "layout_does_not_jump":
        # Keyboard open/close must not move or resize the title and fields, and the header
        # must keep the same height on every page (r26). Keyboard mode is forced via the
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
            browser = await p.chromium.launch()
        except Exception:
            try:
                browser = await p.chromium.launch(executable_path="/usr/bin/chromium", args=["--no-sandbox","--disable-dev-shm-usage"])
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

if __name__ == "__main__":
    static_checks()
    asyncio.run(runtime())
    print("PASS: flow behaviour" if not failed else "FAIL: flow behaviour")
    sys.exit(1 if failed else 0)
