"""Check plan: every browser test, its layer (vb_core.LAYERS) and whether --fast runs it.

--full runs every test once. --fast runs the tests marked FAST below; the appearance layer ("look")
runs in --fast only when verify_release.py finds app.css, index.html, the layout part of app.js or a
test file changed since the last passing check (--look forces it, --no-look skips it).
The safety layer runs first; if it fails nothing else runs. Every other layer always runs.

The focus_* jobs below are short targeted walks, each guarding a real-device failure.
"""
import vb_core
import vb_flows
import vb_guards
import vb_validation
import vb_guards_other
globals().update({k: v for k, v in vars(vb_core).items() if not k.startswith("__")})
globals().update({k: v for k, v in vars(vb_flows).items() if not k.startswith("__")})
globals().update({k: v for k, v in vars(vb_guards).items() if not k.startswith("__")})


async def focus_phone_matrix(browser):
    # Fixed mobile/landline matrix checks the real UI, including Japan's
    # separate branch. A rejected number uses the normal invalid state.
    r = await Run(browser, "focus-phone-matrix").open()
    for number in ("", "+8", "+81", "+81 0", "+81 90 123", "+886 912", "+852 91"):
        await r.fill("phoneInput", number)
        state = await r.st()
        ck(f"[focus] incomplete phone {number!r} stays neutral",
           state["cta_disabled"] and "phoneInput" not in state["bad"], str(state))
    for number, valid in (
        ("+886 2 2345 6789", False), ("+852 2123 4567", False),
        ("+81 3 1234 5678", False), ("+81 120 123 456", False),
        ("+886 912 345 678", True), ("+852 9123 4567", True),
        ("+81 90 1234 5678", True), ("+81 60 1234 5678", True),
        ("+1 202 555 0123", True), ("+44 7911 123456", True),
    ):
        await r.fill("phoneInput", number)
        state = await r.st()
        ck(f"[focus] {number} {'mobile passes' if valid else 'landline rejects'}",
           state["cta_disabled"] != valid and (("phoneInput" in state["bad"]) != valid), str(state))
    await r.close()


async def focus_home_geometry(browser):
    # Phone + Home visual geometry on the three locked phone widths.
    r = await Run(browser, "focus-home").open()
    await _focus_phone_to_scenario(r)
    for width, want_gap in ((390, 14), (360, 12), (320, 12)):
        await r.pg.set_viewport_size({"width": width, "height": 844})
        await r.pg.wait_for_timeout(80)
        g = await r.pg.evaluate("""() => [...document.querySelectorAll('#s-scenario .choice')].map(b => {
          const i=b.querySelector('.ico').getBoundingClientRect(), t=b.querySelector('.ctext').getBoundingClientRect(), c=b.querySelector('.chev').getBoundingClientRect(), r=b.getBoundingClientRect();
          return {left:r.left,right:r.right,top:r.top,bottom:r.bottom,iconL:i.left,iconR:i.right,textL:t.left,textR:t.right,chevL:c.left,chevR:c.right};
        })""")
        ck(f"[focus] Home {width}px has five Scenario cards", len(g) == 5, str(len(g)))
        if len(g) == 5:
            gaps=[round(x['textL']-x['iconR'],1) for x in g]
            arrows=[round(x['chevR'],1) for x in g]
            overlap=all(x['textR'] <= x['chevL'] + 0.5 for x in g)
            widths=[round(x['right']-x['left'],1) for x in g]
            ck(f"[focus] Home {width}px icon/text spacing is locked", all(abs(x-want_gap)<=1.5 for x in gaps), str(gaps))
            ck(f"[focus] Home {width}px arrows align in one column", max(arrows)-min(arrows)<=1.5, str(arrows))
            ck(f"[focus] Home {width}px text never overlaps arrow", overlap)
            ck(f"[focus] Home {width}px card widths align", max(widths)-min(widths)<=1.5, str(widths))
    await r.close()



SEC_STYLE_JS = """() => {
  const rows=[...document.querySelectorAll('#sum > div')].map(r=>[r.querySelector('dt').textContent.trim(), r.querySelector('dd')]);
  const sec=rows.find(r=>r[0]==='Sec')[1], o=sec.querySelector('.secOrigin');
  const probe=document.createElement('i'); document.body.appendChild(probe);
  const rgb=n=>{probe.style.color='var('+n+')'; return getComputedStyle(probe).color;};
  const out={text:sec.textContent.trim(), origin:o?o.textContent:null, originColour:o?getComputedStyle(o).color:null,
             brand:rgb('--brand'), valueColour:getComputedStyle(sec).color, ink:rgb('--input-ink')};
  probe.remove(); return out;}"""

async def _sec_style(r):
    return await r.pg.evaluate(SEC_STYLE_JS)

