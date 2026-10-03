"""Full happy-path flows for every scenario and language (CASES)."""
import vb_core
globals().update({k: v for k, v in vars(vb_core).items() if not k.startswith("__")})


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

def ck_send_count(r, want):
    """A send tap sends exactly the expected usage count (S1-S3), or none (S4, S5)."""
    ck(f"[{r.name}] send usage count is {want or 'none'}", r.send_counts == ([want] if want else []), str(r.send_counts))

async def ck_msg_order(r, lang):
    """中文在前 starts the message with Chinese, English first with English (Japanese is SMS only)."""
    if lang == "ordJa":
        return
    msg = (await r.pg.locator("#msg").input_value()).lstrip()
    zh = bool(msg) and re.match(r"[\u3400-\u9fff\u3000-\u303f\uff00-\uffef]", msg) is not None
    ck(f"[{r.name}] message starts with {'中文' if lang == 'ordZh' else 'English'}", bool(msg) and zh == (lang == "ordZh"), msg[:40])

# ---- forward branch cases ----------------------------------------------------
async def case_s1(r, mode, flight, lang):
    await to_s1(r, mode, flight); await r.act("cta", "msec")
    await r.fill("mSec", "123"); await r.act("cta", "preview")
    if lang != "ordZh": await r.act(lang)
    # Join copy carries the bag tag "flight/SEC"; approved Transit copy carries no typed values.
    # (the approved Japanese SMS copy has no tag either).
    has = (f"{flight}/123",) if mode == "missJoin" and lang != "ordJa" else ()
    exact = ja_expected("s1", "join" if mode == "missJoin" else "transit") if lang == "ordJa" else None
    await ck_msg_order(r, lang)
    await r.act("cta", "external:sms" if lang == "ordJa" else "external:whatsapp", has, exact=exact)
    ck_send_count(r, "S1-SMS-JA" if lang == "ordJa" else "S1-WhatsApp")

async def case_s2(r, mode, flight, lang):
    await to_s2_gate(r, mode, flight)
    await r.fill("callGateZone", "C"); await r.fill("callGate", "5"); await r.act("cta", "preview")
    if lang != "ordZh": await r.act(lang)
    has = ["CX" + flight, "C5"]
    exact = ja_expected("s2", "join" if mode == "callJoin" else "transit", "CX" + flight, "C5") if lang == "ordJa" else None
    await ck_msg_order(r, lang)
    await r.act("cta", "external:sms" if lang == "ordJa" else "external:whatsapp", tuple(has), exact=exact)
    ck_send_count(r, "S2-SMS-JA" if lang == "ordJa" else "S2-WhatsApp")

async def case_direct(r):
    # Call Directly is its own entry on the Scenario page.
    await r.phone(); await r.act("goDirect", "preview")
    ck(f"[{r.name}] call-only preview hides message preview", not await r.pg.locator("#msgToggle").is_visible())
    await r.act("cta", "external:whatsapp-call"); ck_send_count(r, "S3-WhatsApp Call")

