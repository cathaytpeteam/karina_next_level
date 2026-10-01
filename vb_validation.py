"""Field validation table: one row per input rule.

Each row reaches the field's page with every other field valid, then the runner proves that
a valid value enables Next and that each invalid value is what disables it again. Add a row
when a field or rule is added; keep the README rule and the row in step.
"""
import vb_core
globals().update({k: v for k, v in vars(vb_core).items() if not k.startswith("__")})


async def _home(r):
    pass

async def _s4_transfer(r):
    await to_s4(r, "stPossible", "407"); await r.act("cta", "dtransfer")

async def _s4_arrange(r, choice):
    await _s4_transfer(r); await r.fill("tN", "888"); await r.act("cta", "darrange"); await r.act(choice)

async def _s5_bag(r):
    await r.phone(); await r.act("goWpp", "wflight"); await r.fill("wFlight", "123"); await r.act("cta", "bag1")

async def _s4_arrive(r):
    await _s4_arrange(r, "arUnknown"); await r.act("cta", "darrive")

async def _s4_protect_flight(r):
    await _s4_arrange(r, "arKnown"); await r.fill("altTime", "1530")

async def _s4_protect_time(r):
    await _s4_arrange(r, "arKnown"); await r.fill("altN", "401")

async def _s4_gate_flight(r):
    await r.phone(); await r.act("goDp", "dstatus"); await r.act("stGate", "dflight"); await r.act("gsCancelled")

async def _s4_gate_delay(r):
    await to_s4_gate(r, "407"); await r.act("gsDelayed")

async def _s4_gate_number(r):
    await to_s4_gate(r, "407", "gsCancelled"); await fill_protect(r, "401", "B", "", "1945")

# (name, reach the page, field id, valid values, [(invalid value, red border expected?)])
# red=None checks only that Next is disabled (the field may stay neutral while typing).
VALIDATION = [
    ("Phone number", _home, "phoneInput", ["886983952902"], [("123", None), ("85289648964", True)]),
    ("S1 Join flight", lambda r: to_s1(r, "missJoin", "407"), "mFlight", ["407"], [("888", True)]),
    ("S1 Transit flight", lambda r: to_s1(r, "missTransit", "450"), "mFlight", ["450"], [("407", True)]),
    ("S1 SEC", lambda r: _then(r, to_s1(r, "missJoin", "407"), "msec"), "mSec", ["580"], [("600", True)]),
    ("S2 Join flight", lambda r: to_s2(r, "callJoin", "407"), "callFlight", ["407"], [("888", True)]),
    ("S2 Transit flight", lambda r: to_s2(r, "callTransit", "565"), "callFlight", ["565"], [("407", True)]),
    ("S2 SEC", lambda r: _then(r, to_s2(r, "callJoin", "407"), "msec"), "mSec", ["580"], [("600", True)]),
    ("S2 gate", lambda r: to_s2_gate(r, "callJoin", "407"), "callGate", ["5", "1R"], [("", None), ("0", None)]),
    ("S4 Tight Connection flight", lambda r: to_s4(r, "stPossible", ""), "dFlight", ["451", "407"], [("450", True), ("888", True)]),
    ("S4 Already at Gate flight", _s4_gate_flight, "dFlight", ["451"], [("450", True)]),
    ("S4 Delayed time", lambda r: to_s4(r, "stDelayed", "407", ""), "delayTime", ["1800"], [("2575", True)]),
    ("S4 Connecting flight", _s4_transfer, "tN", ["888"], [("401", True)]),
    ("S4 Connecting airline", lambda r: _then_fill(r, _s4_transfer(r), "tN", "888"), "tA", ["KA", "3K"], [("K", None)]),
    ("S4 Protect to flight", _s4_protect_flight, "altN", ["401"], [("407", None), ("888", None)]),
    ("S4 Protect to time", _s4_protect_time, "altTime", ["1530"], [("2599", True)]),
    ("S4 Arrive time", _s4_arrive, "arriveTime", ["1400"], [("2400", True)]),
    ("S4 Already at Gate delay time", _s4_gate_delay, "delayTime", ["1830"], [("2575", None)]),
    ("S4 Protect to gate", _s4_gate_number, "gGate", ["5"], [("0", None)]),
    ("S5 arrival flight", lambda r: _then_act(r, r.phone(), "goWpp", "wflight"), "wFlight", ["123", "888"], [("", None)]),
    ("S5 bag tag", _s5_bag, "b1n", ["123456"], [("12345", None)]),
    ("S5 bag airline", lambda r: _then_fill(r, _s5_bag(r), "b1n", "123456"), "b1a", ["KA"], [("1X", None)]),
]

ROWS = {row[0]: row for row in VALIDATION}


async def _then(r, first, screen):
    await first; await r.act("cta", screen)

async def _then_fill(r, first, field, value):
    await first; await r.fill(field, value)

async def _then_act(r, first, trigger, screen):
    await first; await r.act(trigger, screen)


async def check_row(r, row):
    name, reach, field, valid, invalid = row
    await reach(r)
    for v in valid:
        await r.fill(field, v); await r.expect(f"{name}: {v} enables Next", True, not_bad=[field])
    for v, red in invalid:
        shown = v or "empty"
        await r.fill(field, valid[0])
        await r.expect(f"{name}: {valid[0]} enables Next before trying {shown}", True, not_bad=[field])
        await r.fill(field, v)
        await r.expect(f"{name}: {shown} keeps Next disabled", False, bad=[field] if red else None)


def table_jobs(browser):
    return [run_job(browser, "validation: " + row[0], lambda r, row=row: check_row(r, row)) for row in VALIDATION]