async def focus_s1_happy_path(browser):
    # Scenario 1 happy path + Joining Passenger label + unchanged progress wording.
    r = await Run(browser, "focus-s1").open(); await _focus_phone_to_scenario(r)
    await _simple_click(r, "goMiss", "misstype")
    ck("[focus] S1 Passenger Type says Joining Passenger", (await r.pg.locator("#missJoin .ctext").inner_text()).strip() == "Joining Passenger")
    await _simple_click(r, "missJoin", "mflight")
    ck("[focus] S1 progress wording uses Joining Passenger", " ".join((await r.pg.locator("#step").inner_text()).split()) == "漏查 - Joining Passenger 2/3", (await r.pg.locator("#step").inner_text()).strip())
    await r.fill("mFlight", "407"); await r.expect("S1 valid CX407 enables Next", True, not_bad=["mFlight"])
    await _simple_click(r, "cta", "msec"); await r.fill("mSec", "123"); await r.expect("S1 valid SEC enables Next", True, not_bad=["mSec"])
    await _simple_click(r, "cta", "preview")
    ck("[focus] S1 reaches Confirm details", (await r.st())["screen"] == "preview")
    vb_core._LAYER.set("look")  # the colour checks below are appearance
    sec = await _sec_style(r)
    ck("[focus] S1 Join Sec TPE keeps the normal value colour", sec["origin"] is None and sec["text"] == "TPE 123" and sec["valueColour"] == sec["ink"], str(sec))
    await r.close()


async def focus_s2_happy_path(browser):
    # Scenario 2 happy path.
    r = await Run(browser, "focus-s2").open(); await _focus_phone_to_scenario(r)
    await _simple_click(r, "goCall", "calltype")
    ck("[focus] S2 Passenger Type says Joining Passenger", (await r.pg.locator("#callJoin .ctext").inner_text()).strip() == "Joining Passenger")
    await _simple_click(r, "callJoin", "callflight")
    ck("[focus] S2 progress uses Joining Passenger 2/5", " ".join((await r.pg.locator("#step").inner_text()).split()) == "Final Call - Joining Passenger 2/5", (await r.pg.locator("#step").inner_text()).strip())
    await r.fill("callFlight", "407"); await r.expect("S2 valid CX407 enables Next", True, not_bad=["callFlight"])
    await _simple_click(r, "cta", "msec"); ck("[focus] S2 Sec progress is 3/5", " ".join((await r.pg.locator("#step").inner_text()).split()) == "Final Call - Joining Passenger 3/5", (await r.pg.locator("#step").inner_text()).strip())
    await r.fill("mSec", "123"); await r.expect("S2 valid SEC enables Next", True, not_bad=["mSec"])
    await _simple_click(r, "cta", "callgate"); await r.fill("callGate", "5"); await r.expect("S2 valid gate enables Next", True, not_bad=["callGate"])
    await _simple_click(r, "cta", "preview"); ck("[focus] S2 reaches Confirm details", (await r.st())["screen"] == "preview")
    vb_core._LAYER.set("look")  # the colour checks below are appearance
    sec = await _sec_style(r)
    ck("[focus] S2 Join Sec TPE keeps the normal value colour", sec["origin"] is None and sec["text"] == "TPE 123" and sec["valueColour"] == sec["ink"], str(sec))
    g = await r.pg.evaluate(GATE_JS); ck("[focus] S2 Join Go to Gate is --brand", g["row"] == "Go to Gate" and g["colour"] == g["ink"], str(g))
    await r.close()


async def focus_sec_colours(browser):
    # Transit Sec: a non-TPE origin prefix uses --brand; the digits keep the value colour.
    for scen, ptype, field, flight, origin, gate in (("goMiss", "missTransit", "mFlight", "451", "NRT", False),
                                                   ("goCall", "callTransit", "callFlight", "450", "HKG", True)):
        r = await Run(browser, f"focus-sec-{origin}").open(); await _focus_phone_to_scenario(r)
        await _simple_click(r, scen); await _simple_click(r, ptype)
        await r.fill(field, flight); await _simple_click(r, "cta", "msec"); await r.fill("mSec", "123")
        if gate:
            await _simple_click(r, "cta", "callgate"); await r.fill("callGate", "5")
        await _simple_click(r, "cta", "preview")
        sec = await _sec_style(r)
        ck(f"[focus] {scen[2:]} Transit Sec {origin} prefix uses the brand colour", sec["origin"] == origin and sec["originColour"] == sec["brand"] and sec["text"] == origin + " 123", str(sec))
        ck(f"[focus] {scen[2:]} Transit Sec digits keep the value colour", sec["valueColour"] == sec["ink"], str(sec))
        if gate:
            g = await r.pg.evaluate(GATE_JS); ck(f"[focus] {scen[2:]} Transit Go to Gate is --brand", g["row"] == "Go to Gate" and g["colour"] == g["ink"], str(g))
        await r.close()


async def focus_s5_confirm(browser):
    # Scenario 5 happy path + Confirm details completeness.
    r = await Run(browser, "focus-s5").open(); await _focus_phone_to_scenario(r)
    await _simple_click(r, "goWpp", "wflight"); await r.fill("wFlight", "123"); await r.expect("S5 arrival flight enables Next", True, not_bad=["wFlight"])
    await _simple_click(r, "cta", "bag1"); await r.fill("b1n", "123456"); await r.expect("S5 Bag Tag 1 enables Next", True)
    await _simple_click(r, "cta", "bag2"); await r.fill("b2a", "BR"); await r.fill("b2n", "654321"); await r.expect("S5 Bag Tag 2 enables Next", True)
    await _simple_click(r, "cta", "preview")
    rows = await r.pg.evaluate("[...document.querySelectorAll('#sum div')].map(d => d.querySelector('dt').textContent.trim())")
    ck("[focus] S5 Confirm details has all three summary rows", rows == ["Arrival Flight", "Bag Tag 1", "Bag Tag 2"], str(rows))
    vb_core._LAYER.set("look")
    a = await r.pg.locator("#msgToggle>span:first-child").bounding_box(); b = await r.pg.locator("#previewOrderLabel").bounding_box()
    ck("[focus] Message Preview order label has visual separation", bool(a and b) and b["x"] > a["x"] + 110)
    await r.close()


