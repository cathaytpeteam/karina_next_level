"""Phone, Scenario 1/2/5 and cross-scenario guards from flow-behavior-spec.json."""
import vb_core
import vb_flows
globals().update({k: v for k, v in vars(vb_core).items() if not k.startswith("__")})
globals().update({k: v for k, v in vars(vb_flows).items() if not k.startswith("__")})


async def guard_home_clear_resets_number_and_kept_case(r, name="home_clear_resets_number_and_kept_case"):
    clear_js = "(() => { const e = document.getElementById('phoneInput'), c = document.getElementById('clearAll'), i = document.querySelector('.phoneHeroIcon').getBoundingClientRect(); return {hidden: c.hidden, text: c.textContent.trim(), focused: document.activeElement === e, value: e.value, badge: document.getElementById('badge').hidden, warn: document.getElementById('warn').classList.contains('show'), iconTop: Math.round(i.top)}; })()"
    c0 = await r.pg.evaluate(clear_js)
    ck("[guard] Home Clear hidden on an empty phone page", c0["hidden"], str(c0))
    await r.fill("phoneInput", "85289648964")
    c1 = await r.pg.evaluate(clear_js)
    ck("[guard] Home Clear appears with a number and reads Clear", not c1["hidden"] and c1["text"] == "Clear", str(c1))
    ck("[guard] Home Clear appearing does not move the home icon", c1["iconTop"] == c0["iconTop"], f"{c0['iconTop']} -> {c1['iconTop']}")
    await r.act("clearAll")
    c2 = await r.pg.evaluate(clear_js)
    ck("[guard] Home Clear empties the number, badge and warning and keeps focus", c2["value"] == "" and c2["badge"] and not c2["warn"] and c2["focused"] and c2["hidden"], str(c2))
    await r.expect("Home Clear leaves Next disabled and no red border", cta_enabled=False, not_bad=["phoneInput"])
    s_ = await r.st(); ck("[guard] Home Clear stays on the phone page", s_["screen"] == "phone", s_["screen"])
    await case_s5(r, "ordZh")
    await return_from_app(r)
    await r.pg.click("#cta"); await r.wait(lambda s: s["screen"] == "phone")
    c3 = await r.pg.evaluate(clear_js)
    ck("[guard] Home Clear shows after Try Another Number while a case is kept", not c3["hidden"] and c3["value"] == "", str(c3))
    await r.act("clearAll")
    await r.phone(); await r.act("goWpp", "wflight")
    ck("[guard] Home Clear drops the case kept by Try Another Number", await r.val("wFlight") == "", await r.val("wFlight"))


async def guard_s2_sec_rules_history_and_summary_order(r, name="s2_sec_rules_history_and_summary_order"):
    await to_s2(r, "callJoin", "407"); await r.act("cta", "msec")
    ck("[guard] Final Call Sec uses the TPE origin prefix", await r.pg.locator("#mSecPrefix").inner_text() == "TPE")
    await r.fill("mSec", "600"); await r.expect("Final Call SEC 600 rejected", False, ["mSec"])
    await r.fill("mSec", "580"); await r.expect("Final Call SEC 580 accepted", True, not_bad=["mSec"])
    await r.act("cta", "callgate"); ck("[guard] Sec survives Next Back/Forward", await r.val("mSec") == "580")
    await r.back("msec"); ck("[guard] Back returns to Sec with value", await r.val("mSec") == "580")
    await r.pg.go_forward(); await r.wait(lambda state: state["screen"] == "callgate")
    ck("[guard] Forward returns to Gate with Sec value", await r.val("mSec") == "580")
    await r.fill("callGate", "5"); await r.act("cta", "preview")
    labels = await r.pg.evaluate("[...document.querySelectorAll('#sum dt')].map(e => e.textContent.trim())")
    ck("[guard] Sec is directly above Go to Gate", labels.index("Go to Gate") == labels.index("Sec") + 1, str(labels))
    sec_value = await r.pg.locator("#sum dd").nth(labels.index("Sec")).inner_text()
    ck("[guard] Confirm details show TPE 580", sec_value.strip() == "TPE 580", sec_value)
    await r.back("callgate"); await r.back("msec"); await r.back("callflight"); await r.back("calltype")
    await r.act("callTransit", "callflight"); await r.fill("callFlight", "451"); await r.act("cta", "msec")
    ck("[guard] Transit Sec prefix is its departure airport", await r.pg.locator("#mSecPrefix").inner_text() == "NRT")


SUMMARY_ROWS_JS = "[...document.querySelectorAll('#sum > div')].map(d => [d.querySelector('dt').textContent.trim(), d.querySelector('dd').textContent.trim()])"

async def guard_s2_transit_confirm_shows_dep_from(r, name="s2_transit_confirm_shows_dep_from"):
    await to_s2_gate(r, "callTransit", "565"); await r.fill("callGate", "5"); await r.act("cta", "preview")
    rows = dict(await r.pg.evaluate(SUMMARY_ROWS_JS))
    want = COPY["rules.transit.origins"]["565"]
    ck("[guard] Final Call Transit Confirm details show Dep from", rows.get("Dep from") == want, f"want {want}, rows {rows}")

async def guard_direct_call_confirm_shows_grouped_phone(r, name="direct_call_confirm_shows_grouped_phone"):
    await r.phone(); await r.act("goDirect", "preview")
    rows = dict(await r.pg.evaluate(SUMMARY_ROWS_JS))
    ck("[guard] Call Directly shows the flag and grouped number", rows.get("Phone Number") == "\U0001F1F9\U0001F1FC +886 983 952 902", str(rows))


# Computed style of the first element matching a selector, plus its box.
STYLE_JS = """([sel, props]) => { const e = document.querySelector(sel); if (!e) return null; const c = getComputedStyle(e), b = e.getBoundingClientRect();
  return Object.assign(Object.fromEntries(props.map(p => [p, c[p]])), {left: b.left, top: b.top, width: b.width, height: b.height}); }"""
VAR_COLOUR_JS = "v => { const d = document.createElement('i'); d.style.color = 'var(' + v + ')'; document.body.appendChild(d); const c = getComputedStyle(d).color; d.remove(); return c; }"

