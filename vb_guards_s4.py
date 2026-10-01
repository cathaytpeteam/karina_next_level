"""Scenario 4 (Disrupted Pax) guards from flow-behavior-spec.json."""
import vb_core
import vb_flows
globals().update({k: v for k, v in vars(vb_core).items() if not k.startswith("__")})
globals().update({k: v for k, v in vars(vb_flows).items() if not k.startswith("__")})


async def guard_s4_no_call_by_phone(r, name="s4_no_call_by_phone"):
    await case_s4(r, "stPossible", "arUnknown", "ordEn")
    await call_by_phone_return(r, "S4", False)


async def guard_s4_delayed_requires_time(r, name="s4_delayed_requires_time"):
    await to_s4(r, "stDelayed", delay=None)
    vis = await r.pg.locator("#delayWrap").is_visible()
    ck("[guard] Delayed shows Delayed-to field", vis)
    await r.expect("Delayed without time keeps Next disabled", False)
    await r.fill("delayTime", "1800"); await r.expect("Delayed 18:00 accepted", True)
    ck("[guard] Delayed-to shows full 18:00", await r.val("delayTime") == "18:00", await r.val("delayTime"))

async def guard_s4_flight_type_has_no_next(r, name="s4_flight_type_has_no_next"):
    await r.phone(); await r.act("goDp", "dstatus")
    ck("[guard] S4 Flight Type page has no Next (choices navigate directly)", (await r.st())["foot_hidden"])

async def guard_s4_delayed_flight_focuses_time(r, name="s4_delayed_flight_focuses_time"):
    await to_s4(r, "stDelayed", delay=None)
    await r.pg.wait_for_timeout(100)
    focused = await r.pg.evaluate("document.activeElement.id")
    ck("[guard] valid 3-digit Delayed flight moves the cursor to Delayed to", focused == "delayTime", focused)

async def guard_s4_delayed_bad_time_shows_hint(r, name="s4_delayed_bad_time_shows_hint"):
    await to_s4(r, "stDelayed", delay="2575"); await r.blur("delayTime")
    hint = (await r.pg.locator("#hint").text_content() or "").strip()
    ck("[guard] Delayed 25:75 shows the invalid-time hint", hint == COPY["error.time.invalid"], hint)


async def guard_s4_flight_type_look(r, name="s4_flight_type_look"):
    await r.phone(); await r.act("goDp", "dstatus")
    look = await r.pg.evaluate("""() => { const c = s => getComputedStyle(document.querySelector(s));
      const d = document.createElement('i'); d.style.background = 'var(--surface)'; document.body.appendChild(d); const surface = getComputedStyle(d).backgroundColor; d.remove();
      return {tight: c('#stPossible').backgroundColor, gate: c('#stGate').backgroundColor, surface, align: c('#s-dstatus h1').textAlign}; }""")
    ck("[guard] Tight Connection uses the neutral surface colour; Already at Gate stays tinted", look["tight"] == look["surface"] and look["gate"] != look["surface"], str(look))
    ck("[guard] Flight Type title is not centred (same placement as Passenger Type)", look["align"] in ("start", "left"), look["align"])

async def guard_s4_gate_b1r_row_keeps_height(r, name="s4_gate_b1r_row_keeps_height"):
    # The B1R? suggestion has a reserved row, so the page height does not change when it appears or leaves.
    height = "() => document.querySelector('.screen:not([hidden])').scrollHeight"
    r2 = await Run(r.browser, name + " (Final Call)").open()
    for run, walk, field, button in ((r, to_s4_gate(r, "407", "gsCancelled"), "gGate", "gGateR"),
                                     (r2, to_s2_gate(r2, "callJoin", "407"), "callGate", "callGateR")):
        await walk; before = await run.pg.evaluate(height)
        await run.fill(field, "1"); await run.pg.wait_for_timeout(100)
        shown = await run.pg.locator("#" + button).is_visible(); with_button = await run.pg.evaluate(height)
        await run.fill(field, "5"); await run.pg.wait_for_timeout(100); without = await run.pg.evaluate(height)
        ck(f"[guard] {field}: B1R? appearing or leaving does not change the page height", shown and before == with_button == without,
           f"{before} / {with_button} / {without}, button shown {shown}")
    await r2.close()


async def guard_s4_delayed_time_display(r, name="s4_delayed_time_display"):
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

async def guard_s4_protect_fields_side_by_side(r, name="s4_protect_fields_side_by_side"):
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