async def focus_s4_flight_rules(browser):
    # Scenario 4: blank is neutral; inbound transit flights rejected; TPE departures accepted.
    r = await Run(browser, "focus-s4").open(); await _focus_phone_to_scenario(r)
    await _simple_click(r, "goDp", "dstatus"); await _simple_click(r, "stGate", "dflight")
    st = await r.st(); ck("[focus] S4 Flight from TPE blank stays neutral", "dFlight" not in st["bad"] and st["cta_disabled"], str(st))
    for n in ("450", "530", "564"):
        await r.fill("dFlight", n); await r.expect(f"S4 CX{n} is not a TPE departure", False, ["dFlight"])
    for n in ("451", "531", "565", "407"):
        await r.fill("dFlight", n); await r.expect(f"S4 CX{n} is accepted as TPE departure", False, not_bad=["dFlight"])
    # A complete gate case with a non-TPE departure must stay blocked (the red border alone is not enough).
    await r.fill("dFlight", "450"); await _simple_click(r, "gsCancelled")
    await r.expect("S4 CX450 + Cancelled keeps Next disabled", False, ["dFlight"])
    await r.fill("dFlight", "451"); await _simple_click(r, "gsCancelled")
    await r.expect("S4 CX451 + Cancelled enables Next", True, not_bad=["dFlight"])
    await _simple_click(r, "cta", "dnew")
    st=await r.st(); ck("[focus] S4 Protect to starts neutral", "gNewN" not in st["bad"] and st["cta_disabled"], str(st))
    for n in ("450", "530", "564"):
        await r.fill("gNewN", n); await r.expect(f"S4 Protect to rejects CX{n}", False, ["gNewN"])
    await r.fill("gNewN", "407"); await r.expect("S4 Protect to accepts CX407", False, not_bad=["gNewN"])
    await r.fill("gGate", "9"); await r.fill("gDepTime", "1955"); await r.blur("gDepTime")
    await r.expect("S4 valid Protect to fields enable Next", True, not_bad=["gNewN","gDepTime"])
    await _simple_click(r, "cta", "dgateaction")
    await _simple_click(r, "gProtectedFlight"); await _simple_click(r, "gpAsap")
    await r.expect("S4 Proceed to Gate selection enables Next", True)
    await _simple_click(r, "cta", "preview"); ck("[focus] S4 reaches Confirm details", (await r.st())["screen"] == "preview")
    await r.close()


async def focus_s4_happy_path(browser):
    # Scenario 4 non-gate happy path: every page with valid input must enable Next.
    r = await Run(browser, "focus-s4-flow").open(); await _focus_phone_to_scenario(r)
    await _simple_click(r, "goDp", "dstatus"); await _simple_click(r, "stPossible", "dflight")
    await r.fill("dFlight", "450"); await r.expect("S4 Tight Connection CX450 keeps Next disabled", False, ["dFlight"])
    await r.fill("dFlight", "451"); await r.expect("S4 Tight Connection flight enables Next", True, not_bad=["dFlight"])
    await _simple_click(r, "cta", "dtransfer")
    await r.fill("tA", "BR"); await r.fill("tN", "123"); await r.expect("S4 Connecting flight enables Next", True, not_bad=["tN"])
    await _simple_click(r, "cta", "darrange"); await _simple_click(r, "arUnknown")
    await r.expect("S4 arrangement choice enables Next", True)
    await _simple_click(r, "cta", "darrive"); await r.fill("arriveTime", "1400"); await r.expect("S4 arrival time enables Next", True, not_bad=["arriveTime"])
    await _simple_click(r, "cta", "preview"); ck("[focus] S4 non-gate flow reaches Confirm details", (await r.st())["screen"] == "preview")
    await r.close()


async def focus_auto_advance(browser):
    # Auto-advance: a complete, valid field moves the cursor to the next empty field; an invalid one keeps it.
    async def focused(r):
        await r.pg.wait_for_timeout(150)
        return await r.pg.evaluate("document.activeElement ? document.activeElement.id : ''")
    async def enter(r, id_, val):
        await r.pg.locator("#" + id_).click(); await r.fill(id_, val)
    r = await Run(browser, "focus-auto-advance").open(); await _focus_phone_to_scenario(r)
    await _simple_click(r, "goDp", "dstatus"); await _simple_click(r, "stGate", "dflight")
    await r.fill("dFlight", "407"); await _simple_click(r, "gsCancelled"); await _simple_click(r, "cta", "dnew")
    await enter(r, "gNewN", "407"); ck("[focus] Protect to: invalid flight keeps the cursor", await focused(r) == "gNewN")
    await enter(r, "gNewN", "401"); ck("[focus] Protect to: valid flight moves to DEP", await focused(r) == "gDepTime")
    await r.fill("gDepTime", "1945"); ck("[focus] Protect to: complete DEP moves to Gate", await focused(r) == "gGate")
    await r.close()
    r = await Run(browser, "focus-auto-advance-2").open(); await _focus_phone_to_scenario(r)
    await _simple_click(r, "goDp", "dstatus"); await _simple_click(r, "stPossible", "dflight")
    await r.fill("dFlight", "451"); await _simple_click(r, "cta", "dtransfer")
    await enter(r, "tA", "BR"); ck("[focus] Connecting flight: airline code moves to number", await focused(r) == "tN")
    await r.fill("tN", "123"); await _simple_click(r, "cta", "darrange"); await _simple_click(r, "arKnown")
    await enter(r, "altA", "BR"); ck("[focus] Flight arrangement: airline code moves to number", await focused(r) == "altN")
    await enter(r, "altN", "401"); ck("[focus] Flight arrangement: valid flight moves to dep time", await focused(r) == "altTime")
    await r.close()
    r = await Run(browser, "focus-auto-advance-3").open(); await _focus_phone_to_scenario(r)
    await _simple_click(r, "goWpp", "wflight"); await r.fill("wFlight", "123"); await _simple_click(r, "cta", "bag1")
    await enter(r, "b1a", "BR"); ck("[focus] Bag 1: airline code moves to tag number", await focused(r) == "b1n")
    await r.close()