async def style(r, sel, *props):
    return await r.pg.evaluate(STYLE_JS, [sel, list(props)]) or {}

async def guard_progress_title_style(r, name="progress_title_style"):
    await to_s1(r, "missJoin", "407")
    s = await style(r, "#step", "fontWeight", "fontSize")
    ck("[guard] progress title is bold 17px", s.get("fontWeight") == "700" and s.get("fontSize") == "17px", str(s))

async def guard_confirm_details_text_style(r, name="confirm_details_text_style"):
    await to_s2_gate(r, "callJoin", "407"); await r.fill("callGate", "5"); await r.act("cta", "preview")
    s = await style(r, ".msgToggle small", "fontSize", "fontWeight")
    ck("[guard] message language label is 15px semibold", s.get("fontSize") == "15px" and s.get("fontWeight") == "600", str(s))
    s = await style(r, "#sum dt", "wordBreak", "overflowWrap")
    ck("[guard] Confirm details labels never break inside a word", s.get("wordBreak") == "normal" and s.get("overflowWrap") == "normal", str(s))
    await _back_to_scenario(r); await r.act("goWpp", "wflight"); await r.fill("wFlight", "123"); await r.act("cta", "bag1")
    await r.fill("b1n", "123456"); await r.act("cta", "bag2"); await r.fill("b2n", "654321"); await r.act("cta", "preview")
    s = await style(r, "#sum .bagConfirmNote", "fontSize")
    ck("[guard] Wrong Pick-up unclaimed-bag note is 18px", s.get("fontSize") == "18px", str(s))

async def _back_to_scenario(r):
    for _ in range(8):
        s = await r.st()
        if s["screen"] == "scenario":
            return
        await r.pg.click("#back"); await r.wait(lambda x: x["screen"] != s["screen"])

async def guard_passenger_type_rows_full_width(r, name="passenger_type_rows_full_width"):
    await r.phone()
    for trig, scr, join, transit in (("goMiss", "misstype", "missJoin", "missTransit"), ("goCall", "calltype", "callJoin", "callTransit")):
        await r.act(trig, scr)
        a, b = await style(r, "#" + join), await style(r, "#" + transit)
        ck(f"[guard] {scr}: Transit Passenger spans the full row like Joining Passenger", abs(a.get("width", 0) - b.get("width", -9)) < 1, f"{a.get('width')} vs {b.get('width')}")
        await r.back("scenario")

async def guard_scenario_icons_size(r, name="scenario_icons_size"):
    await r.phone()
    boxes = await r.pg.evaluate("[...document.querySelectorAll('#s-scenario .ico img, #s-scenario .ico .scIco')].map(e => { const b = e.getBoundingClientRect(); return [Math.round(b.width), Math.round(b.height)]; })")
    ck("[guard] all five Scenario icons are 42 x 30", len(boxes) == 5 and all(b == [42, 30] for b in boxes), str(boxes))

async def guard_s2_flight_field_aligns_with_sec(r, name="s2_flight_field_aligns_with_sec"):
    await to_s2(r, "callJoin", "407")
    code, flight = await style(r, "#s-callflight .field .code"), await style(r, "#callFlight")
    await r.act("cta", "msec")
    prefix, sec = await style(r, "#mSecPrefix"), await style(r, "#mSec")
    ck("[guard] Final Call flight field lines up with the Sec field", abs(code.get("left", 0) - prefix.get("left", -9)) < 1 and abs(code.get("width", 0) - prefix.get("width", -9)) < 1
       and abs(flight.get("left", 0) - sec.get("left", -9)) < 1, f"code {code.get('left')}/{code.get('width')} prefix {prefix.get('left')}/{prefix.get('width')} input {flight.get('left')} vs {sec.get('left')}")


async def guard_phone_library_retries_after_bad_load(r, name="phone_library_retries_after_bad_load"):
    # The app is served over a test origin. The first download of the phone library arrives but
    # defines nothing (a broken or cut-off copy); the app must give up on it after its 2 s wait,
    # load the library again and then recognise a non-Taiwan number.
    origin, lib, asked = "http://findpax.test/", "libphonenumber-mobile.js", []
    async def serve(route):
        path = route.request.url[len(origin):].split("?")[0] or "index.html"
        if path == lib:
            asked.append(path)
            if len(asked) == 1:
                return await route.fulfill(status=200, content_type="text/javascript", body="/* cut-off copy */")
        f = R / path
        if not f.is_file():
            return await route.fulfill(status=404, body="")
        types = {".html": "text/html", ".js": "text/javascript", ".css": "text/css", ".png": "image/png", ".webmanifest": "application/manifest+json"}
        await route.fulfill(status=200, content_type=types.get(f.suffix, "application/octet-stream"), body=f.read_bytes())
    ctx = await r.browser.new_context(viewport={"width": 390, "height": 844}, service_workers="block")
    await ctx.route(origin + "**", serve); await ctx.route(COUNT_HOST + "**", lambda route: route.fulfill(status=204, body=""))
    pg = await ctx.new_page(); errors = []
    pg.on("pageerror", lambda e: errors.append(str(e)))
    await pg.goto(origin); await pg.wait_for_selector("#s-phone:not([hidden])")
    ready = False
    for _ in range(60):
        ready = await pg.evaluate("!!window.libphonenumber")
        if ready:
            break
        await pg.wait_for_timeout(100)
    ck("[guard] phone library is loaded again after a broken first copy", ready and len(asked) >= 2, f"ready {ready}, library requests {len(asked)}")
    await pg.fill("#phoneInput", PHONE_RETRY); await pg.wait_for_timeout(200)
    badge = (await pg.locator("#badge").inner_text()).strip() if await pg.locator("#badge").is_visible() else ""
    ck("[guard] after the retry a Japanese number shows the JP badge", "JP" in badge, badge)
    ck(f"[{name}] no JavaScript errors", not errors, "; ".join(errors[:3]))
    await ctx.close()


