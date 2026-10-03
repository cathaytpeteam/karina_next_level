"""Shared setup for the Find Pax browser tests: app bundle, spec, ck(), Run and navigation helpers."""
from pathlib import Path
import asyncio, contextvars, json, os, re, sys, traceback, urllib.parse

R = Path(__file__).resolve().parent
N_ASSETS = len(re.findall(r'"\./[^"]*"', re.search(r'const ASSETS=\[(.*?)\];', (R / "sw.js").read_text(encoding="utf-8"), re.S).group(1)))
HTML = (R / "index.html").read_text(encoding="utf-8")
# Browser-flow tests use set_content() because managed Chromium may block file://.
# Inline modular local assets so set_content() matches the deployed app without file:// access.
_APP_CSS = (R / "app.css").read_text(encoding="utf-8")
_COPY_JS = (R / "copy.js").read_text(encoding="utf-8")
_APP_JS = (R / "app.js").read_text(encoding="utf-8")
# Browser-flow tests must observe the exact external URL without letting headless Chromium replace
# the app document with an error page for whatsapp:/sms:/tel:. Patch only the in-memory test copy.
for _src, _dst, _n in (("window.location.href=webUrl;", "window.__findPaxTestNavigate(webUrl);", 2),
                       ("window.location.href=appUrl;", "window.__findPaxTestNavigate(appUrl);", 1),
                       ('window.location.href="sms:"+recipient+(isiOS?"&":"?")+"body="+encoded;', 'window.__findPaxTestNavigate("sms:"+recipient+(isiOS?"&":"?")+"body="+encoded);', 1),
                       ('window.location.href="tel:+"+S.phone;', 'window.__findPaxTestNavigate("tel:+"+S.phone);', 1)):
    if _APP_JS.count(_src) != _n: raise RuntimeError(f"external-navigation test anchor drift: {_src}")
    _APP_JS = _APP_JS.replace(_src, _dst)
_TEST_NAV_JS = "window.__findPaxTestNav=[];window.__findPaxTestNavigate=u=>window.__findPaxTestNav.push(u);"
HTML = HTML.replace('<link rel="stylesheet" href="./app.css">', '<style>'+_APP_CSS+'</style>')
HTML = HTML.replace('<script src="./copy.js"></script>', '<script>'+_COPY_JS+'</script>')
HTML = HTML.replace('<script src="./app.js"></script>', '<script>'+_TEST_NAV_JS+'</script><script>'+_APP_JS+'</script>')
# The inlined test page cannot satisfy the app's Content-Security-Policy (script-src 'self' forbids
# inline code), so it is removed here only. The CSP itself is verified on a real http origin in the
# safety layer's privacy check, exactly as a phone loads the app.
HTML = re.sub(r'<meta http-equiv="Content-Security-Policy"[^>]*>\n?', '', HTML)
_COPY_MATCH = re.search(r'window\.FIND_PAX_COPY\s*=\s*Object\.freeze\((\{.*\})\);', _COPY_JS, re.S)
COPY = json.loads(_COPY_MATCH.group(1)) if _COPY_MATCH else {}
SPEC = json.loads((R / "flow-behavior-spec.json").read_text(encoding="utf-8"))
PHONE = "886983952902"
PHONE_RETRY = "819012345678"

failed = False

# Check layers, in run order and ordered by what goes wrong when a check fails. Every ck() line is
# counted under the layer of the job that runs it; only a failed safety layer stops the other layers.
LAYERS = [("safety", "安全"), ("send", "送出內容"), ("clear", "資料清除"), ("input", "輸入規則"),
          ("flow", "流程"), ("open", "能開能更新"), ("look", "外觀")]
LAYER_COUNTS = {k: [0, 0] for k, _ in LAYERS}
_LAYER = contextvars.ContextVar("find_pax_layer", default="flow")

def print_layer_counts(skipped=()):
    """Machine-readable per-layer totals for verify_release.py: LAYER key passed failed|skip."""
    for k, _ in LAYERS:
        print(f"LAYER {k} skip" if k in skipped else f"LAYER {k} {LAYER_COUNTS[k][0]} {LAYER_COUNTS[k][1]}", flush=True)