async def focus_s4_gate_colour(browser):
    # Already at Gate Confirm details: the Proceed to Gate row is --brand.
    r = await Run(browser, "focus-confirm-S4-gate").open(); await _focus_phone_to_scenario(r)
    await _simple_click(r, "goDp", "dstatus"); await _simple_click(r, "stGate", "dflight")
    await r.fill("dFlight", "407"); await _simple_click(r, "gsCancelled"); await _simple_click(r, "cta", "dnew")
    await fill_protect(r); await _simple_click(r, "cta", "dgateaction")
    await _simple_click(r, "gProtectedFlight"); await _simple_click(r, "gpAsap"); await _simple_click(r, "cta", "preview")
    g = await r.pg.evaluate(GATE_JS)
    ck("[focus] S4 Already at Gate Proceed to Gate is --brand", g["row"] == "Proceed to Gate" and g["colour"] == g["ink"], str(g))
    await r.close()


async def focus_keyboard_single_field(browser):
    # Single-field pages sit lower on taller phones; opening the keyboard must not move the title,
    # scroll the page, or hide the field behind Next. Worst cases: small phones with a tall keyboard.
    KB_JS = """() => {const s=document.querySelector('.screen:not([hidden])'), h=s.querySelector('h1'), f=[...s.querySelectorAll('.field')].filter(x=>x.offsetParent);
      return {id:s.id, kb:document.querySelector('#app').classList.contains('kb'), h1:Math.round(h.getBoundingClientRect().top),
              fb:Math.round(Math.max(...f.map(x=>x.getBoundingClientRect().bottom))), ft:Math.round(document.querySelector('#foot').getBoundingClientRect().top),
              sc:document.querySelector('main').scrollTop, pad:parseFloat(getComputedStyle(s).paddingTop)};}"""
    for label, w, full, visible, steps, field in (
            ("iPhone 390x844 Flight", 390, 844, 550, [("goMiss", None), ("missJoin", None)], "mFlight"),
            ("small Android tall keyboard Bag Tag 1", 360, 668, 348, [("goWpp", None), ("wFlight", "123"), ("cta", None)], "b1n"),
            ("small Android tall keyboard Connecting flight", 360, 668, 348, [("goDp", None), ("stPossible", None), ("dFlight", "451"), ("cta", None)], "tN")):
        r = await Run(browser, "focus-single-field-" + label).open(); await r.pg.set_viewport_size({"width": w, "height": full})
        await _focus_phone_to_scenario(r)
        for trig, val in steps:
            if val is None: await _simple_click(r, trig)
            else: await r.fill(trig, val)
        await r.pg.wait_for_timeout(200); before = await r.pg.evaluate(KB_JS)
        await r.pg.focus("#" + field); await r.pg.set_viewport_size({"width": w, "height": visible}); await r.pg.wait_for_timeout(500)
        after = await r.pg.evaluate(KB_JS)
        ck(f"[focus] {label}: keyboard opens without moving the title or scrolling", after["kb"] and before["h1"] == after["h1"] and after["sc"] == 0, f"{before} -> {after}")
        ck(f"[focus] {label}: field stays above Next with the keyboard open", after["fb"] <= after["ft"] - 6, str(after))
        if full >= 800:
            ck(f"[focus] {label}: page sits lower on a tall phone", before["pad"] > 100, str(before))
        await r.close()


async def focus_b1r_lift(browser):
    # Gate 1 in area B: the layout stays as it is until B1R? appears; then the page lifts so
    # B1R? clears Next, and drops back to the same place when B1R? hides again.
    B1R_JS = """() => {const s=document.querySelector('.screen:not([hidden])'), b=s.querySelector('.gateR');
      return {kb:document.querySelector('#app').classList.contains('kb'), shown:!b.hidden, rb:Math.round(b.getBoundingClientRect().bottom),
              h1:Math.round(s.querySelector('h1').getBoundingClientRect().top), pad:parseFloat(getComputedStyle(s).paddingTop),
              ft:Math.round(document.querySelector('#foot').getBoundingClientRect().top)};}"""
    for label, w, full, visible, gate_path in (("iPhone 393x852 Final Call gate", 393, 852, 450, False),
                                               ("Pro Max 430x932 Final Call gate", 430, 932, 480, False),
                                               ("small Android tall keyboard Protect to gate", 360, 668, 348, True)):
        r = await Run(browser, "focus-b1r-lift-" + label).open(); await r.pg.set_viewport_size({"width": w, "height": full})
        if gate_path:
            await to_s4_gate(r, "407", "gsCancelled"); await r.fill("gNewN", "401"); iid = "gGate"
        else:
            await to_s2_gate(r, "callJoin", "407"); iid = "callGate"
        await r.pg.focus("#" + iid); await r.pg.set_viewport_size({"width": w, "height": visible}); await r.pg.wait_for_timeout(500)
        await r.fill(iid, "2"); rest = await r.pg.evaluate(B1R_JS)
        if not gate_path:
            ck(f"[focus] {label}: original layout kept before B1R? appears", rest["kb"] and rest["pad"] > 100, str(rest))
        await r.fill(iid, "1"); up = await r.pg.evaluate(B1R_JS)
        ck(f"[focus] {label}: B1R? lifts the page above Next", up["shown"] and up["rb"] <= up["ft"] - 6 and up["h1"] < rest["h1"], f"{rest} -> {up}")
        await r.fill(iid, "2"); down = await r.pg.evaluate(B1R_JS)
        ck(f"[focus] {label}: page drops back when B1R? hides", not down["shown"] and down["h1"] == rest["h1"], f"{rest} -> {down}")
        await r.close()


