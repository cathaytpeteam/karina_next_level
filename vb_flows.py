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
    await to_s2_gate(r, mode, flight)
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

async def case_s5(r, lang):
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

# ---- guards -------------------------------------------------------------------
RETURN_FROM_APP_JS = """() => {
    const setHidden = h => Object.defineProperty(document, 'hidden', {configurable: true, get: () => h});
    setHidden(true); document.dispatchEvent(new Event('visibilitychange'));
    setHidden(false); document.dispatchEvent(new Event('visibilitychange'));
}"""

async def call_by_phone_return(r, tag, want):
    """After staff return from WhatsApp/SMS: label, visibility, position, colours and tel: link."""
    await r.pg.evaluate(RETURN_FROM_APP_JS); await r.pg.wait_for_timeout(100)
    ck(f"[guard] {tag} return shows Try Another Number", (await r.pg.locator("#cta").inner_text()).strip() == "Try Another Number")
    ck(f"[guard] {tag} Call by Phone {'shown' if want else 'hidden'} after return", (await r.pg.locator("#callPhone").is_visible()) == want)
    brand = await r.pg.evaluate("(() => { const e = document.createElement('i'); e.style.color = 'var(--brand)'; document.body.append(e); const c = getComputedStyle(e).color; e.remove(); return c; })()")
    if not want:
        solo = await r.pg.evaluate("getComputedStyle(document.getElementById('cta')).backgroundColor")
        ck(f"[guard] {tag} Try Another Number alone takes the primary colour", solo == brand, solo)
        return
    a = await r.pg.locator("#callPhone").bounding_box(); b = await r.pg.locator("#cta").bounding_box()
    ck(f"[guard] {tag} Call by Phone sits above Try Another Number", bool(a and b) and a["y"] + a["height"] <= b["y"], f"{a} {b}")
    bg = await r.pg.evaluate("['callPhone','cta'].map(i => getComputedStyle(document.getElementById(i)).backgroundColor)")
    ck(f"[guard] {tag} Call by Phone takes the primary colour, Try Another Number the secondary", bg[0] == brand and bg[1] != brand, str(bg))
    n0 = len(r.nav); await r.pg.click("#callPhone")
    for _ in range(40):
        if len(r.nav) > n0: break
        await r.pg.wait_for_timeout(50)
    url = r.nav[n0] if len(r.nav) > n0 else ""
    ck(f"[guard] {tag} Call by Phone opens tel: with the number", url == "tel:+" + PHONE, url)