async def guard_s4_non_delayed_hides_time(r, name="s4_non_delayed_hides_time"):
    for st in ("stPossible", "stUnknown"):
        rr = await Run(r.browser, name + " " + st).open()
        await to_s4(rr, st)
        ck(f"[guard] {st} hides Delayed-to field", not await rr.pg.locator("#delayWrap").is_visible())
        await rr.expect(f"{st} needs no time", True); await rr.close()


async def guard_s4_connecting_allows_non_cx(r, name="s4_connecting_allows_non_cx"):
    await to_s4(r, "stPossible"); await r.act("cta", "dtransfer")
    await r.fill("tA", "KA"); await r.fill("tN", "401"); await r.expect("connecting KA401 accepted", True, not_bad=["tN"])

async def guard_s4_connecting_rejects_bad_airline(r, name="s4_connecting_rejects_bad_airline"):
    await to_s4(r, "stPossible"); await r.act("cta", "dtransfer")
    await r.fill("tN", "888"); await r.fill("tA", "K")
    await r.expect("airline 'K' neutral while still typing", False, not_bad=["tN"])
    await r.blur("tA"); await r.expect("airline 'K' red after leaving the field", False, ["tN"])

async def guard_s4_protect_panel_attached_to_option(r, name="s4_protect_panel_attached_to_option"):
    await to_s4(r, "stDelayed"); await r.act("cta", "dtransfer"); await r.fill("tN", "888"); await r.act("cta", "darrange")
    await r.act("arKnown"); await r.pg.wait_for_timeout(350)
    box = {i: await r.pg.locator("#" + i).bounding_box() for i in ("arKnown", "altWrap", "arUnknown")}
    k, w, u = box["arKnown"], box["altWrap"], box["arUnknown"]
    ck("[guard] protect fields sit directly under 'Will protect to' and above 'Arrange in airport'",
       abs(w["y"] - (k["y"] + k["height"])) < 2 and u["y"] >= w["y"] + w["height"] and abs(w["x"] - k["x"]) < 1 and abs(w["width"] - k["width"]) < 1,
       str(box))

async def guard_s4_arrange_requires_choice(r, name="s4_arrange_requires_choice"):
    await to_s4(r, "stPossible"); await r.act("cta", "dtransfer"); await r.fill("tN", "888"); await r.act("cta", "darrange")
    await r.expect("no arrangement chosen keeps Next disabled", False)
    await r.act("arUnknown"); await r.expect("Arrange in airport enables Next", True)

async def guard_s4_protect_requires_valid_flight_and_time(r, name="s4_protect_requires_valid_flight_and_time"):
    await to_s4(r, "stPossible"); await r.act("cta", "dtransfer"); await r.fill("tN", "888"); await r.act("cta", "darrange")
    await r.act("arKnown"); await r.expect("Will protect to without details disabled", False)
    await r.fill("altN", "401"); await r.fill("altTime", "1530"); await r.expect("CX401 15:30 accepted", True)
    await r.fill("altTime", "2599"); await r.expect("protect time 25:99 rejected", False, ["altTime"])

async def guard_s4_protect_cx_requires_tpe_whitelist(r, name="s4_protect_cx_requires_tpe_whitelist"):
    await to_s4(r, "stPossible", "407"); await r.act("cta", "dtransfer"); await r.fill("tN", "888"); await r.act("cta", "darrange")
    await r.act("arKnown"); await r.fill("altN", "888"); await r.fill("altTime", "1530")
    await r.expect("protect CX888 (not TPE whitelist) rejected", False, ["altN"])
    ck("[guard] CX non-whitelist protect hint is red", (await r.pg.locator("#hint").inner_text()) == "CX flight must depart TPE" and await r.pg.locator("#hint").evaluate("e=>e.classList.contains('bad')"))

async def guard_s4_protect_rejects_same_tpe_flight(r, name="s4_protect_rejects_same_tpe_flight"):
    await to_s4(r, "stPossible", "407"); await r.act("cta", "dtransfer"); await r.fill("tN", "888"); await r.act("cta", "darrange")
    await r.act("arKnown"); await r.fill("altN", "407"); await r.fill("altTime", "1530")
    await r.expect("protect same CX407 rejected", False, ["altN"])
    ck("[guard] same-flight protect hint is red", (await r.pg.locator("#hint").inner_text()) == "Same as Flight from TPE — not allowed" and await r.pg.locator("#hint").evaluate("e=>e.classList.contains('bad')"))