async def focus_privacy(browser):
    # Privacy at run time, on a real http origin (like a phone) where storage is available:
    # a complete Final Call case keeps nothing on the device and loads nothing from another site.
    import http.server as _hs, functools as _ft, threading as _th
    class _Quiet(_hs.SimpleHTTPRequestHandler):
        def log_message(self, *a): pass
    _srv = _hs.ThreadingHTTPServer(("127.0.0.1", 0), _ft.partial(_Quiet, directory=str(R)))
    _th.Thread(target=_srv.serve_forever, daemon=True).start()
    pg = await browser.new_page(viewport={"width": 390, "height": 844}, reduced_motion="reduce")
    _counts = []
    await pg.route(COUNT_HOST + "**", lambda route: answer_count(route, _counts))
    await pg.goto(f"http://127.0.0.1:{_srv.server_address[1]}/index.html")
    # wait_for_function evaluates a string in the page, which the page's CSP refuses; poll with evaluate instead.
    _t0 = asyncio.get_running_loop().time()
    while not await pg.evaluate("!!window.libphonenumber"):
        if asyncio.get_running_loop().time() - _t0 > 15: raise TimeoutError("window.libphonenumber not ready within 15 s")
        await asyncio.sleep(0.05)
    _screen = "document.querySelector('.screen:not([hidden])').id"
    async def _fill(i, v): await pg.fill("#" + i, v); await pg.dispatch_event("#" + i, "input"); await settle(pg)
    async def _tap(i):
        before = await pg.evaluate(_screen); await pg.click("#" + i)
        await until(lambda: pg.evaluate(_screen), lambda s: s != before); await settle(pg)
    await _fill("phoneInput", "886912345678"); await _tap("cta"); await _tap("goCall"); await _tap("callTransit")
    await _fill("callFlight", "450"); await _tap("cta"); await _fill("mSec", "123"); await _tap("cta"); await _fill("callGate", "5"); await _tap("cta")
    pv = await pg.evaluate("""async () => ({screen: document.querySelector('.screen:not([hidden])').id, origin: location.origin,
        outside: performance.getEntriesByType('resource').map(e=>e.name).filter(u=>!u.startsWith(location.origin) && !u.startsWith('data:')),
        local: localStorage.length, session: sessionStorage.length, cookie: document.cookie.length,
        dbs: indexedDB.databases ? (await indexedDB.databases()).length : 0})""")
    ck("[focus] privacy: the real-origin run reached Confirm details", pv["screen"] == "s-preview", str(pv))
    ck("[focus] privacy: nothing loaded from another site except the usage count", not [u for u in pv["outside"] if not u.startswith(COUNT_HOST)], str(pv["outside"]))
    # One home Next = one count, carrying only the fixed name "next", no phone number and no referrer.
    ck("[focus] privacy: one home Next sends exactly one usage count", len(_counts) == 1, str(_counts))
    ck("[focus] privacy: the usage count carries only the fixed name next",
       all(re.fullmatch(r"https://cathaytpeteam\.goatcounter\.com/count\?p=next&e=true&rnd=\d+", c["url"]) and "912345678" not in c["url"] for c in _counts), str(_counts))
    ck("[focus] privacy: the usage count sends no referrer", all("referer" not in c["headers"] for c in _counts), str(_counts))
    ck("[focus] privacy: nothing stored on the device (storage, cookies, databases)", pv["local"] == 0 and pv["session"] == 0 and pv["cookie"] == 0 and pv["dbs"] == 0, str(pv))
    # The Content-Security-Policy makes the browser itself refuse other sites, even if code tried.
    blocked = await pg.evaluate("""() => new Promise(done => {
        const seen = []; document.addEventListener('securitypolicyviolation', e => seen.push(e.effectiveDirective));
        const img = new Image(); img.src = 'https://blocked.example/x.png';
        fetch('https://blocked.example/y').catch(() => {});
        setTimeout(() => done(seen), 500);})""")
    ck("[focus] privacy: the browser blocks other sites (Content-Security-Policy)", "img-src" in blocked and "connect-src" in blocked, str(blocked))
    # One S2 WhatsApp send tap = one more count, carrying only the fixed name S2-WhatsApp, no phone number and no referrer.
    await pg.click("#cta"); await pg.wait_for_timeout(300)  # the send tap leaves the page on Confirm details
    ck("[focus] privacy: one S2 WhatsApp send tap sends exactly one usage count S2-WhatsApp",
       count_names(_counts[1:]) == ["S2-WhatsApp"] and all("912345678" not in c["url"] for c in _counts), str(_counts[1:]))
    await pg.close(); _srv.shutdown()