async def guard_s5_call_by_phone_after_whatsapp(r, name="s5_call_by_phone_after_whatsapp"):
    await case_s5(r, "ordZh")
    ck("[guard] S5 Call by Phone hidden until staff return from WhatsApp", await r.pg.locator("#callPhone").is_hidden())
    await r.pg.evaluate("""() => {
        const setHidden = h => Object.defineProperty(document, 'hidden', {configurable: true, get: () => h});
        setHidden(true); document.dispatchEvent(new Event('visibilitychange'));
        setHidden(false); document.dispatchEvent(new Event('visibilitychange'));
    }""")
    await settle(r.pg)
    ck("[guard] S5 return shows Try Another Number", (await r.pg.locator("#cta").inner_text()).strip() == "Try Another Number")
    ck("[guard] S5 Call by Phone shown after return", await r.pg.locator("#callPhone").is_visible())
    ck("[guard] S5 Call by Phone label", (await r.pg.locator("#callPhone").inner_text()).strip() == "Call by Phone")
    ck("[guard] S5 Call by Phone has a phone icon", await r.pg.locator("#callPhone svg").count() == 1)
    a = await r.pg.locator("#callPhone").bounding_box(); b = await r.pg.locator("#cta").bounding_box()
    ck("[guard] S5 Call by Phone sits above Try Another Number", bool(a and b) and a["y"] + a["height"] <= b["y"], f"{a} {b}")
    await tap_call_by_phone(r, "S5", "")

async def guard_direct_call_by_phone_after_whatsapp(r, name="direct_call_by_phone_after_whatsapp"):
    await case_direct(r)
    ck("[guard] Call Directly: Call by Phone hidden until staff return from WhatsApp", await r.pg.locator("#callPhone").is_hidden())
    await return_from_app(r)
    ck("[guard] Call Directly return shows Try Another Number", (await r.pg.locator("#cta").inner_text()).strip() == "Try Another Number")
    ck("[guard] Call Directly: Call by Phone shown after return", await r.pg.locator("#callPhone").is_visible())
    a = await r.pg.locator("#callPhone").bounding_box(); b = await r.pg.locator("#cta").bounding_box()
    ck("[guard] Call Directly: Call by Phone sits above Try Another Number", bool(a and b) and a["y"] + a["height"] <= b["y"], f"{a} {b}")
    await tap_call_by_phone(r, "Call Directly:", "S3-Call by phone")

async def guard_s1_call_by_phone_after_whatsapp(r, name="s1_call_by_phone_after_whatsapp"):
    await to_s1(r, "missJoin", "450"); await r.act("cta", "msec"); await r.fill("mSec", "12"); await r.act("cta", "preview")
    await r.act("ordEn")
    ck("[guard] 漏查 Call by Phone hidden until staff return", await r.pg.locator("#callPhone").is_hidden())
    await r.act("cta", "external:whatsapp"); await call_by_phone_return(r, "漏查", True, "S1-Call by phone")

async def guard_s2_call_by_phone_after_sms(r, name="s2_call_by_phone_after_sms"):
    await case_s2(r, "callTransit", "451", "ordJa")
    await call_by_phone_return(r, "Final Call Japanese SMS", True, "S2-Call by phone")

async def guard_try_another_number_keeps_case(r, name="try_another_number_keeps_case"):
    await case_s5(r, "ordZh")
    await return_from_app(r)
    await r.pg.click("#cta"); s_ = await r.wait(lambda s: s["screen"] == "phone")
    ck("[guard] Try Another Number returns to the phone page", s_["screen"] == "phone", s_["screen"])
    sel = await r.pg.evaluate("(() => { const e = document.getElementById('phoneInput'); return [document.activeElement === e, e.value, document.getElementById('badge').hidden]; })()")
    ck("[guard] Try Another Number empties the number field and focuses it", sel == [True, "", True], str(sel))
    await r.expect("empty number keeps Next disabled", cta_enabled=False)
    await r.fill("phoneInput", PHONE_RETRY); await r.act("cta", "scenario"); await r.act("goWpp", "wflight")
    ck("[guard] Try Another Number keeps the Wrong Pick-up fields", [await r.val(x) for x in ("wFlight", "b1n", "b2a", "b2n")] == ["123", "123456", "BR", "654321"])
    await r.act("cta", "bag1"); await r.act("cta", "bag2"); s_ = await r.act("cta", "preview")
    ck("[guard] Retry language default follows the new number (Japan on Wrong Pick-up: English)", "ordEn" in s_["pressed"] and "ordZh" not in s_["pressed"], str(s_["pressed"]))
    n0 = len(r.nav); await r.pg.click("#cta")
    for _ in range(40):
        if len(r.nav) > n0: break
        await r.pg.wait_for_timeout(50)
    url = urllib.parse.unquote(r.nav[n0]) if len(r.nav) > n0 else ""
    ck("[guard] Retry sends to the new number with the kept case", PHONE_RETRY in url and PHONE not in url and "BR654321" in url, url[:90])

async def guard_edited_field_after_back_starts_from_send(r, name="edited_field_after_back_starts_from_send"):
    await case_s5(r, "ordZh")
    await return_from_app(r)
    await r.back("bag2"); await r.act("cta", "preview")
    ck("[guard] Back and Next without edits keeps Call by Phone and Try Another Number", (await r.pg.locator("#cta").inner_text()).strip() == "Try Another Number" and await r.pg.locator("#callPhone").is_visible())
    await r.back("bag2"); await r.fill("b2n", "654322"); await r.act("cta", "preview")
    ck("[guard] Edited field after Back shows only Send on WhatsApp", (await r.pg.locator("#cta").inner_text()).strip() == "Send on WhatsApp" and await r.pg.locator("#callPhone").is_hidden())
    await r.act("cta", "external:whatsapp", ("BR654322",))

async def guard_new_number_after_back_starts_from_send(r, name="new_number_after_back_starts_from_send"):
    await case_s5(r, "ordZh")
    await return_from_app(r)
    for to in ("bag2", "bag1", "wflight", "scenario", "phone"): await r.back(to)
    await r.phone(PHONE_RETRY); await r.act("goWpp", "wflight"); await r.fill("wFlight", "123"); await r.act("cta", "bag1")
    await r.fill("b1n", "123456"); await r.act("cta", "bag2"); await r.fill("b2a", "BR"); await r.fill("b2n", "654321"); await r.act("cta", "preview")
    ck("[guard] New number after Back shows only Send on WhatsApp", (await r.pg.locator("#cta").inner_text()).strip() == "Send on WhatsApp" and await r.pg.locator("#callPhone").is_hidden())