async def launch_chromium(p):
    local_browser = os.environ.get('FIND_PAX_CHROMIUM')
    if local_browser:
        return await p.chromium.launch(executable_path=local_browser, headless=True,
                                       args=["--no-sandbox", "--disable-dev-shm-usage"])
    try:
        return await p.chromium.launch(headless=True)
    except Exception:
        return await p.chromium.launch(executable_path="/usr/bin/chromium", headless=True, args=["--no-sandbox","--disable-dev-shm-usage"])

# Lines of the browser job that is running; None prints at once (one job at a time).
_OUT = contextvars.ContextVar("find_pax_out", default=None)

def ck(name, ok, detail=""):
    global failed
    line = ("PASS " if ok else "FAIL ") + name + ("" if ok or not detail else "  -> " + detail)
    buf = _OUT.get()
    if buf is None:
        print(line)
    else:
        buf.append(line)
    LAYER_COUNTS[_LAYER.get()][0 if ok else 1] += 1
    if not ok:
        failed = True
    return ok

JOB_CHOICES = ("1", "2", "3")

def workers():
    """Browser jobs run at the same time: --jobs 1, 2 or 3 (default 3 with --fast, otherwise 1)."""
    v = sys.argv[sys.argv.index("--jobs") + 1] if "--jobs" in sys.argv and sys.argv.index("--jobs") + 1 < len(sys.argv) else ("3" if "--fast" in sys.argv else "1")
    if v not in JOB_CHOICES:
        print(f"ERROR: --jobs must be 1, 2 or 3 (got {v!r}). No browser test was run.")
        raise SystemExit(2)
    return int(v)

JOB_TIMES = []  # (seconds, label) of every finished job, printed by --timing

async def run_jobs(jobs):
    """Run independent browser jobs (no-argument coroutine functions) workers() at a time, started in list order.
    Each job prints its PASS/FAIL lines together when it ends, so parallel output never interleaves.
    Shared records (failed, covered, unexpected, toggles_hit) only grow, so the totals do not depend on order.
    back_verified and lang_checked make the first job to reach an edge or preview do its one Back/Forward
    or language check; with --jobs 2/3 that can be a different job from run to run.
    A job that raises is reported as one FAIL line (test file and line) and the other jobs carry on.
    A job's checks are counted under its .layer (see LAYERS)."""
    sem = asyncio.Semaphore(workers())
    async def one(job):
        async with sem:
            buf = []
            _OUT.set(buf)
            _LAYER.set(getattr(job, "layer", "flow"))
            t0 = asyncio.get_running_loop().time()
            try:
                await job()
            except Exception as e:
                tb = [f for f in traceback.extract_tb(e.__traceback__) if Path(f.filename).parent == R]
                tb = [f for f in tb if Path(f.filename).name != "vb_core.py"] or tb  # point at the test, not the helper
                where = f"{Path(tb[-1].filename).name}:{tb[-1].lineno}" if tb else "?"
                msg = (str(e).strip().splitlines() or [""])[0][:160]
                ck(f"[{getattr(job, 'label', job.__name__)}] test ran to the end", False, f"{type(e).__name__} at {where}: {msg}")
            finally:
                JOB_TIMES.append((asyncio.get_running_loop().time() - t0, getattr(job, "label", job.__name__)))
                if buf:
                    print("\n".join(buf), flush=True)
    await asyncio.gather(*(one(j) for j in jobs))

def run_job(browser, name, fn, layer="flow"):
    """A job that opens a fresh page as Run(name), calls fn(r) and closes it; its checks count under layer."""
    async def job():
        r = await Run(browser, name).open()
        try:
            await fn(r)
        except Exception:
            await r.ctx.close()
            raise
        await r.close()
    job.label, job.layer = name, layer
    return job

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

# Usage counts (one GoatCounter image per home Next, S1-S3 send / WhatsApp call tap or S1-S3 Call by
# Phone tap) are answered locally in every test, so test runs never reach the real counter; each
# request is recorded for the privacy checks.
COUNT_HOST = "https://cathaytpeteam.goatcounter.com/"
COUNT_NAMES = ["next", "S1-WhatsApp", "S2-WhatsApp", "S1-SMS-JA", "S2-SMS-JA", "S3-WhatsApp Call",
               "S1-Call by phone", "S2-Call by phone", "S3-Call by phone"]