async def focus_button_colours(browser):
    # Button text colours: every button on every screen uses an approved colour,
    # never the body ink or black (button defaults to color:inherit).
    r = await Run(browser, "focus-button-colours").open()
    bad = await r.pg.evaluate("""() => {
      const probe=document.createElement('i'); document.body.appendChild(probe);
      const rgb=n=>{probe.style.color='var('+n+')'; return getComputedStyle(probe).color;};
      const allowed=['--brand-strong','--delay-ink','--on-brand','--muted'].map(rgb), banned=[rgb('--ink'),'rgb(0, 0, 0)'];
      document.querySelectorAll('section.screen').forEach(x=>x.hidden=false);
      const out=[];
      document.querySelectorAll('button').forEach(b=>{
        const hasText=el=>[...el.childNodes].some(n=>n.nodeType===3&&n.textContent.trim());
        const t=hasText(b)?b:([...b.querySelectorAll('*')].find(hasText)||b);
        const c=getComputedStyle(t).color;
        if(banned.includes(c)||!allowed.includes(c)) out.push((b.id||b.className)+' '+c);
      });
      probe.remove(); return out;}""")
    ck("[focus] button text uses approved colours only (never body ink or black)", not bad, "; ".join(bad))
    await r.close()


async def focus_test_probe(browser):
    """The test probe exists only under automated tests, answers without touching the page or the case,
    refuses the phone page and unknown names, and never returns a passenger number."""
    r = await Run(browser, "test probe").open()
    pr = await r.pg.evaluate("() => { const p = window.__findPaxProbe; return p ? {keys: Object.keys(p).sort(), frozen: Object.isFrozen(p)} : null; }")
    ck("[probe] test probe present under automated tests, frozen, with only check and message", pr == {"keys": ["check", "message"], "frozen": True}, str(pr))
    refused = await r.pg.evaluate("""() => [{step: 'phone'}, {step: 'preview'}, {step: 'mflight', fields: {phoneInput: '1'}},
        {step: 'mflight', state: {phone: '1'}}, {step: 'mflight', state: {callNoMessage: true}}].map(c => {
        try { window.__findPaxProbe.check(c); return false; } catch (e) { return true; } })
        .concat([{flow: 'direct'}, {flow: ''}].map(c => { try { window.__findPaxProbe.message(c); return false; } catch (e) { return true; } }))""")
    ck("[probe] refuses the phone page, Confirm details, Call Directly and unknown fields or state", all(refused), str(refused))
    if (await r.phone())["screen"] != "scenario":  # the home page failed (another safety check names why)
        await r.close(); return
    await r.act("goWpp", "wflight"); await r.fill("wFlight", "123")
    before = (await r.st(), await r.pg.evaluate(vb_validation.FIELD_VALUES_JS, PROBE_FIELDS + ["phoneInput", "msg"]))
    ans = await probe_all(r.pg, "message", [c[1] for c in vb_flows.matrix_cases()[::25]])
    ans += await probe_all(r.pg, "check", [{"step": s, "fields": {"mFlight": "450"}, "state": {"missMode": "join"}} for s in PROBE_STEPS])
    after = (await r.st(), await r.pg.evaluate(vb_validation.FIELD_VALUES_JS, PROBE_FIELDS + ["phoneInput", "msg"]))
    ck("[probe] answers leave the screen, fields and case unchanged", before == after, f"{before} -> {after}")
    text = json.dumps(ans, ensure_ascii=False)
    ck("[probe] answers never carry the passenger number", PHONE[-9:] not in text and PHONE[-9:-6] + " " + PHONE[-6:-3] not in text)
    await r.act("cta", "bag1")
    ck("[probe] the real page still works after probe answers", (await r.st())["screen"] == "bag1")
    await r.close()
    # A staff phone: navigator.webdriver is false, so the probe must not exist at all.
    ctx = await browser.new_context(viewport={"width": 390, "height": 844})
    await ctx.add_init_script("Object.defineProperty(Navigator.prototype, 'webdriver', {get: () => false})")
    pg = await ctx.new_page()
    lib = (R / "libphonenumber-mobile.js").read_text(encoding="utf-8")
    await pg.set_content(HTML.replace("</head>", "<script>" + lib + "</script></head>"), wait_until="domcontentloaded")
    await pg.wait_for_selector("#s-phone:not([hidden])")
    got = await pg.evaluate("() => [navigator.webdriver, '__findPaxProbe' in window, Object.getOwnPropertyNames(window).filter(n => /probe/i.test(n))]")
    ck("[probe] no test probe when the browser is not automated (navigator.webdriver false)", got == [False, False, []], str(got))
    await ctx.close()


async def focus_message_matrix(browser):
    r = await Run(browser, "message matrix").open(); await vb_flows.message_matrix(r); await r.close()