async def guard_try_another_number_language_follows_new_number(r, name="try_another_number_language_follows_new_number"):
    await to_s1(r, "missJoin", "450"); await r.act("cta", "msec"); await r.fill("mSec", "12"); s_ = await r.act("cta", "preview")
    ck("[guard] Taiwan number defaults to 中文 on 漏查", "ordZh" in s_["pressed"], str(s_["pressed"]))
    await r.act("cta", "external:whatsapp")
    await return_from_app(r)
    await r.pg.click("#cta"); await r.wait(lambda s: s["screen"] == "phone")
    await r.phone(PHONE_RETRY); await r.act("goMiss", "misstype"); await r.act("missJoin", "mflight")
    ck("[guard] Retry keeps 漏查 flight", await r.val("mFlight") == "450", await r.val("mFlight"))
    await r.act("cta", "msec"); ck("[guard] Retry keeps 漏查 SEC", await r.val("mSec") == "12", await r.val("mSec"))
    s_ = await r.act("cta", "preview")
    ck("[guard] Retry with a Japanese number defaults to 日本語 on 漏查", "ordJa" in s_["pressed"], str(s_["pressed"]))

async def guard_s2_transit_ja_all_flights(r, name="s2_transit_ja_all_flights"):
    # Every transit flight gets the right origin/destination and stays within 2 SMS, using the longest
    # supported gate form (B1R); Join with B1R stays within one SMS. One real Japanese SMS send (CX451),
    # then every flight through the test probe, which builds the message with the app's own code.
    await to_s2_gate(r, "callTransit", "451")
    await r.fill("callGateZone", "B"); await r.fill("callGate", "1R"); await r.act("cta", "preview")
    await r.act("ordJa"); await r.act("cta", "external:sms", exact=ja_expected("s2", "transit", "CX451", "B1R"))
    qs = [(f"CX{f}", "transit", f) for f in ("450", "451", "530", "531", "564", "565")] + [("Join B1R", "join", "407")]
    ans = await probe_all(r.pg, "message", [{"flow": "call", "fields": {"callFlight": f, "mSec": "123", "callGateZone": "B", "callGate": "1R"},
                                             "state": {"callMode": m, "order": "ja"}} for _, m, f in qs])
    for (tag, m, f), a in zip(qs, ans):
        rx, limit = ja_expected("s2", m, "CX" + f, "B1R")
        ck(f"[{name} {tag}] message text is exactly the locked copy (rule)", re.fullmatch(rx, a["text"]) is not None, a["text"][:160])
        ck(f"[{name} {tag}] message fits {limit} chars ({'1' if limit == 67 else '2'} SMS) (rule)", len(a["text"]) <= limit, f"{len(a['text'])} chars")


async def guard_layout_does_not_jump(r, name="layout_does_not_jump"):
    # Keyboard open/close must not move or resize the title and fields. Home keeps
    # only the top safe area; other pages keep equal header heights. Keyboard mode uses the
    # same .kb class the app applies when the on-screen keyboard is up.
    M = """() => { const s = document.querySelector('.screen:not([hidden])'); const h = s.querySelector('h1');
      const f = s.querySelector('.field'); const r = e => e ? Math.round(e.getBoundingClientRect().top) : null;
      const probe = document.createElement('div');
      probe.style.cssText = 'position:fixed;visibility:hidden;padding-top:env(safe-area-inset-top,0px)';
      document.body.appendChild(probe);
      const safeTop = Math.round(parseFloat(getComputedStyle(probe).paddingTop) || 0); probe.remove();
      return [s.id, r(h), h ? getComputedStyle(h).fontSize : '', r(f), f ? Math.round(f.getBoundingClientRect().height) : null,
              Math.round(document.querySelector('.head').getBoundingClientRect().height), safeTop]; }"""
    K = "on => { const a = document.getElementById('app'); a.classList.toggle('kb', on); a.style.setProperty('--vh', on ? '470px' : '100%'); }"
    # Switch and measure in one evaluate, so the app's own viewport sync (a 180 ms timer) cannot run in between.
    PROBE = "() => { const m = (" + M + "), k = (" + K + "); const n = m(); k(true); const kb = m(); k(false); return [n, kb]; }"
    heads, home_heads, jumps, header_jumps = set(), [], [], []
    async def probe():
        n, k = await r.pg.evaluate(PROBE)
        if n[0] == "s-phone":
            home_heads.extend([(n[5], n[6]), (k[5], k[6])])
        else:
            heads.add(n[5]); heads.add(k[5])
        if abs(n[5] - k[5]) > 1: header_jumps.append(f"{n[0]}: {n[5]} -> {k[5]}")
        if n[1:5] != k[1:5]: jumps.append(f"{n[0]}: {n[1:5]} -> {k[1:5]}")
    await probe()
    # Home content only overflows while the keyboard is open.
    home_scroll = await r.pg.evaluate("""() => {
      const app = document.getElementById('app'); app.classList.add('kb'); app.style.setProperty('--vh', '470px');
      const main = document.querySelector('#main'), screen = document.querySelector('#s-phone');
      const before = screen.getBoundingClientRect().top;
      const canScroll = main.scrollHeight > main.clientHeight + 1;
      main.scrollTo(0, Math.min(120, main.scrollHeight));
      const after = screen.getBoundingClientRect().top;
      const moved = main.scrollTop > 0 && after < before - 1;
      main.scrollTo(0, 0); app.classList.remove('kb'); app.style.setProperty('--vh', '100%');
      return {canScroll, moved, before: Math.round(before), after: Math.round(after)};
    }""")
    ck("[guard] home content keeps its initial top spacing", home_scroll["before"] >= 0, str(home_scroll))
    ck("[guard] home content scrolls instead of being covered by a fixed blank block", home_scroll["canScroll"] and home_scroll["moved"], str(home_scroll))
    await r.phone(); await r.act("goDp", "dstatus"); await r.act("stDelayed", "dflight"); await probe()
    await r.fill("dFlight", "407"); await r.fill("delayTime", "1800"); await r.act("cta", "dtransfer"); await probe()
    await r.fill("tN", "888"); await r.act("cta", "darrange"); await r.act("arKnown"); await r.pg.wait_for_timeout(350); await probe()
    await r.fill("altN", "401"); await r.fill("altTime", "1530"); await r.act("cta", "darrive"); await probe()
    ck("[guard] title and fields do not move or resize when the keyboard opens", not jumps, "; ".join(jumps))
    ck("[guard] home header contains only the top safe area", bool(home_heads) and all(abs(height - safe) <= 1 for height, safe in home_heads), str(home_heads))
    ck("[guard] non-home header heights remain equal and nonzero", bool(heads) and min(heads) > 0 and max(heads) - min(heads) <= 1, str(sorted(heads)))
    ck("[guard] header height stays stable when the keyboard opens", not header_jumps, "; ".join(header_jumps))

