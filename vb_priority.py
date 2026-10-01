"""Fast release gate (--priority): focused checks plus sampled full-suite flows, guards and rules."""
import vb_core
import vb_flows
import vb_guards
import vb_validation
globals().update({k: v for k, v in vars(vb_core).items() if not k.startswith("__")})
globals().update({k: v for k, v in vars(vb_flows).items() if not k.startswith("__")})
globals().update({k: v for k, v in vars(vb_guards).items() if not k.startswith("__")})


async def priority_suite():
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        browser = await launch_chromium(p)

        # Fixed mobile/landline matrix checks the real UI, including Japan's
        # separate branch. A rejected number uses the normal invalid state.
        r = await Run(browser, "priority-phone-matrix").open()
        for number in ("", "+8", "+81", "+81 0", "+81 90 123", "+886 912", "+852 91"):
            await r.fill("phoneInput", number)
            state = await r.st()
            ck(f"[priority] incomplete phone {number!r} stays neutral",
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
            ck(f"[priority] {number} {'mobile passes' if valid else 'landline rejects'}",
               state["cta_disabled"] != valid and (("phoneInput" in state["bad"]) != valid), str(state))
        await r.close()

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
        sec = await r.pg.evaluate("""() => {
          const rows=[...document.querySelectorAll('#sum > div')].map(r=>[r.querySelector('dt').textContent.trim(), r.querySelector('dd')]);
          const sec=rows.find(r=>r[0]==='Sec')[1], o=sec.querySelector('.secOrigin');
          const probe=document.createElement('i'); document.body.appendChild(probe);
          const rgb=n=>{probe.style.color='var('+n+')'; return getComputedStyle(probe).color;};
          const out={text:sec.textContent.trim(), origin:o?o.textContent:null, originColour:o?getComputedStyle(o).color:null,
                     brand:rgb('--brand'), valueColour:getComputedStyle(sec).color, ink:rgb('--input-ink')};
          probe.remove(); return out;}""")
        ck("[priority] S1 Join Sec TPE keeps the normal value colour", sec["origin"] is None and sec["text"] == "TPE 123" and sec["valueColour"] == sec["ink"], str(sec))
        await r.close()

        # Scenario 2 happy path.
        r = await Run(browser, "priority-s2").open(); await _priority_phone_to_scenario(r)
        await _simple_click(r, "goCall", "calltype")
        ck("[priority] S2 Passenger Type says Joining Passenger", (await r.pg.locator("#callJoin .ctext").inner_text()).strip() == "Joining Passenger")
        await _simple_click(r, "callJoin", "callflight")
        ck("[priority] S2 progress uses Joining Passenger 2/5", " ".join((await r.pg.locator("#step").inner_text()).split()) == "Final Call - Joining Passenger 2/5", (await r.pg.locator("#step").inner_text()).strip())
        await r.fill("callFlight", "407"); await r.expect("S2 valid CX407 enables Next", True, not_bad=["callFlight"])
        await _simple_click(r, "cta", "msec"); ck("[priority] S2 Sec progress is 3/5", " ".join((await r.pg.locator("#step").inner_text()).split()) == "Final Call - Joining Passenger 3/5", (await r.pg.locator("#step").inner_text()).strip())
        await r.fill("mSec", "123"); await r.expect("S2 valid SEC enables Next", True, not_bad=["mSec"])
        await _simple_click(r, "cta", "callgate"); await r.fill("callGate", "5"); await r.expect("S2 valid gate enables Next", True, not_bad=["callGate"])
        await _simple_click(r, "cta", "preview"); ck("[priority] S2 reaches Confirm details", (await r.st())["screen"] == "preview")
        sec = await r.pg.evaluate("""() => {
          const rows=[...document.querySelectorAll('#sum > div')].map(r=>[r.querySelector('dt').textContent.trim(), r.querySelector('dd')]);
          const sec=rows.find(r=>r[0]==='Sec')[1], o=sec.querySelector('.secOrigin');
          const probe=document.createElement('i'); document.body.appendChild(probe);
          const rgb=n=>{probe.style.color='var('+n+')'; return getComputedStyle(probe).color;};
          const out={text:sec.textContent.trim(), origin:o?o.textContent:null, originColour:o?getComputedStyle(o).color:null,
                     brand:rgb('--brand'), valueColour:getComputedStyle(sec).color, ink:rgb('--input-ink')};
          probe.remove(); return out;}""")
        ck("[priority] S2 Join Sec TPE keeps the normal value colour", sec["origin"] is None and sec["text"] == "TPE 123" and sec["valueColour"] == sec["ink"], str(sec))
        g = await r.pg.evaluate(GATE_JS); ck("[priority] S2 Join Go to Gate is --brand", g["row"] == "Go to Gate" and g["colour"] == g["ink"], str(g))
        await r.close()

        # Transit Sec: a non-TPE origin prefix uses --brand; the digits keep the value colour.
        for scen, ptype, field, flight, origin, gate in (("goMiss", "missTransit", "mFlight", "451", "NRT", False),
                                                       ("goCall", "callTransit", "callFlight", "450", "HKG", True)):
            r = await Run(browser, f"priority-sec-{origin}").open(); await _priority_phone_to_scenario(r)
            await _simple_click(r, scen); await _simple_click(r, ptype)
            await r.fill(field, flight); await _simple_click(r, "cta", "msec"); await r.fill("mSec", "123")
            if gate:
                await _simple_click(r, "cta", "callgate"); await r.fill("callGate", "5")
            await _simple_click(r, "cta", "preview")
            sec = await r.pg.evaluate("""() => {
          const rows=[...document.querySelectorAll('#sum > div')].map(r=>[r.querySelector('dt').textContent.trim(), r.querySelector('dd')]);
          const sec=rows.find(r=>r[0]==='Sec')[1], o=sec.querySelector('.secOrigin');
          const probe=document.createElement('i'); document.body.appendChild(probe);
          const rgb=n=>{probe.style.color='var('+n+')'; return getComputedStyle(probe).color;};
          const out={text:sec.textContent.trim(), origin:o?o.textContent:null, originColour:o?getComputedStyle(o).color:null,
                     brand:rgb('--brand'), valueColour:getComputedStyle(sec).color, ink:rgb('--input-ink')};
          probe.remove(); return out;}""")
            ck(f"[priority] {scen[2:]} Transit Sec {origin} prefix uses the brand colour", sec["origin"] == origin and sec["originColour"] == sec["brand"] and sec["text"] == origin + " 123", str(sec))
            ck(f"[priority] {scen[2:]} Transit Sec digits keep the value colour", sec["valueColour"] == sec["ink"], str(sec))
            if gate:
                g = await r.pg.evaluate(GATE_JS); ck(f"[priority] {scen[2:]} Transit Go to Gate is --brand", g["row"] == "Go to Gate" and g["colour"] == g["ink"], str(g))
            await r.close()

        # Scenario 5 happy path + Confirm details completeness.
        r = await Run(browser, "priority-s5").open(); await _priority_phone_to_scenario(r)
        await _simple_click(r, "goWpp", "wflight"); await r.fill("wFlight", "123"); await r.expect("S5 arrival flight enables Next", True, not_bad=["wFlight"])
        await _simple_click(r, "cta", "bag1"); await r.fill("b1n", "123456"); await r.expect("S5 Bag Tag 1 enables Next", True)
        await _simple_click(r, "cta", "bag2"); await r.fill("b2a", "BR"); await r.fill("b2n", "654321"); await r.expect("S5 Bag Tag 2 enables Next", True)
        await _simple_click(r, "cta", "preview")
        rows = await r.pg.evaluate("[...document.querySelectorAll('#sum div')].map(d => d.querySelector('dt').textContent.trim())")
        ck("[priority] S5 Confirm details has all three summary rows", rows == ["Arrival Flight", "Bag Tag 1", "Bag Tag 2"], str(rows))
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
        # A complete gate case with a non-TPE departure must stay blocked (the red border alone is not enough).
        await r.fill("dFlight", "450"); await _simple_click(r, "gsCancelled")
        await r.expect("S4 CX450 + Cancelled keeps Next disabled", False, ["dFlight"])
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
        await r.fill("dFlight", "450"); await r.expect("S4 Tight Connection CX450 keeps Next disabled", False, ["dFlight"])
        await r.fill("dFlight", "451"); await r.expect("S4 Tight Connection flight enables Next", True, not_bad=["dFlight"])
        await _simple_click(r, "cta", "dtransfer")
        await r.fill("tA", "BR"); await r.fill("tN", "123"); await r.expect("S4 Connecting flight enables Next", True, not_bad=["tN"])
        await _simple_click(r, "cta", "darrange"); await _simple_click(r, "arUnknown")
        await r.expect("S4 arrangement choice enables Next", True)
        await _simple_click(r, "cta", "darrive"); await r.fill("arriveTime", "1400"); await r.expect("S4 arrival time enables Next", True, not_bad=["arriveTime"])
        await _simple_click(r, "cta", "preview"); ck("[priority] S4 non-gate flow reaches Confirm details", (await r.st())["screen"] == "preview")
        await r.close()

        # Auto-advance: a complete, valid field moves the cursor to the next empty field; an invalid one keeps it.
        async def focused(r):
            await r.pg.wait_for_timeout(150)
            return await r.pg.evaluate("document.activeElement ? document.activeElement.id : ''")
        async def enter(r, id_, val):
            await r.pg.locator("#" + id_).click(); await r.fill(id_, val)
        r = await Run(browser, "priority-auto-advance").open(); await _priority_phone_to_scenario(r)
        await _simple_click(r, "goDp", "dstatus"); await _simple_click(r, "stGate", "dflight")
        await r.fill("dFlight", "407"); await _simple_click(r, "gsCancelled"); await _simple_click(r, "cta", "dnew")
        await enter(r, "gNewN", "407"); ck("[priority] Protect to: invalid flight keeps the cursor", await focused(r) == "gNewN")
        await enter(r, "gNewN", "401"); ck("[priority] Protect to: valid flight moves to DEP", await focused(r) == "gDepTime")
        await r.fill("gDepTime", "1945"); ck("[priority] Protect to: complete DEP moves to Gate", await focused(r) == "gGate")
        await r.close()
        r = await Run(browser, "priority-auto-advance-2").open(); await _priority_phone_to_scenario(r)
        await _simple_click(r, "goDp", "dstatus"); await _simple_click(r, "stPossible", "dflight")
        await r.fill("dFlight", "451"); await _simple_click(r, "cta", "dtransfer")
        await enter(r, "tA", "BR"); ck("[priority] Connecting flight: airline code moves to number", await focused(r) == "tN")
        await r.fill("tN", "123"); await _simple_click(r, "cta", "darrange"); await _simple_click(r, "arKnown")
        await enter(r, "altA", "BR"); ck("[priority] Flight arrangement: airline code moves to number", await focused(r) == "altN")
        await enter(r, "altN", "401"); ck("[priority] Flight arrangement: valid flight moves to dep time", await focused(r) == "altTime")
        await r.close()
        r = await Run(browser, "priority-auto-advance-3").open(); await _priority_phone_to_scenario(r)
        await _simple_click(r, "goWpp", "wflight"); await r.fill("wFlight", "123"); await _simple_click(r, "cta", "bag1")
        await enter(r, "b1a", "BR"); ck("[priority] Bag 1: airline code moves to tag number", await focused(r) == "b1n")
        await r.close()

        # Already at Gate Confirm details: the Proceed to Gate row is --brand.
        r = await Run(browser, "priority-confirm-S4-gate").open(); await _priority_phone_to_scenario(r)
        await _simple_click(r, "goDp", "dstatus"); await _simple_click(r, "stGate", "dflight")
        await r.fill("dFlight", "407"); await _simple_click(r, "gsCancelled"); await _simple_click(r, "cta", "dnew")
        await fill_protect(r); await _simple_click(r, "cta", "dgateaction")
        await _simple_click(r, "gProtectedFlight"); await _simple_click(r, "gpAsap"); await _simple_click(r, "cta", "preview")
        g = await r.pg.evaluate(GATE_JS)
        ck("[priority] S4 Already at Gate Proceed to Gate is --brand", g["row"] == "Proceed to Gate" and g["colour"] == g["ink"], str(g))
        await r.close()

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
            r = await Run(browser, "priority-single-field-" + label).open(); await r.pg.set_viewport_size({"width": w, "height": full})
            await _priority_phone_to_scenario(r)
            for trig, val in steps:
                if val is None: await _simple_click(r, trig)
                else: await r.fill(trig, val)
            await r.pg.wait_for_timeout(200); before = await r.pg.evaluate(KB_JS)
            await r.pg.focus("#" + field); await r.pg.set_viewport_size({"width": w, "height": visible}); await r.pg.wait_for_timeout(500)
            after = await r.pg.evaluate(KB_JS)
            ck(f"[priority] {label}: keyboard opens without moving the title or scrolling", after["kb"] and before["h1"] == after["h1"] and after["sc"] == 0, f"{before} -> {after}")
            ck(f"[priority] {label}: field stays above Next with the keyboard open", after["fb"] <= after["ft"] - 6, str(after))
            if full >= 800:
                ck(f"[priority] {label}: page sits lower on a tall phone", before["pad"] > 100, str(before))
            await r.close()

        # Gate 1 in area B: the layout stays as it is until B1R? appears; then the page lifts so
        # B1R? clears Next, and drops back to the same place when B1R? hides again.
        B1R_JS = """() => {const s=document.querySelector('.screen:not([hidden])'), b=s.querySelector('.gateR');
          return {kb:document.querySelector('#app').classList.contains('kb'), shown:!b.hidden, rb:Math.round(b.getBoundingClientRect().bottom),
                  h1:Math.round(s.querySelector('h1').getBoundingClientRect().top), pad:parseFloat(getComputedStyle(s).paddingTop),
                  ft:Math.round(document.querySelector('#foot').getBoundingClientRect().top)};}"""
        for label, w, full, visible, gate_path in (("iPhone 393x852 Final Call gate", 393, 852, 450, False),
                                                   ("Pro Max 430x932 Final Call gate", 430, 932, 480, False),
                                                   ("small Android tall keyboard Protect to gate", 360, 668, 348, True)):
            r = await Run(browser, "priority-b1r-lift-" + label).open(); await r.pg.set_viewport_size({"width": w, "height": full})
            if gate_path:
                await to_s4_gate(r, "407", "gsCancelled"); await r.fill("gNewN", "401"); iid = "gGate"
            else:
                await to_s2_gate(r, "callJoin", "407"); iid = "callGate"
            await r.pg.focus("#" + iid); await r.pg.set_viewport_size({"width": w, "height": visible}); await r.pg.wait_for_timeout(500)
            await r.fill(iid, "2"); rest = await r.pg.evaluate(B1R_JS)
            if not gate_path:
                ck(f"[priority] {label}: original layout kept before B1R? appears", rest["kb"] and rest["pad"] > 100, str(rest))
            await r.fill(iid, "1"); up = await r.pg.evaluate(B1R_JS)
            ck(f"[priority] {label}: B1R? lifts the page above Next", up["shown"] and up["rb"] <= up["ft"] - 6 and up["h1"] < rest["h1"], f"{rest} -> {up}")
            await r.fill(iid, "2"); down = await r.pg.evaluate(B1R_JS)
            ck(f"[priority] {label}: page drops back when B1R? hides", not down["shown"] and down["h1"] == rest["h1"], f"{rest} -> {down}")
            await r.close()

        # Privacy at run time, on a real http origin (like a phone) where storage is available:
        # a complete Final Call case keeps nothing on the device and loads nothing from another site.
        import http.server as _hs, functools as _ft, threading as _th
        class _Quiet(_hs.SimpleHTTPRequestHandler):
            def log_message(self, *a): pass
        _srv = _hs.ThreadingHTTPServer(("127.0.0.1", 0), _ft.partial(_Quiet, directory=str(R)))
        _th.Thread(target=_srv.serve_forever, daemon=True).start()
        pg = await browser.new_page(viewport={"width": 390, "height": 844})
        _counts = []
        await pg.route(COUNT_HOST + "**", lambda route: answer_count(route, _counts))
        await pg.goto(f"http://127.0.0.1:{_srv.server_address[1]}/index.html")
        # wait_for_function evaluates a string in the page, which the page's CSP refuses; poll with evaluate instead.
        _t0 = asyncio.get_running_loop().time()
        while not await pg.evaluate("!!window.libphonenumber"):
            if asyncio.get_running_loop().time() - _t0 > 15: raise TimeoutError("window.libphonenumber not ready within 15 s")
            await asyncio.sleep(0.05)
        async def _fill(i, v): await pg.fill("#" + i, v); await pg.dispatch_event("#" + i, "input"); await pg.wait_for_timeout(120)
        async def _tap(i): await pg.click("#" + i); await pg.wait_for_timeout(250)
        await _fill("phoneInput", "886912345678"); await _tap("cta"); await _tap("goCall"); await _tap("callTransit")
        await _fill("callFlight", "450"); await _tap("cta"); await _fill("mSec", "123"); await _tap("cta"); await _fill("callGate", "5"); await _tap("cta")
        pv = await pg.evaluate("""async () => ({screen: document.querySelector('.screen:not([hidden])').id, origin: location.origin,
            outside: performance.getEntriesByType('resource').map(e=>e.name).filter(u=>!u.startsWith(location.origin) && !u.startsWith('data:')),
            local: localStorage.length, session: sessionStorage.length, cookie: document.cookie.length,
            dbs: indexedDB.databases ? (await indexedDB.databases()).length : 0})""")
        ck("[priority] privacy: the real-origin run reached Confirm details", pv["screen"] == "s-preview", str(pv))
        ck("[priority] privacy: nothing loaded from another site except the usage count", not [u for u in pv["outside"] if not u.startswith(COUNT_HOST)], str(pv["outside"]))
        # One home Next = one count, carrying only the fixed name "next", no phone number and no referrer.
        ck("[priority] privacy: one home Next sends exactly one usage count", len(_counts) == 1, str(_counts))
        ck("[priority] privacy: the usage count carries only the fixed name next",
           all(re.fullmatch(r"https://cathaytpeteam\.goatcounter\.com/count\?p=next&e=true&rnd=\d+", c["url"]) and "912345678" not in c["url"] for c in _counts), str(_counts))
        ck("[priority] privacy: the usage count sends no referrer", all("referer" not in c["headers"] for c in _counts), str(_counts))
        ck("[priority] privacy: nothing stored on the device (storage, cookies, databases)", pv["local"] == 0 and pv["session"] == 0 and pv["cookie"] == 0 and pv["dbs"] == 0, str(pv))
        # The Content-Security-Policy makes the browser itself refuse other sites, even if code tried.
        blocked = await pg.evaluate("""() => new Promise(done => {
            const seen = []; document.addEventListener('securitypolicyviolation', e => seen.push(e.effectiveDirective));
            const img = new Image(); img.src = 'https://blocked.example/x.png';
            fetch('https://blocked.example/y').catch(() => {});
            setTimeout(() => done(seen), 500);})""")
        ck("[priority] privacy: the browser blocks other sites (Content-Security-Policy)", "img-src" in blocked and "connect-src" in blocked, str(blocked))
        # One S2 WhatsApp send tap = one more count, carrying only the fixed name S2-WhatsApp, no phone number and no referrer.
        await _tap("cta"); await pg.wait_for_timeout(300)
        ck("[priority] privacy: one S2 WhatsApp send tap sends exactly one usage count S2-WhatsApp",
           count_names(_counts[1:]) == ["S2-WhatsApp"] and all("912345678" not in c["url"] for c in _counts), str(_counts[1:]))
        await pg.close(); _srv.shutdown()

        # Button text colours: every button on every screen uses an approved colour,
        # never the body ink or black (button defaults to color:inherit).
        r = await Run(browser, "priority-button-colours").open()
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
        ck("[priority] button text uses approved colours only (never body ink or black)", not bad, "; ".join(bad))
        await r.close()

        await browser.close()


# Sampled from the full suite: each of these catches a planted bug that the priority gate above misses
# (mutation testing). Running them here keeps those protections in the fast check.
PRIORITY_CASES = ["S1 missJoin ordZh", "Call Directly", "S4 stPossible arKnown ordEn",
                  "S4 Already at Gate gsDelayed gProtectedFlight gpAsap ordZh CX531", "Final Call B1R", "Protect to B1R"]
PRIORITY_GUARDS = ["s2_sec_rules_history_and_summary_order", "header_number_on_passenger_type",
                   "s1_join_short_message", "s4_gate_delayed_requires_time", "s4_gate_requires_valid_gate",
                   "s2_transit_confirm_shows_dep_from", "direct_call_confirm_shows_grouped_phone", "s4_flight_type_has_no_next",
                   "s4_delayed_flight_focuses_time", "s4_delayed_bad_time_shows_hint", "s4_gate_status_required",
                   "s4_gate_dep_and_proceed_required", "progress_title_style", "confirm_details_text_style",
                   "passenger_type_rows_full_width", "scenario_icons_size", "s2_flight_field_aligns_with_sec",
                   "s4_flight_type_look", "s4_gate_b1r_row_keeps_height",
                   "phone_library_retries_after_bad_load"]
PRIORITY_RULES = ["s1_mode_switch_clears_inputs", "s2_mode_switch_clears_inputs", "s4_flight_type_switch_clears_delay_time",
                  "s4_leaving_gate_branch_clears_fields", "scenario_reentry_starts_clean"]

async def priority_gate():
    """The whole --priority run: priority_suite (own browser, the longest job, so it starts first) beside
    the sampled cases, guards and rules and the validation table, workers() jobs at a time."""
    from playwright.async_api import async_playwright
    cases = dict(CASES)
    async def guard(r, name): ck(f"[priority] guard: {name}", await g(r, name))
    async def state_rule(r, name): ck(f"[priority] state rule: {name}", await rule(r, name))
    async with async_playwright() as p:
        browser = await launch_chromium(p)
        jobs = [priority_suite]
        jobs += [run_job(browser, name, cases[name]) for name in PRIORITY_CASES]
        jobs += [run_job(browser, name, lambda r, name=name: guard(r, name)) for name in PRIORITY_GUARDS]
        jobs += [run_job(browser, name, lambda r, name=name: state_rule(r, name)) for name in PRIORITY_RULES]
        jobs += vb_validation.table_jobs(browser)
        await run_jobs(jobs)
        await browser.close()
    ck("[priority] sampled flows stay inside the spec", not unexpected, " | ".join(sorted(set(unexpected))[:8]))