COUNT_RX = re.compile(r"https://cathaytpeteam\.goatcounter\.com/count\?p=("
                      + "|".join(re.escape(urllib.parse.quote(n)) for n in COUNT_NAMES) + r")&e=true&rnd=\d+")

def count_names(counts):
    """Fixed names of recorded usage counts; anything else (or one carrying a referrer) shows as '?'."""
    return [urllib.parse.unquote(m.group(1)) if (m := COUNT_RX.fullmatch(c["url"])) and "referer" not in c["headers"] else "?"
            for c in counts]
COUNT_GIF = bytes.fromhex("47494638396101000100800000000000ffffff21f90401000000002c00000000010001000002024401003b")

async def answer_count(route, seen):
    seen.append({"url": route.request.url, "headers": await route.request.all_headers()})
    await route.fulfill(status=200, content_type="image/gif", body=COUNT_GIF)

# The app's reaction to a tap or a typed value ends in zero-delay timers (render after focusout) and
# animation frames (focus moves). SETTLE_JS resolves once those queued before it have run; the 300 ms
# cap only matters if the page cannot draw frames.
SETTLE_JS = """() => new Promise(done => {
  const cap = setTimeout(done, 300);
  requestAnimationFrame(() => setTimeout(() => { clearTimeout(cap); done(); }, 0));
})"""

async def settle(pg):
    """Wait until the app has finished reacting to the last tap or input (see SETTLE_JS)."""
    await pg.evaluate(SETTLE_JS)

async def until(get, ok, ms=2000):
    """Call get() until ok(value) holds or ms pass; return the last value (the check reports it)."""
    t_end = asyncio.get_running_loop().time() + ms / 1000
    while True:
        v = await get()
        if ok(v) or asyncio.get_running_loop().time() > t_end:
            return v
        await asyncio.sleep(0.02)

async def await_external(pg, nav, n0, counts, c0):
    """Capture the external URL without leaving the test document, then wait for its usage count.
    A count normally arrives with the URL; S4/S5 send none, so that wait ends after 150 ms."""
    loop = asyncio.get_running_loop()
    t_end = loop.time() + 2
    while len(nav) <= n0 and loop.time() < t_end:
        test_nav = await pg.evaluate("window.__findPaxTestNav || []")
        if len(test_nav) > len(nav): nav[:] = test_nav
        if len(nav) <= n0: await asyncio.sleep(0.01)
    t_end = loop.time() + 0.15
    while len(counts) <= c0 and loop.time() < t_end:
        await asyncio.sleep(0.01)
    n = -1
    while n != len(counts):
        n = len(counts)
        await asyncio.sleep(0.04)
    await settle(pg)

HOME_DONE_JS = "() => !!(history.state && history.state.findPax && history.state.pos === 0)"

async def home_done(pg):
    """After Home / a tap on the header number: wait until the browser history is back on the phone
    page (the app rewinds it with history.go, which finishes a moment after the screen changes)."""
    await until(lambda: pg.evaluate(HOME_DONE_JS), bool)
    await settle(pg)

class Run:
    def __init__(self, browser, name):
        self.browser, self.name, self.nav, self.counts, self.send_counts = browser, name, [], [], []

    async def open(self):
        # Reduced motion (the app's own prefers-reduced-motion rules) makes screens and panels appear at once.
        self.ctx = await self.browser.new_context(viewport={"width": 390, "height": 844}, reduced_motion="reduce")
        await self.ctx.route(COUNT_HOST + "**", lambda route: answer_count(route, self.counts))
        self.pg = await self.ctx.new_page()
        self.errors = []
        self.pg.on("pageerror", lambda e: self.errors.append(str(e)))
        cdp = await self.ctx.new_cdp_session(self.pg)
        cdp.on("Page.frameRequestedNavigation", lambda ev: self.nav.append(ev["url"]))
        await cdp.send("Page.enable")
        # Load the exact app document without relying on file://, which is blocked by some
        # managed Chromium policies. The bundled phone library is inlined only in the test page.
        lib = (R / "libphonenumber-mobile.js").read_text(encoding="utf-8")
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
        await settle(self.pg)

    async def blur(self, id_):
        await self.pg.locator("#" + id_).evaluate("e => e.blur()")
        await settle(self.pg)

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
        n0, c0 = len(self.nav), len(self.counts)
        await self.pg.click(sel)
        if before["screen"] == "preview" and trigger == "cta":
            await await_external(self.pg, self.nav, n0, self.counts, c0)
            self.send_counts = count_names(self.counts[c0:])
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