async def guard_partial_flight_not_red_while_typing(r, name="partial_flight_not_red_while_typing"):
    await to_s4(r, "stPossible", "4"); await r.expect("CX4 (could become 407) neutral", False, not_bad=["dFlight"])
    await r.fill("dFlight", "40"); await r.expect("CX40 (could become 407) neutral", False, not_bad=["dFlight"])
    await r.blur("dFlight"); await r.expect("CX40 red after leaving the field", False, ["dFlight"])

async def guard_impossible_prefix_red_immediately(r, name="impossible_prefix_red_immediately"):
    await to_s4(r, "stPossible", "8"); await r.expect("CX8 (no allowed flight starts with 8) red at once", False, ["dFlight"])
    rr = await Run(r.browser, name + " S1 transit").open()
    await to_s1(rr, "missTransit", "45"); await rr.expect("S1 Transit CX45 neutral while typing", False, not_bad=["mFlight"])
    await rr.fill("mFlight", "47"); await rr.expect("S1 Transit CX47 red at once", False, ["mFlight"]); await rr.close()

async def guard_s1_join_short_message(r, name="s1_join_short_message"):
    await to_s1(r, "missJoin", "450"); await r.act("cta", "msec"); await r.fill("mSec", "12"); await r.act("cta", "preview")
    msg = await r.pg.locator("#msg").input_value()
    ck("[guard] S1 Join uses the short message", "4 號櫃位" in msg and "Counter 4" in msg and "尚未進入離境禁區" not in msg and msg.endswith("450/012"), msg[-60:])
    ck("[guard] S1 Join has no Msg length control", await r.pg.locator("#previewLenSeg").count() == 0)

async def guard_s1_s2_language_pick_keeps_button_order(r, name="s1_s2_language_pick_keeps_button_order"):
    order_js = "() => ['ordZh','ordEn','ordJa'].filter(id => !document.getElementById(id).hidden).sort((a, b) => Number(getComputedStyle(document.getElementById(a)).order) - Number(getComputedStyle(document.getElementById(b)).order))"
    await to_s1(r, "missJoin", "450"); await r.act("cta", "msec"); await r.fill("mSec", "12"); await r.act("cta", "preview")
    start = await r.pg.evaluate(order_js)
    ck("[guard] S1 Taiwan phone puts 中文 first", start[0] == "ordZh", str(start))
    for lang in ("ordEn", "ordJa", "ordZh"):
        await r.act(lang)
        now = await r.pg.evaluate(order_js)
        ck(f"[guard] S1 picking {lang} keeps the button order", now == start, str(now))
        ck(f"[guard] S1 {lang} is selected", await r.pg.locator("#" + lang).get_attribute("aria-pressed") == "true")
    await r.back("msec"); await r.back("mflight"); await r.back("misstype"); await r.back("scenario")
    await r.act("goCall", "calltype"); await r.act("callJoin", "callflight"); await r.fill("callFlight", "407"); await r.act("cta", "msec")
    await r.fill("mSec", "12"); await r.act("cta", "callgate"); await r.fill("callGate", "5"); await r.act("cta", "preview")
    start = await r.pg.evaluate(order_js)
    await r.act("ordEn"); now = await r.pg.evaluate(order_js)
    ck("[guard] S2 picking English keeps the button order", now == start and start[0] == "ordZh", f"{start} -> {now}")

async def guard_header_number_on_passenger_type(r, name="header_number_on_passenger_type"):
    who_js = "() => [!document.getElementById('who').hidden, document.getElementById('whoNum').textContent.replace(/ /g, '')]"
    await r.phone()
    for trig, scr in (("goMiss", "misstype"), ("goCall", "calltype"), ("goDp", "dstatus")):
        await r.act(trig, scr)
        shown, num = await r.pg.evaluate(who_js)
        ck(f"[guard] {scr} shows the phone number top-right", shown and num == "+" + PHONE, num)
        s = await style(r, "#who", "color", "fontWeight", "fontSize", "backgroundColor")
        want = await r.pg.evaluate(VAR_COLOUR_JS, "--muted")
        ck(f"[guard] {scr} header number is muted grey 15px weight 500, no background",
           s.get("color") == want and s.get("fontWeight") == "500" and s.get("fontSize") == "15px" and s.get("backgroundColor") == "rgba(0, 0, 0, 0)", str(s))
        await r.back("scenario")
    await r.act("goDirect", "preview")
    shown, num = await r.pg.evaluate(who_js)
    ck("[guard] Call Directly Confirm details shows the number in the header Home capsule", shown and num == "+" + PHONE, num)