# ---- the plan ------------------------------------------------------------------------
FOCUS = {
    "privacy at run time": ("safety", focus_privacy), "test probe": ("safety", focus_test_probe),
    "message matrix": ("send", focus_message_matrix), "phone matrix": ("input", focus_phone_matrix),
    "S4 flight rules": ("input", focus_s4_flight_rules), "S1 happy path": ("flow", focus_s1_happy_path),
    "S2 happy path": ("flow", focus_s2_happy_path), "S4 happy path": ("flow", focus_s4_happy_path),
    "S5 Confirm details": ("send", focus_s5_confirm), "Home geometry": ("look", focus_home_geometry),
    "Sec colours": ("look", focus_sec_colours), "S4 gate colour": ("look", focus_s4_gate_colour),
    "auto-advance": ("look", focus_auto_advance), "keyboard single field": ("look", focus_keyboard_single_field),
    "B1R lift": ("look", focus_b1r_lift), "button colours": ("look", focus_button_colours),
}

# Layer of every flow case, spec guard and spec state rule (a name missing here fails the run).
CASE_LAYER = {name: ("look" if "B1R" in name else "send") for name, _ in CASES}
GUARD_LAYER = {
    "send": ["s5_call_by_phone_after_whatsapp", "direct_call_by_phone_after_whatsapp", "s1_call_by_phone_after_whatsapp",
             "s2_call_by_phone_after_sms", "s4_no_call_by_phone", "s1_join_short_message", "s2_transit_ja_all_flights",
             "try_another_number_language_follows_new_number", "s1_s2_language_pick_keeps_button_order", "phone_formats_normalize",
             "s2_transit_confirm_shows_dep_from", "direct_call_confirm_shows_grouped_phone", "s2_sec_rules_history_and_summary_order"],
    "clear": ["home_clear_resets_number_and_kept_case", "home_button_returns_home_without_number", "scenario_pick_clears_every_case",
              "try_another_number_keeps_case", "new_number_after_back_starts_from_send", "edited_field_after_back_starts_from_send",
              "s1_mode_switch_clears_inputs", "s1_same_mode_keeps_inputs", "s2_mode_switch_clears_inputs",
              "s4_flight_type_switch_clears_delay_time", "s4_same_flight_type_keeps_delay_time", "back_preserves_inputs",
              "s4_leaving_gate_branch_clears_fields", "s4_same_gate_branch_keeps_fields"],
    "input": ["s4_delayed_requires_time", "s4_connecting_allows_non_cx", "s4_connecting_rejects_bad_airline", "s4_arrange_requires_choice",
              "s4_protect_requires_valid_flight_and_time", "s4_protect_cx_requires_tpe_whitelist", "s4_protect_rejects_same_tpe_flight",
              "s4_protect_allows_non_cx", "s4_gate_status_required", "s4_gate_delayed_requires_time", "s4_gate_protect_rules",
              "s4_gate_requires_valid_gate", "s4_gate_dep_and_proceed_required"],
    "flow": ["s4_flight_type_has_no_next", "s4_non_delayed_hides_time", "enter_key_advances"],
    "open": ["phone_library_retries_after_bad_load"],
    "look": ["confirm_details_text_style", "header_number_on_passenger_type", "impossible_prefix_red_immediately", "layout_does_not_jump",
             "partial_flight_not_red_while_typing", "passenger_type_rows_full_width", "phone_input_fits", "progress_title_fits",
             "progress_title_style", "s2_flight_field_aligns_with_sec", "s4_delayed_bad_time_shows_hint", "s4_delayed_flight_focuses_time",
             "s4_delayed_time_display", "s4_flight_type_look", "s4_gate_b1r_row_keeps_height", "s4_gate_fields_side_by_side",
             "s4_protect_fields_side_by_side", "s4_protect_panel_attached_to_option", "scenario_icons_size"],
}
SPEC_LAYER = {n: k for k, names in GUARD_LAYER.items() for n in names}
# Validation jobs: rows on one path share a page (vb_validation.WALKS); the Phone number row covers
# canned (blocked) numbers, so it belongs to safety. The rule matrix asks the probe every value.
ROW_LAYER = dict({name: layer for name, (layer, _) in vb_validation.WALKS.items()}, **{"rule matrix": "input"})

# --fast: safety, one case per way out (WhatsApp, Japanese SMS 1 and 2 parts, WhatsApp call, tel:, S4, S5),
# the clear-on-pick / Home / type-switch rules, the validation table, and the earlier fast-gate guards.
# Appearance tests are all skipped or all run (see the module docstring); everything else waits for --full.
FAST = {
    "privacy at run time", "test probe", "message matrix", "S1 missJoin ordZh", "S1 missTransit ordJa", "S2 callJoin ordEn", "S2 callTransit ordJa", "Call Directly",
    "S4 stPossible arKnown ordEn", "S4 Already at Gate gsDelayed gProtectedFlight gpAsap ordZh CX531", "S5 ordEn",
    "s2_call_by_phone_after_sms", "s2_sec_rules_history_and_summary_order", "s1_join_short_message",
    "s2_transit_confirm_shows_dep_from", "direct_call_confirm_shows_grouped_phone",
    "scenario_pick_clears_every_case", "home_button_returns_home_without_number", "s1_mode_switch_clears_inputs",
    "s2_mode_switch_clears_inputs", "s4_flight_type_switch_clears_delay_time", "s4_leaving_gate_branch_clears_fields",
    "S4 flight rules", "s4_gate_status_required", "s4_gate_delayed_requires_time", "s4_gate_requires_valid_gate",
    "s4_gate_dep_and_proceed_required", "s4_flight_type_has_no_next", "phone_library_retries_after_bad_load",
} | {"validation: " + n for n in ROW_LAYER}

LAYER_ORDER = [k for k, _ in LAYERS]