async def guard_s4_protect_allows_non_cx(r, name="s4_protect_allows_non_cx"):
    await to_s4(r, "stPossible", "407"); await r.act("cta", "dtransfer"); await r.fill("tN", "888"); await r.act("cta", "darrange")
    await r.act("arKnown"); await r.fill("altA", "KA"); await r.fill("altN", "888"); await r.fill("altTime", "1530")
    await r.expect("protect KA888 remains allowed", True, not_bad=["altN"])

async def guard_s4_gate_status_required(r, name="s4_gate_status_required"):
    await to_s4_gate(r)
    ck("[guard] Already at Gate step 2 shows Flight status", await r.pg.locator("#gStatusWrap").is_visible())
    await r.expect("Already at Gate without Flight status keeps Next disabled", False)
    ck("[guard] no status: Delayed to hidden", not await r.pg.locator("#delayWrap").is_visible())
    await r.act("gsCancelled"); await r.expect("CX407 + Cancelled enables Next", True)
    await r.back("dstatus"); await r.act("stPossible", "dflight")
    ck("[guard] Tight Connection step 2 has no Flight status", not await r.pg.locator("#gStatusWrap").is_visible())

async def guard_s4_gate_delayed_requires_time(r, name="s4_gate_delayed_requires_time"):
    await to_s4_gate(r); await r.act("gsDelayed")
    await r.pg.wait_for_timeout(400)  # Delayed to slides open (0.23 s) in the Already at Gate branch
    ck("[guard] gate Delayed shows Delayed to", (await r.pg.locator('#delayWrap').evaluate('e => e.getBoundingClientRect().height')) > 40 and await r.pg.locator("#delayWrap").evaluate("e => e.classList.contains('gateDelayOpen')"))
    await r.expect("gate Delayed without time keeps Next disabled", False)
    await r.fill("delayTime", "2575"); await r.expect("gate Delayed 25:75 rejected", False, ["delayTime"])
    await r.fill("delayTime", "2100"); await r.expect("gate Delayed 21:00 accepted", True, not_bad=["delayTime"])
    await r.act("gsCancelled")
    await r.pg.wait_for_timeout(400)
    ck("[guard] Cancelled hides and clears Delayed to", (await r.pg.locator('#delayWrap').evaluate('e => e.getBoundingClientRect().height')) < 2 and await r.val("delayTime") == "" and not await r.pg.locator("#delayWrap").evaluate("e => e.classList.contains('gateDelayOpen')"))

async def guard_s4_gate_protect_rules(r, name="s4_gate_protect_rules"):
    await to_s4_gate(r, "407", "gsCancelled"); await fill_protect(r, "407")
    await r.expect("gate protect same CX407 rejected", False, ["gNewN"])
    ck("[guard] gate same-flight hint is red", (await r.pg.locator("#hint").inner_text()) == "Same as Flight from TPE — not allowed" and await r.pg.locator("#hint").evaluate("e=>e.classList.contains('bad')"))
    await r.fill("gNewN", "888"); await r.expect("gate protect CX888 (not TPE whitelist) rejected", False, ["gNewN"])
    ck("[guard] gate non-whitelist hint is red", (await r.pg.locator("#hint").inner_text()) == "CX flight must depart TPE" and await r.pg.locator("#hint").evaluate("e=>e.classList.contains('bad')"))
    for n in ("401", "451", "531", "565"):
        await r.fill("gNewN", n); await r.expect(f"gate protect CX{n} (TPE departure) accepted", True, not_bad=["gNewN"])
    for n in ("450", "530", "564"):
        await r.fill("gNewN", n); await r.expect(f"gate protect CX{n} (not TPE departure) rejected", False, ["gNewN"])

async def guard_s4_gate_requires_valid_gate(r, name="s4_gate_requires_valid_gate"):
    await to_s4_gate(r, "407", "gsCancelled"); await fill_protect(r, "401", "B", "", "1945")
    await r.expect("gate empty keeps Next disabled", False)
    await r.fill("gGate", "0"); await r.expect("gate 0 rejected", False)
    await r.fill("gGateZone", "C"); await r.fill("gGate", "1R"); await r.expect("gate C1R normalizes to C1", True)
    ck("[guard] C1R is not retained", await r.val("gGate") == "1")