async def guard_phone_input_fits(r, name="phone_input_fits"):
    fit_js = "() => { const e = document.getElementById('phoneInput'), b = document.getElementById('badge'); return [e.scrollWidth <= e.clientWidth + 1, parseFloat(getComputedStyle(e).fontSize), !b.hidden, b.textContent]; }"
    for W in (390, 360, 320):
        await r.pg.set_viewport_size({"width": W, "height": 844}); await r.pg.wait_for_timeout(150)
        for num, cc in (("8613812345678", "CN"), ("4915123456789", "DE"), ("6281234567890", "ID")):
            await r.fill("phoneInput", num); await r.pg.wait_for_timeout(100)
            fits, fs, shown, label = await r.pg.evaluate(fit_js)
            ck(f"[guard] {W}px: +{num} fits the phone field", fits and fs >= 16 and shown and label.startswith(chr(127397 + ord(cc[0]))), f"fits={fits} font={fs} badge={label!r}")
    await r.pg.set_viewport_size({"width": 390, "height": 844}); await r.pg.wait_for_timeout(150)
    await r.fill("phoneInput", "8613812345678"); await r.pg.wait_for_timeout(100)
    _, _, _, label = await r.pg.evaluate(fit_js)
    ck("[guard] 390px: badge keeps the country letters", label.endswith("CN"), label)
    await r.fill("phoneInput", "85291234567"); await r.pg.wait_for_timeout(100)
    _, fs, _, _ = await r.pg.evaluate(fit_js)
    ck("[guard] 390px: a shorter number returns to the full 24px size", fs == 24, str(fs))

async def guard_phone_formats_normalize(r, name="phone_formats_normalize"):
    state_js = "() => [document.getElementById('cta').disabled, document.getElementById('phoneField').classList.contains('bad'), document.getElementById('warn').classList.contains('show')]"
    for raw, want in (("886983952902", "+886 983 952 902"), ("8860983952902", "+886 983 952 902"), ("886000983952902", "+886 983 952 902"),
                      ("00886983952902", "+886 983 952 902"), ("008860983952902", "+886 983 952 902"),
                      ("\uff18\uff18\uff16\uff10\uff19\uff18\uff13\uff19\uff15\uff12\uff19\uff10\uff12", "+886 983 952 902"),
                      ("0086013812345678", "+86 138 1234 5678"), ("008109012345678", "+81 90 1234 5678")):
        await r.fill("phoneInput", raw)
        await r.act("cta", "scenario")
        who = await r.pg.locator("#whoNum").inner_text()
        ck(f"[guard] {raw!r} reaches {want}", who == want, who)
        await r.back("phone")
    for raw in ("0", "00"):
        await r.fill("phoneInput", raw)
        dis, bad, _ = await r.pg.evaluate(state_js)
        ck(f"[guard] {raw!r} stays neutral while a 00 prefix is typed", dis and not bad)
    await r.fill("phoneInput", "0085289648964")
    dis, bad, warn = await r.pg.evaluate(state_js)
    ck("[guard] a canned number behind 00 is still blocked", dis and bad and warn)

async def guard_progress_title_fits(r, name="progress_title_fits"):
    # A Range measures the label text exactly; scrollWidth rounds away the sub-pixel overflow that still shows an ellipsis.
    fit_js = "() => { const e = document.getElementById('step'), l = e.querySelector('.progressLabel'); if (!l) return [false, 0, e.textContent]; const g = document.createRange(); g.selectNodeContents(l); return [g.getBoundingClientRect().width <= l.getBoundingClientRect().width + 0.01 && e.scrollWidth <= e.clientWidth + 0.5, parseFloat(getComputedStyle(e).fontSize), e.textContent]; }"
    async def check():
        for W in (390, 360, 320):
            await r.pg.set_viewport_size({"width": W, "height": 844}); await r.pg.wait_for_timeout(150)
            fits, fs, text = await r.pg.evaluate(fit_js)
            ck(f"[guard] {W}px: progress title fits without an ellipsis ({text})", fits and fs >= 13, f"font={fs}")
    await r.phone(); await r.act("goDp", "dstatus")
    for st in ("stPossible", "stDelayed", "stUnknown", "stGate"):
        await r.act(st, "dflight"); await check(); await r.back("dstatus")
    await r.back("scenario"); await r.act("goCall", "calltype"); await r.act("callTransit", "callflight"); await check()

HOME_BTN_JS = "(() => { const b = document.getElementById('homeBtn'), r = b.getBoundingClientRect(), e = document.getElementById('phoneInput'); return {shown: !b.hidden && b.offsetParent !== null && r.width > 0 && r.top >= 0 && r.bottom <= innerHeight, text: b.getAttribute('aria-label') || '', value: e.value, focused: document.activeElement === e, clear: document.getElementById('clearAll').hidden}; })()"


async def _home_from(r, label, screen):
    s_ = await r.st()
    h = await r.pg.evaluate(HOME_BTN_JS)
    ck(f"[guard] Home shown on {label}", s_["screen"] == screen and h["shown"] and h["text"] == "Home", f"{s_['screen']} {h}")
    await r.pg.click("#homeBtn")
    s_ = await r.wait(lambda x: x["screen"] == "phone")
    h = await r.pg.evaluate(HOME_BTN_JS)
    ck(f"[guard] Home from {label} opens an empty phone page", s_["screen"] == "phone" and h["value"] == "" and h["focused"] and h["clear"], f"{s_['screen']} {h}")
    await home_done(r.pg)


