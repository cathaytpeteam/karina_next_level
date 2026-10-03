"""Guard and state-rule dispatch: g() runs one spec guard, rule() one state rule."""
import vb_core
import vb_flows
globals().update({k: v for k, v in vars(vb_core).items() if not k.startswith("__")})
globals().update({k: v for k, v in vars(vb_flows).items() if not k.startswith("__")})
import vb_guards_other, vb_guards_s4


GUARDS = {**vb_guards_other.GUARDS, **vb_guards_s4.GUARDS}


async def g(r, name):
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
    else:
        return False
    return True