async def guard_s4_gate_dep_and_proceed_required(r, name="s4_gate_dep_and_proceed_required"):
    await to_s4_gate(r, "407", "gsCancelled"); await fill_protect(r, "401", "B", "9", "")
    await r.expect("no Dep and no Proceed choice keeps Next disabled", False)
    await r.fill("gDepTime", "2575"); await r.expect("Dep 25:75 rejected", False, ["gDepTime"])
    await r.fill("gDepTime", "1955"); await r.expect("Protect to complete enables Next (Proceed to Gate is step 4/5)", True, not_bad=["gDepTime"])
    await r.act("cta", "dgateaction"); await r.expect("no Proceed choice keeps Next disabled", False)
    await r.act("gpWait"); await r.expect("Wait for Staff without a gate target keeps Next disabled", False)
    await r.act("gOriginalFlight"); await r.expect("original-flight target + Wait for Staff enables Next", True)
    # A gate target alone (no ASAP / Wait for Staff) must not be enough: checked on a fresh case.
    r2 = await Run(r.browser, name + " (target only)").open()
    await to_s4_gate(r2, "407", "gsCancelled"); await fill_protect(r2, "401", "B", "9", "1955")
    await r2.act("cta", "dgateaction"); await r2.act("gOriginalFlight")
    await r2.expect("gate target without ASAP or Wait for Staff keeps Next disabled", False)
    await r2.close()

async def guard_s4_gate_fields_side_by_side(r, name="s4_gate_fields_side_by_side"):
    for W in (390, 360, 320):
        await r.pg.set_viewport_size({"width": W, "height": 844})
        if W == 390:
            await to_s4_gate(r, "451", "gsDelayed", "2100"); await fill_protect(r, "531", "B", "1R", "1955")
        await r.pg.wait_for_timeout(300)
        a = await r.pg.locator("#gNewN").evaluate("e => e.closest('.field').getBoundingClientRect().toJSON()")
        t = await r.pg.locator("#gGate").evaluate("e => e.closest('.field').getBoundingClientRect().toJSON()")
        dp = await r.pg.locator("#gDepTime").evaluate("e => e.closest('.field').getBoundingClientRect().toJSON()")
        clip = await r.pg.evaluate("[...document.querySelectorAll('#s-dnew input, #s-dnew .opt')].filter(e => e.offsetParent && e.scrollWidth > e.clientWidth + 1).map(e => e.id)")
        ck(f"[guard] {W}px: CX flight and Dep side by side, gate below", abs(a["top"] - dp["top"]) < 1 and dp["left"] > a["right"] and t["top"] >= a["bottom"], f"{a} {t} {dp}")
        ck(f"[guard] {W}px: Protect to fields not clipped", not clip, str(clip))


GUARDS = {
    "s4_no_call_by_phone": guard_s4_no_call_by_phone,
    "s4_delayed_requires_time": guard_s4_delayed_requires_time,
    "s4_delayed_time_display": guard_s4_delayed_time_display,
    "s4_protect_fields_side_by_side": guard_s4_protect_fields_side_by_side,
    "s4_non_delayed_hides_time": guard_s4_non_delayed_hides_time,
    "s4_connecting_allows_non_cx": guard_s4_connecting_allows_non_cx,
    "s4_connecting_rejects_bad_airline": guard_s4_connecting_rejects_bad_airline,
    "s4_protect_panel_attached_to_option": guard_s4_protect_panel_attached_to_option,
    "s4_arrange_requires_choice": guard_s4_arrange_requires_choice,
    "s4_protect_requires_valid_flight_and_time": guard_s4_protect_requires_valid_flight_and_time,
    "s4_protect_cx_requires_tpe_whitelist": guard_s4_protect_cx_requires_tpe_whitelist,
    "s4_protect_rejects_same_tpe_flight": guard_s4_protect_rejects_same_tpe_flight,
    "s4_protect_allows_non_cx": guard_s4_protect_allows_non_cx,
    "s4_gate_status_required": guard_s4_gate_status_required,
    "s4_gate_delayed_requires_time": guard_s4_gate_delayed_requires_time,
    "s4_gate_protect_rules": guard_s4_gate_protect_rules,
    "s4_gate_requires_valid_gate": guard_s4_gate_requires_valid_gate,
    "s4_gate_dep_and_proceed_required": guard_s4_gate_dep_and_proceed_required,
    "s4_gate_fields_side_by_side": guard_s4_gate_fields_side_by_side,
    "s4_flight_type_has_no_next": guard_s4_flight_type_has_no_next,
    "s4_delayed_flight_focuses_time": guard_s4_delayed_flight_focuses_time,
    "s4_delayed_bad_time_shows_hint": guard_s4_delayed_bad_time_shows_hint,
    "s4_flight_type_look": guard_s4_flight_type_look,
    "s4_gate_b1r_row_keeps_height": guard_s4_gate_b1r_row_keeps_height,
}