async def guard_home_button_returns_home_without_number(r, name="home_button_returns_home_without_number"):
    h = await r.pg.evaluate(HOME_BTN_JS)
    ck("[guard] Home hidden on the phone page", not h["shown"], str(h))
    await r.phone()
    await r.pg.set_viewport_size({"width": 320, "height": 640}); await r.pg.wait_for_timeout(150)
    fit = await r.pg.evaluate("(() => { const g = id => document.getElementById(id).getBoundingClientRect(), w = document.getElementById('who'), b = g('back'), h = g('homeBtn'), n = g('who'); return {backOneLine: b.height <= 50, numberFits: w.scrollWidth <= w.clientWidth + 1 && n.left >= h.left && n.right <= h.right, homeInside: h.left >= b.right && h.right <= innerWidth}; })()")
    ck("[guard] Home icon, Back and the number fit the header at 320 px", all(fit.values()), str(fit))
    await r.pg.click("#whoNum"); s_ = await r.wait(lambda x: x["screen"] == "phone")
    ck("[guard] Tapping the number in the Home capsule also goes Home", s_["screen"] == "phone" and await r.val("phoneInput") == "", s_["screen"])
    await home_done(r.pg); await r.phone()
    await r.pg.set_viewport_size({"width": 390, "height": 844}); await r.pg.wait_for_timeout(150)
    # The Home capsule is one shared header control: one page per kind (choice, field, Confirm details, branch) is enough.
    await _home_from(r, "Scenario", "scenario")
    await to_s1(r, "missJoin", "407"); await r.act("cta", "msec"); await r.fill("mSec", "123"); await _home_from(r, "S1 Sec", "msec")
    await to_s2_gate(r, "callJoin", "407"); await r.fill("callGate", "5"); await r.act("cta", "preview"); await _home_from(r, "S2 Confirm details", "preview")
    await r.phone(); await r.act("goDirect", "preview"); await _home_from(r, "S3 Confirm details", "preview")
    await to_s4_gate(r, "407", "gsCancelled"); await fill_protect(r); await _home_from(r, "S4 Protect to", "dnew")
    await r.phone(); await r.act("goWpp", "wflight"); await r.fill("wFlight", "123"); await r.act("cta", "bag1"); await r.fill("b1n", "123456"); await r.act("cta", "bag2"); await _home_from(r, "S5 Bag 2", "bag2")
    await r.phone(); await r.act("goWpp", "wflight")
    ck("[guard] Home drops the case (S5 flight empty)", await r.val("wFlight") == "", await r.val("wFlight"))
    await r.pg.click("#homeBtn"); await r.wait(lambda x: x["screen"] == "phone"); await home_done(r.pg)
    await r.phone(); await r.act("goDp", "dstatus"); await r.act("stPossible", "dflight")
    ck("[guard] Home drops the case (S4 flight empty)", await r.val("dFlight") == "", await r.val("dFlight"))
    await r.pg.click("#homeBtn"); await r.wait(lambda x: x["screen"] == "phone"); await home_done(r.pg)
    names = count_names(r.counts)
    ck("[guard] Home sends no usage count (only home Next counts)", set(names) == {"next"}, str(names))
    await case_s5(r, "ordZh")
    await return_from_app(r)
    await _home_from(r, "Confirm details after return", "preview")


CASE_TEXT_FIELDS = ["mFlight", "mSec", "callFlight", "callGate", "wFlight", "b1n", "b2n",
                    "dFlight", "tN", "delayTime", "altN", "altTime", "arriveTime"]
SCENARIO_FIELDS = {"miss": ["mFlight", "mSec"], "call": ["callFlight", "mSec", "callGate"],
                   "wpp": ["wFlight", "b1n", "b2n"],
                   "dp": ["dFlight", "tN", "delayTime", "altN", "altTime", "arriveTime"]}
SCENARIO_PICK = {"miss": ("goMiss", "misstype"), "call": ("goCall", "calltype"), "wpp": ("goWpp", "wflight"),
                 "dp": ("goDp", "dstatus"), "direct": ("goDirect", "preview")}


async def _pick_matrix(r, xs):
    """Fields of the scenarios in xs and the message, set on their own page, are cleared by every scenario pick."""
    await r.phone()
    for x in xs:
        ids = SCENARIO_FIELDS[x]
        for y, (btn, first) in SCENARIO_PICK.items():
            await r.pg.click("#" + SCENARIO_PICK[x][0]); await r.wait(lambda s: s["screen"] == SCENARIO_PICK[x][1])
            await r.pg.evaluate("ids => { ids.forEach(i => { const e = document.getElementById(i); e.value = '999'; e.dispatchEvent(new Event('input', {bubbles: true})); }); document.getElementById('msg').value = 'old 999'; }", ids)
            await r.pg.click("#back"); await r.wait(lambda s: s["screen"] == "scenario")
            await r.pg.click("#" + btn); await r.wait(lambda s, f=first: s["screen"] == f)
            left = await r.pg.evaluate("ids => ids.filter(i => document.getElementById(i).value !== '')", CASE_TEXT_FIELDS)
            msg = await r.pg.evaluate("document.getElementById('msg').value")
            ck(f"[guard] {x} -> {y}: picking a scenario clears every case field and the message", not left and "999" not in msg, f"{left} {msg[:40]!r}")
            await r.pg.click("#back"); await r.wait(lambda s: s["screen"] == "scenario")

async def _reentry_some(r, tags):
    """Re-entering a scenario after a full typed case: empty fields, no stale red border, default language again.
    S2 runs on the same page right after S1, so the Sec typed in S1 must not reach S2 either."""
    for tag, num, steps, stale in REENTRY:
        if tag in tags:
            await _reentry(r, tag, num, steps, stale)

async def _pick_after_retry(r):
    """After Try Another Number, picking another scenario drops the kept case."""
    await _back_to(r, "phone")
    await case_s5(r, "ordZh")
    await return_from_app(r)
    await r.pg.click("#cta"); await r.wait(lambda s: s["screen"] == "phone")
    await r.phone(); await r.act("goDp", "dstatus"); await r.back("scenario"); await r.act("goWpp", "wflight")
    ck("[guard] Picking another scenario after Try Another Number clears the kept case", await r.val("wFlight") == "", await r.val("wFlight"))

# The guard in parts that need no shared page, so the plan can run them at the same time (vb_priority.py).
SCENARIO_PICK_PARTS = {
    "S1 S2 fields": lambda r: _pick_matrix(r, ["miss", "call"]),
    "S5 S4 fields": lambda r: _pick_matrix(r, ["wpp", "dp"]),
    "re-entry S1 S2": lambda r: _reentry_some(r, ("S1", "S2")),
    "re-entry S4 S5": lambda r: _reentry_some(r, ("S4", "S5")),
    "after Try Another Number": _pick_after_retry,
}

async def guard_scenario_pick_clears_every_case(r, name="scenario_pick_clears_every_case", part=None):
    # Every scenario's fields and the message are cleared by every scenario pick (20 switches), re-entry
    # starts clean, and a pick after Try Another Number drops the kept case. part runs one piece only.
    for key, fn in SCENARIO_PICK_PARTS.items():
        if part in (None, key):
            await fn(r)

