"""Guard and state-rule dispatch: g() runs one spec guard, rule() one state rule."""
import vb_core
import vb_flows
globals().update({k: v for k, v in vars(vb_core).items() if not k.startswith("__")})
globals().update({k: v for k, v in vars(vb_flows).items() if not k.startswith("__")})
import vb_guards_other, vb_guards_s4
import vb_validation


GUARDS = {**vb_guards_other.GUARDS, **vb_guards_s4.GUARDS}


# Spec guards whose whole check is one row of the field validation table (vb_validation.py).
TABLE_GUARDS = {
    "phone_invalid_blocks_next": "Phone number",
    "phone_canned_number_blocked": "Phone number",
    "s1_join_rejects_non_whitelist": "S1 Join flight",
    "s1_transit_rejects_join_only_flight": "S1 Transit flight",
    "s1_sec_over_580": "S1 SEC",
    "s2_join_rejects_non_whitelist": "S2 Join flight",
    "s2_transit_rejects_join_only_flight": "S2 Transit flight",
    "s2_gate_requires_valid_number": "S2 gate",
    "s5_bag_requires_six_digits": "S5 bag tag",
    "s5_bag_airline_letters_only": "S5 bag airline",
    "s4_flight_from_tpe_rejects_non_whitelist": "S4 Tight Connection flight",
    "s4_delayed_rejects_invalid_time": "S4 Delayed time",
    "s4_connecting_rejects_tpe_departure": "S4 Connecting flight",
    "s4_arrive_rejects_invalid_time": "S4 Arrive time",
}


async def g(r, name):
    if name in TABLE_GUARDS:
        await vb_validation.check_row(r, vb_validation.ROWS[TABLE_GUARDS[name]])
        return True
    fn = GUARDS.get(name)
    if fn is None:
        return False
    result = await fn(r)
    return True if result is None else result


async def rule(r, name):
    if name == "s1_mode_switch_clears_inputs":
        await to_s1(r, "missJoin", "407"); await r.back("misstype"); await r.act("missTransit", "mflight")
        ck("[rule] S1 Join -> Transit clears flight", await r.val("mFlight") == "")
    elif name == "s1_same_mode_keeps_inputs":
        await to_s1(r, "missJoin", "407"); await r.back("misstype"); await r.act("missJoin", "mflight")
        ck("[rule] S1 re-selecting Join keeps flight", await r.val("mFlight") == "407")
    elif name == "s2_mode_switch_clears_inputs":
        await to_s2(r, "callJoin", "407"); await r.act("cta", "msec"); await r.fill("mSec", "123")
        await r.back("callflight"); await r.back("calltype"); await r.act("callTransit", "callflight")
        ck("[rule] S2 Join -> Transit clears flight", await r.val("callFlight") == "")
        await r.fill("callFlight", "450"); await r.act("cta", "msec")
        ck("[rule] S2 Join -> Transit clears SEC", await r.val("mSec") == "", await r.val("mSec"))
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
    elif name == "try_another_number_other_scenario_starts_clean":
        await case_s5(r, "ordZh")
        await r.pg.evaluate(RETURN_FROM_APP_JS); await r.pg.wait_for_timeout(100)
        await r.pg.click("#cta"); await r.wait(lambda s: s["screen"] == "phone")
        await r.phone(); await r.act("goDp", "dstatus"); await r.back("scenario"); await r.act("goWpp", "wflight")
        ck("[rule] Picking another scenario after Try Another Number clears the kept case", await r.val("wFlight") == "", await r.val("wFlight"))
    elif name == "scenario_reentry_starts_clean":
        for tag, num, steps, stale in REENTRY:
            await _reentry(r, tag, num, steps, stale)
    else:
        return False
    return True


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
        ck(f"[rule] {tag} setup: {field}={bad_value} shows a red border", field in (await r.st())["bad"])
    ck(f"[rule] {tag} setup: Back reaches the Scenario page", await _back_to(r, "scenario"))
    dirty = await _walk(r, steps)
    ck(f"[rule] {tag} re-entry starts with empty fields and no red border", not dirty, ", ".join(dirty))
    again = [b for b in (await r.st())["pressed"] if b.startswith("ord")]
    ck(f"[rule] {tag} re-entry restores the default language", again == lang, f"first {lang}, again {again}")