async def case_s5(r, lang):
    await r.phone(); await r.act("goWpp", "wflight"); await r.fill("wFlight", "123"); await r.act("cta", "bag1")
    await r.fill("b1n", "123456"); await r.act("cta", "bag2")
    await r.fill("b2a", "BR"); await r.fill("b2n", "654321"); await r.act("cta", "preview")
    await r.act("ordEn"); await r.act("msgToggle"); await r.act("msgToggle")
    if lang == "ordZh": await r.act("ordZh")
    await ck_msg_order(r, lang)
    await r.act("cta", "external:whatsapp", ("CX123", "CX123456", "BR654321")); ck_send_count(r, "")

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
    await ck_msg_order(r, lang)
    if status == "stDelayed": has.append("18:00")
    await r.act("cta", "external:whatsapp", tuple(has)); ck_send_count(r, "")

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
    want_rows = ["Disrupted Flight=CX451", "Protect to=CX" + new + " / Dep 19:55",
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
        await to_s2_gate(r, "callJoin", "407")
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
    CASES.append((f"S5 {l}", lambda r, l=l: case_s5(r, l)))
for i, s in enumerate(("stPossible", "stDelayed", "stUnknown")):
    for j, a in enumerate(("arKnown", "arUnknown")):
        l = ("ordEn", "ordZh")[(i + j) % 2]
        CASES.append((f"S4 {s} {a} {l}", lambda r, s=s, a=a, l=l: case_s4(r, s, a, l)))

for s_, t_, g_, l_, n_ in (("gsDelayed", "gProtectedFlight", "gpAsap", "ordZh", "531"), ("gsDelayed", "gOriginalFlight", "gpWait", "ordEn", "403"),
                            ("gsCancelled", "gOriginalFlight", "gpAsap", "ordEn", "565"), ("gsCancelled", "gProtectedFlight", "gpWait", "ordZh", "479")):
    CASES.append((f"S4 Already at Gate {s_} {t_} {g_} {l_} CX{n_}", lambda r, s_=s_, t_=t_, g_=g_, l_=l_, n_=n_: case_s4_gate(r, s_, t_, g_, l_, n_)))

# ---- message matrix (probe) ---------------------------------------------------------
# The real cases above send once per scenario, passenger type and language. Here the probe builds every
# message branch for every allowed flight, and each must be exactly the approved copy in the right
# language order, with the expected Confirm details rows.
GEN_FLIGHTS = COPY["rules.cx.general"]; TR_FLIGHTS = COPY["rules.cx.transit"]
TPE_FLIGHTS = [n for n in GEN_FLIGHTS if n not in COPY["rules.cx.nonTpeOriginTransit"]]
DEST = COPY["rules.transit.destinations"]; DEST_CODES = COPY["rules.transit.destinationCodes"]
ORIGINS = COPY["rules.transit.origins"]; SEC_PFX = COPY["rules.sec.prefixes"]; HOME = COPY["rules.sec.homeIata"]
ORDER = {"ordZh": "zh", "ordEn": "en", "ordJa": "ja"}
TIME_RX = r"(?:[01]\d|2[0-3]):[0-5]\d"

def fill_copy(cid, vals):
    t = COPY[cid]
    for k, v in vals.items():
        t = t.replace("{" + k + "}", v)
    return t

def both(zh, en, lang):
    return zh + "\n\n" + en if lang == "ordZh" else en + "\n\n" + zh

def msg_rx(text):
    """Exact text, except the Taipei time (the clock at the moment of building)."""
    return re.escape(text).replace(re.escape("{TaipeiTime}"), TIME_RX)

def matrix_cases():
    """(label, probe question, expected text regex, expected rows, max chars or None) for every branch."""
    out = []
    for lang in ORDER:
        for f in GEN_FLIGHTS:  # S1 Join
            tag = f + "/123"
            want = COPY["s1.join.ja"] if lang == "ordJa" else both(fill_copy("s1.join.zh", {"flight_number": f}), fill_copy("s1.join.en", {"flight_number": f}), lang) + "\n\n" + tag
            out.append((f"S1 Join {lang}", {"flow": "miss", "fields": {"mFlight": f, "mSec": "123"}, "state": {"missMode": "join", "order": ORDER[lang]}},
                        re.escape(want), [["Flight", "CX" + f], ["Sec", HOME + " 123"]], 134 if lang == "ordJa" else None))
        for f in TR_FLIGHTS:  # S1 Transit
            want = COPY["s1.transit.ja"] if lang == "ordJa" else both(COPY["s1.transit.zh"], COPY["s1.transit.en"], lang)
            rows = [["Flight", "CX" + f], ["Sec", SEC_PFX[f]["transit"] + " 123"], ["Dep from", ORIGINS[f]], ["Destination", DEST_CODES[f]]]
            out.append((f"S1 Transit {lang}", {"flow": "miss", "fields": {"mFlight": f, "mSec": "123"}, "state": {"missMode": "transit", "order": ORDER[lang]}},
                        re.escape(want), rows, 67 if lang == "ordJa" else None))
        for mode, flights in (("join", GEN_FLIGHTS), ("transit", TR_FLIGHTS)):  # S2, both gate forms
            for f in flights:
                for zone, gate in (("C", "5"), ("B", "1R")):
                    d = DEST.get(f, DEST["451"]); g = zone + gate
                    vals = {"Flight": "CX" + f, "Gate": g, "DestinationZh": d["zh"], "DestinationEn": d["en"]}
                    if mode == "transit":
                        rt = COPY["rules.transit.smsRouteJa"][f]; vals.update(OriginJa=rt["from"], DestinationJaShort=rt["to"])
                    want = fill_copy(f"s2.{mode}.ja", vals) if lang == "ordJa" else both(fill_copy(f"s2.{mode}.zh", vals), fill_copy(f"s2.{mode}.en", vals), lang)
                    rows = [["Flight", "CX" + f]] + ([["Dep from", ORIGINS[f]]] if mode == "transit" else []) \
                        + ([["Destination", DEST_CODES[f]]] if f in DEST_CODES else []) \
                        + [["Sec", (SEC_PFX[f]["transit"] if mode == "transit" else HOME) + " 123"], ["Go to Gate", g]]
                    out.append((f"S2 {mode.capitalize()} {lang}", {"flow": "call", "fields": {"callFlight": f, "mSec": "123", "callGateZone": zone, "callGate": gate},
                                "state": {"callMode": mode, "order": ORDER[lang]}}, msg_rx(want), rows,
                                (134 if mode == "transit" else 67) if lang == "ordJa" else None))
        if lang == "ordJa":
            continue
        for status in ("possible", "delayed", "unknown"):  # S4 Tight Connection / Delayed / Suspended
            for arrange in ("known", "airport"):
                f = {"dFlight": "407", "tA": "CX", "tN": "888", "arriveTime": "14:00"}
                if status == "delayed": f["delayTime"] = "18:00"
                if arrange == "known": f.update(altA="CX", altN="401", altTime="15:30")
                vals = {"Disrupted Flight": "CX407", "Connecting Flight": "CX888", "Delay Time": f.get("delayTime", ""),
                        "Alternative Flight": "CX401" if arrange == "known" else "", "Alternative Departure Time": f.get("altTime", ""), "Arrive Airport Before": "14:00"}
                rows = [["Disrupted Flight", "CX407"], ["Connecting Flight", "CX888"],
                        ["Arrangement", "Protect to CX401 / Dep 15:30" if arrange == "known" else "Arrange in Airport"], ["Arrive at Airport Before", "14:00"]]
                want = both(fill_copy(f"s4.zh.{status}.{arrange}", vals), fill_copy(f"s4.en.{status}.{arrange}", vals), lang)
                out.append((f"S4 {status} {arrange} {lang}", {"flow": "dp", "fields": f,
                            "state": {"status": status, "arrange": "known" if arrange == "known" else "unknown", "order": ORDER[lang]}}, re.escape(want), rows, None))
        for st in ("delayed", "cancelled"):  # S4 Already at Gate: every branch, every protect-to flight
            for tg in ("original", "new"):
                for go in ("asap", "wait"):
                    for n in TPE_FLIGHTS:
                        if n == "451": continue
                        d = DEST.get(n, DEST["451"])
                        vals = {"Disrupted Flight": "CX451", "Delay Time": "21:00" if st == "delayed" else "", "New Flight": "CX" + n, "Gate": "B9",
                                "Dep Time": "19:55", "DestinationZh": d["zh"], "DestinationEn": d["en"]}
                        want = both(fill_copy(f"s4.zh.gate.{st}.{tg}.{go}", vals), fill_copy(f"s4.en.gate.{st}.{tg}.{go}", vals), lang)
                        rows = [["Disrupted Flight", "CX451"], ["Protect to", "CX" + n + " / Dep 19:55"], ["Proceed to Gate", "CX451" if tg == "original" else "CX" + n + " / B9"]]
                        f = {"dFlight": "451", "gNewN": n, "gGateZone": "B", "gGate": "9", "gDepTime": "19:55", "delayTime": "21:00" if st == "delayed" else ""}
                        out.append((f"S4 Already at Gate {st} {tg} {go} {lang}", {"flow": "dp", "fields": f,
                                    "state": {"status": "gate", "gateStatus": st, "gateTarget": tg, "gateGo": go, "order": ORDER[lang]}}, re.escape(want), rows, None))
        vals = {"Arrival Flight": "CX123", "Bag Tag 1": "CX123456", "Bag Tag 2": "BR654321"}  # S5
        out.append((f"S5 {lang}", {"flow": "wpp", "fields": {"wFlight": "123", "b1a": "CX", "b1n": "123456", "b2a": "BR", "b2n": "654321"}, "state": {"order": ORDER[lang]}},
                    re.escape(both(fill_copy("s5.zh", vals), fill_copy("s5.en", vals), lang)),
                    [["Arrival Flight", "CX123"], ["Bag Tag 1", "CX123456"], ["Bag Tag 2", "BR654321"]], None))
    return out

async def message_matrix(r):
    cases = matrix_cases()
    ans = await probe_all(r.pg, "message", [c[1] for c in cases])
    groups = {}
    for (label, q, rx, rows, limit), a in zip(cases, ans):
        g = groups.setdefault(label, [0, []])
        g[0] += 1
        why = []
        if re.fullmatch(rx, a["text"]) is None: why.append("text")
        if a["rows"] != rows: why.append(f"rows {a['rows']}")
        if limit and len(a["text"]) > limit: why.append(f"{len(a['text'])} chars > {limit}")
        if why: g[1].append(f"{q['fields']}: {', '.join(why)}")
    for label, (n, bad) in groups.items():
        ck(f"[{r.name}] {label}: approved message, language order and Confirm details for all {n} inputs (rule)", not bad, "; ".join(bad[:3]))

# ---- guards -------------------------------------------------------------------
RETURN_FROM_APP_JS = """() => {
    const setHidden = h => Object.defineProperty(document, 'hidden', {configurable: true, get: () => h});
    setHidden(true); document.dispatchEvent(new Event('visibilitychange'));
    setHidden(false); document.dispatchEvent(new Event('visibilitychange'));
}"""

async def return_from_app(r):
    """Staff come back from WhatsApp / SMS (the page is hidden, then shown again)."""
    await r.pg.evaluate(RETURN_FROM_APP_JS); await settle(r.pg)

async def call_by_phone_return(r, tag, want, tel_count="", label=False, icon=False):
    """After staff return from WhatsApp/SMS: visibility, ordering, colours and tel: link.

    label/icon opt into the two extra presentation assertions used by S5, while keeping
    the common return behaviour in one place for S1/S2/S3/S5.
    """
    await return_from_app(r)
    ck(f"[guard] {tag} return shows Try Another Number", (await r.pg.locator("#cta").inner_text()).strip() == "Try Another Number")
    call = r.pg.locator("#callPhone")
    ck(f"[guard] {tag} Call by Phone {'shown' if want else 'hidden'} after return", (await call.is_visible()) == want)
    brand = await r.pg.evaluate("(() => { const e = document.createElement('i'); e.style.color = 'var(--brand)'; document.body.append(e); const c = getComputedStyle(e).color; e.remove(); return c; })()")
    if not want:
        solo = await r.pg.evaluate("getComputedStyle(document.getElementById('cta')).backgroundColor")
        ck(f"[guard] {tag} Try Another Number alone takes the primary colour", solo == brand, solo)
        return
    if label:
        ck(f"[guard] {tag} Call by Phone label", (await call.inner_text()).strip() == "Call by Phone")
    if icon:
        ck(f"[guard] {tag} Call by Phone has a phone icon", await call.locator("svg").count() == 1)
    a = await call.bounding_box(); b = await r.pg.locator("#cta").bounding_box()
    ck(f"[guard] {tag} Call by Phone sits above Try Another Number", bool(a and b) and a["y"] + a["height"] <= b["y"], f"{a} {b}")
    bg = await r.pg.evaluate("['callPhone','cta'].map(i => getComputedStyle(document.getElementById(i)).backgroundColor)")
    ck(f"[guard] {tag} Call by Phone takes the primary colour, Try Another Number the secondary", bg[0] == brand and bg[1] != brand, str(bg))
    await tap_call_by_phone(r, tag, tel_count)

async def tap_call_by_phone(r, tag, tel_count):
    """Tap Call by Phone: it opens tel: with the number and sends exactly the expected usage count (or none)."""
    n0, c0 = len(r.nav), len(r.counts); await r.pg.click("#callPhone")
    await await_external(r.pg, r.nav, n0, r.counts, c0)
    url = r.nav[n0] if len(r.nav) > n0 else ""
    ck(f"[guard] {tag} Call by Phone opens tel: with the number", url == "tel:+" + PHONE, url)
    got = count_names(r.counts[c0:])
    ck(f"[guard] {tag} Call by Phone usage count is {tel_count or 'none'}", got == ([tel_count] if tel_count else []), str(got))