# Re-entering a scenario from the Scenario page starts a clean case: empty fields, no stale red
# border and the phone-based default language again. Each walk fills a case to Confirm details,
# picks the other language, leaves one invalid field (red; S5 has no field that turns red), goes back
# to the Scenario page and walks the same steps again. Steps: ("act", control, screen) or ("fill", field, value).
# Each number's default language differs from the language the scenario button starts with (S1/S2/S5 中文,
# S4 English), so a picked language that survives re-entry is visible.
REENTRY = [
    ("S1", PHONE_RETRY, [("act", "goMiss", "misstype"), ("act", "missJoin", "mflight"), ("fill", "mFlight", "407"), ("act", "cta", "msec"),
            ("fill", "mSec", "123"), ("act", "cta", "preview")], ("msec", "mSec", "999")),
    ("S2", PHONE_RETRY, [("act", "goCall", "calltype"), ("act", "callJoin", "callflight"), ("fill", "callFlight", "407"), ("act", "cta", "msec"),
            ("fill", "mSec", "123"), ("act", "cta", "callgate"), ("fill", "callGate", "5"), ("act", "cta", "preview")], ("msec", "mSec", "999")),
    ("S4", PHONE, [("act", "goDp", "dstatus"), ("act", "stPossible", "dflight"), ("fill", "dFlight", "407"), ("act", "cta", "dtransfer"),
            ("fill", "tN", "888"), ("act", "cta", "darrange"), ("act", "arUnknown", None), ("act", "cta", "darrive"),
            ("fill", "arriveTime", "1400"), ("act", "cta", "preview")], ("dflight", "dFlight", "450")),
    ("S5", PHONE_RETRY, [("act", "goWpp", "wflight"), ("fill", "wFlight", "123"), ("act", "cta", "bag1"), ("fill", "b1n", "123456"),
            ("act", "cta", "bag2"), ("fill", "b2n", "654321"), ("act", "cta", "preview")], None),
]

async def _back_to(r, screen):
    for _ in range(8):
        s = await r.st()
        if s["screen"] == screen:
            return True
        await r.pg.click("#back"); await r.wait(lambda x: x["screen"] != s["screen"])
    return False

async def _walk(r, steps):
    dirty = []
    for kind, a, b in steps:
        if kind == "act":
            await r.act(a, b)
            continue
        if await r.val(a) or a in (await r.st())["bad"]:
            dirty.append(f"{a}={await r.val(a)!r}")
        await r.fill(a, b)
    return dirty

async def _reentry(r, tag, num, steps, stale):
    await _back_to(r, "phone"); await r.phone(num)
    await _walk(r, steps)
    lang = [b for b in (await r.st())["pressed"] if b.startswith("ord")]
    await r.act("ordZh" if lang == ["ordEn"] else "ordEn")
    if stale:
        screen, field, bad_value = stale
        await _back_to(r, screen); await r.fill(field, bad_value); await r.blur(field)
        ck(f"[guard] {tag} setup: {field}={bad_value} shows a red border", field in (await r.st())["bad"])
    ck(f"[guard] {tag} setup: Back reaches the Scenario page", await _back_to(r, "scenario"))
    dirty = await _walk(r, steps)
    ck(f"[guard] {tag} re-entry starts with empty fields and no red border", not dirty, ", ".join(dirty))
    again = [b for b in (await r.st())["pressed"] if b.startswith("ord")]
    ck(f"[guard] {tag} re-entry restores the default language", again == lang, f"first {lang}, again {again}")


# Guards the plan may run as separate parts at the same time: name -> part keys of guard(r, part=key).
GUARD_PARTS = {"scenario_pick_clears_every_case": list(SCENARIO_PICK_PARTS)}

GUARDS = {
    "home_clear_resets_number_and_kept_case": guard_home_clear_resets_number_and_kept_case,
    "s2_sec_rules_history_and_summary_order": guard_s2_sec_rules_history_and_summary_order,
    "s5_call_by_phone_after_whatsapp": guard_s5_call_by_phone_after_whatsapp,
    "direct_call_by_phone_after_whatsapp": guard_direct_call_by_phone_after_whatsapp,
    "s1_call_by_phone_after_whatsapp": guard_s1_call_by_phone_after_whatsapp,
    "s2_call_by_phone_after_sms": guard_s2_call_by_phone_after_sms,
    "try_another_number_keeps_case": guard_try_another_number_keeps_case,
    "edited_field_after_back_starts_from_send": guard_edited_field_after_back_starts_from_send,
    "new_number_after_back_starts_from_send": guard_new_number_after_back_starts_from_send,
    "try_another_number_language_follows_new_number": guard_try_another_number_language_follows_new_number,
    "s2_transit_ja_all_flights": guard_s2_transit_ja_all_flights,
    "layout_does_not_jump": guard_layout_does_not_jump,
    "partial_flight_not_red_while_typing": guard_partial_flight_not_red_while_typing,
    "impossible_prefix_red_immediately": guard_impossible_prefix_red_immediately,
    "s1_join_short_message": guard_s1_join_short_message,
    "s1_s2_language_pick_keeps_button_order": guard_s1_s2_language_pick_keeps_button_order,
    "header_number_on_passenger_type": guard_header_number_on_passenger_type,
    "phone_input_fits": guard_phone_input_fits,
    "phone_formats_normalize": guard_phone_formats_normalize,
    "progress_title_fits": guard_progress_title_fits,
    "s2_transit_confirm_shows_dep_from": guard_s2_transit_confirm_shows_dep_from,
    "direct_call_confirm_shows_grouped_phone": guard_direct_call_confirm_shows_grouped_phone,
    "progress_title_style": guard_progress_title_style,
    "confirm_details_text_style": guard_confirm_details_text_style,
    "passenger_type_rows_full_width": guard_passenger_type_rows_full_width,
    "scenario_icons_size": guard_scenario_icons_size,
    "s2_flight_field_aligns_with_sec": guard_s2_flight_field_aligns_with_sec,
    "phone_library_retries_after_bad_load": guard_phone_library_retries_after_bad_load,
    "home_button_returns_home_without_number": guard_home_button_returns_home_without_number,
    "scenario_pick_clears_every_case": guard_scenario_pick_clears_every_case,
}