# ---- test probe (window.__findPaxProbe, app.js [test probe]) -------------------------
# Under automated tests the app answers rule questions with its own rules for given field values:
# check({step, fields, state, focus}) -> {ok, bad, hint}; message({flow, fields, state}) -> {text, rows}.
PROBE_FIELDS = ["mFlight", "mSec", "wFlight", "b1a", "b1n", "b2a", "b2n", "dFlight", "delayTime", "tA", "tN", "altA", "altN",
                "altTime", "arriveTime", "gNewN", "gDepTime", "gGateZone", "gGate", "callFlight", "callGateZone", "callGate"]
PROBE_STEPS = ("mflight", "msec", "wflight", "bag1", "bag2", "dstatus", "dflight", "dtransfer", "darrange", "darrive",
               "dnew", "dgateaction", "callflight", "callgate")

async def probe_all(pg, kind, cases):
    """Ask the probe many questions in one call (kind is "check" or "message"); answers come back in order."""
    return await pg.evaluate("([k, cs]) => cs.map(c => window.__findPaxProbe[k](c))", [kind, cases])

# ---- helpers to reach screens ----------------------------------------------
async def to_s1(r, mode, flight):
    await r.phone(); await r.act("goMiss", "misstype"); await r.act(mode, "mflight")
    await r.fill("mFlight", flight)

async def to_s2(r, mode, flight):
    await r.phone(); await r.act("goCall", "calltype"); await r.act(mode, "callflight")
    await r.fill("callFlight", flight)

async def to_s2_gate(r, mode, flight, sec="123"):
    await to_s2(r, mode, flight); await r.act("cta", "msec"); await r.fill("mSec", sec); await r.act("cta", "callgate")

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

GATE_JS = """() => {
  const probe=document.createElement('i'); document.body.appendChild(probe);
  probe.style.color='var(--brand)'; const ink=getComputedStyle(probe).color; probe.remove();
  const row=[...document.querySelectorAll('#sum > div')].find(d=>['Go to Gate','Proceed to Gate'].includes(d.querySelector('dt').textContent.trim()));
  return {row:row?row.querySelector('dt').textContent.trim():'', colour:row?getComputedStyle(row.querySelector('dd')).color:'', ink};}"""

async def fill_protect(r, n="401", zone="B", gate="5", dep="1945"):
    # Fills Protect to (3/5) only. Proceed to Gate is its own page (4/5): callers that need it
    # continue with r.act("cta", "dgateaction") and select there.
    await r.fill("gNewN", n); await r.fill("gGateZone", zone); await r.fill("gGate", gate); await r.fill("gDepTime", dep); await r.blur("gDepTime")

# ---- focused checks (vb_priority.py) -----------------------------------------------
async def _simple_click(r, id_, screen=None):
    await r.pg.locator("#" + id_).click()
    if screen:
        st = await r.wait(lambda x: x["screen"] == screen, 2000)
        ck(f"[focus] {id_} opens {screen}", st["screen"] == screen, st["screen"])
        return st
    await settle(r.pg)
    return await r.st()

async def _focus_phone_to_scenario(r):
    st = await r.st()
    ck("[focus] Phone starts with Next disabled", st["screen"] == "phone" and st["cta_disabled"])
    ck("[focus] Phone starts without a stale red border", "phoneInput" not in st["bad"])
    ck("[focus] Phone country badge starts hidden", await r.pg.locator("#badge").is_hidden())
    await r.fill("phoneInput", PHONE)
    st = await until(r.st, lambda x: not x["cta_disabled"])
    badge_visible = await r.pg.locator("#badge").is_visible()
    badge_text = (await r.pg.locator("#badge").inner_text()).strip() if badge_visible else ""
    ck("[focus] valid Taiwan phone shows country badge", badge_visible and "TW" in badge_text, badge_text)
    ck("[focus] valid Taiwan phone enables Next", not st["cta_disabled"], str(st))
    await _simple_click(r, "cta", "scenario")