# The longest jobs start first (after safety), so with --jobs 2/3 they do not finish last on their own.
# Order never changes which checks run or their totals.
START_FIRST = ["validation: rule matrix", "home_button_returns_home_without_number", "keyboard single field",
               "auto-advance", "B1R lift", "scenario_pick_clears_every_case"]


def plan_problems():
    """Spec names with no layer, layer names that are not in the spec, and FAST / START_FIRST names that are not tests."""
    named = set(FOCUS) | set(CASE_LAYER) | {"validation: " + n for n in ROW_LAYER}
    spec = set(SPEC["guards"]) | set(SPEC["state_rules"])
    return sorted(spec - set(SPEC_LAYER)) + sorted(f"{n} (no such test)" for n in (set(SPEC_LAYER) - spec) | ((FAST | set(START_FIRST)) - named - spec))


def tests(browser):
    """Every browser test as (name, layer, job), safety first, then layer by layer."""
    cases = dict(CASES)
    async def guard(r, name): ck(f"guard implemented: {name}", await g(r, name))
    async def guard_part(r, name, part, first):
        await vb_guards.GUARDS[name](r, part=part)
        if first: ck(f"guard implemented: {name}", True)
    async def state_rule(r, name): ck(f"state rule implemented: {name}", await rule(r, name))
    out = []
    for name, (layer, fn) in FOCUS.items():
        async def job(fn=fn): await fn(browser)
        job.label, job.layer = name, layer
        out.append((name, layer, job))
    out += [(n, CASE_LAYER[n], run_job(browser, n, cases[n], CASE_LAYER[n])) for n in cases]
    for n in SPEC["guards"]:
        layer = SPEC_LAYER.get(n, "flow")
        if n in vb_guards.GUARDS and n in vb_guards_other.GUARD_PARTS:  # one job per part, run at the same time
            parts = vb_guards_other.GUARD_PARTS[n]
            out += [(n, layer, run_job(browser, f"{n} · {pt}", lambda r, n=n, pt=pt, i=i: guard_part(r, n, pt, i == 0), layer))
                    for i, pt in enumerate(parts)]
        else:
            out.append((n, layer, run_job(browser, n, lambda r, n=n: guard(r, n), layer)))
    out += [(n, SPEC_LAYER.get(n, "flow"), run_job(browser, n, lambda r, n=n: state_rule(r, n), SPEC_LAYER.get(n, "flow"))) for n in SPEC["state_rules"]]
    out += [(j.label, j.layer, j) for j in vb_validation.table_jobs(browser)]
    return sorted(out, key=lambda t: LAYER_ORDER.index(t[1]))


async def run(fast, look):
    """Run the plan: safety first (stop if it fails), then every other selected test.
    Returns the layers that did not run."""
    from playwright.async_api import async_playwright
    bad = plan_problems()
    ck("plan: every test has a layer and every FAST name is a test", not bad, ", ".join(bad[:8]))
    skipped = {"look"} if fast and not look else set()
    async with async_playwright() as p:
        browser = await launch_chromium(p)
        chosen = [(layer, j) for n, layer, j in sorted(tests(browser), key=lambda t: START_FIRST.index(t[0]) if t[0] in START_FIRST else len(START_FIRST))
                  if layer not in skipped and (not fast or n in FAST or layer == "look")]
        await run_jobs([j for layer, j in chosen if layer == "safety"])
        if vb_core.LAYER_COUNTS["safety"][1]:
            print("FAIL 安全檢查失敗：其他瀏覽器檢查沒有執行（先修好上面的安全問題）", flush=True)
            await browser.close()
            return set(LAYER_ORDER) - {"safety"}
        await run_jobs([j for layer, j in chosen if layer != "safety"])
        await browser.close()
    ck("runtime: no transition outside the spec", not unexpected, " | ".join(sorted(set(unexpected))[:8]))
    if not fast:
        miss = [k for k in EDGE_INDEX if k not in covered]
        ck(f"runtime: all {len(EDGE_INDEX)} spec branches executed ({len(covered)} hit)", not miss,
           " | ".join(f"{k[0]} '{k[1]}' {list(k[5])} --{k[2]}--> {k[3]} '{k[4]}'" for k in miss[:8]))
        nav = [k for k in covered if not k[3].startswith("external:")]
        ck(f"runtime: Back + Forward verified for all {len(nav)} in-app branches", all(k in back_verified for k in nav))
        tg = {(s, t) for s, ts in SPEC["toggles"].items() for t in ts}
        ck("runtime: every toggle control exercised", tg <= toggles_hit, str(sorted(tg - toggles_hit)))
        lm = [t for t in SPEC["preview_languages"] if t not in lang_checked]
        ck("runtime: language buttons checked on every preview type", not lm, str(lm))
    return skipped


async def only(name):
    """Run one named test: a plan name, flow case, guard, state rule or validation row."""
    import difflib
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        browser = await launch_chromium(p)
        everything = tests(browser)
        found = [j for n, _, j in everything if n in (name, "validation: " + name)]
        found = found if len({j.label.split(" · ")[0] for j in found}) == 1 else found[:1]  # every part of a split guard
        found = found or [j for _, _, j in everything if j.label == name]  # one part: "NAME · part"
        if found:
            await run_jobs(found)
        else:
            ck(f"--only: no test named {name!r}", False,
               "closest: " + ", ".join(difflib.get_close_matches(name, [n for n, _, _ in everything], 8, 0.3)))
        await browser.close()
