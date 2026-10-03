"""Field validation table: one row per input rule, plus the rule matrix.

Each row is typed on its real page with every other field valid: a valid value must enable Next and
each invalid value must disable it again (with the red border where marked). Rows on the same path
share one page (WALKS), and every typed value is also asked of the test probe, whose answer must
match the screen. The rule matrix then asks the probe every flight number, SEC and time at once.
Add a row when a field or rule is added; keep the README rule and the row in step.
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


SCREEN_FIELDS_JS = "() => [...document.querySelectorAll('.screen:not([hidden]) input, .screen:not([hidden]) select')].map(e => e.id)"
SAME_BOX_JS = "ids => ids.flatMap(i => { const f = document.getElementById(i).closest('.field'); return f ? [...f.querySelectorAll('input, select')].map(e => e.id) : [i]; })"
FIELD_VALUES_JS = "ids => Object.fromEntries(ids.map(i => [i, document.getElementById(i).value]))"

async def ck_rule_matches_screen(r, label, state):
    """The probe, given exactly what is on the page, agrees with Next and the red borders on screen."""
    s = await r.st()
    if s["screen"] not in PROBE_STEPS:
        return
    fields = await r.pg.evaluate(FIELD_VALUES_JS, PROBE_FIELDS)
    focus = await r.pg.evaluate("() => document.activeElement ? document.activeElement.id : ''")
    ans = (await probe_all(r.pg, "check", [{"step": s["screen"], "fields": fields, "state": state, "focus": focus}]))[0]
    shown = set(await r.pg.evaluate(SCREEN_FIELDS_JS)) & set(PROBE_FIELDS)
    red = set(await r.pg.evaluate(SAME_BOX_JS, ans["bad"]))  # a red border wraps every input in its box
    ok = ans["ok"] == (not s["cta_disabled"]) and red & shown == set(s["bad"]) & shown
    ck(f"[{r.name}] {label}: rule answer matches the screen", ok, f"rule={ans} screen=Next {'off' if s['cta_disabled'] else 'on'}, red {s['bad']}")


async def check_row(r, row, state=None, leave=None):
    """Type the row's values on the current page. With state (the probe's view of the case) each value
    is also cross-checked with the probe; leave refills the field afterwards for the next row."""
    name, reach, field, valid, invalid = row
    if state is None:
        await reach(r)
    async def cross(label):
        if state is not None:
            await ck_rule_matches_screen(r, f"{name}: {label}", state)
    for v in valid:
        await r.fill(field, v); await r.expect(f"{name}: {v} enables Next", True, not_bad=[field]); await cross(v)
    for v, red in invalid:
        shown = v or "empty"
        await r.fill(field, valid[0])
        await r.expect(f"{name}: {valid[0]} enables Next before trying {shown}", True, not_bad=[field])
        await r.fill(field, v)
        await r.expect(f"{name}: {shown} keeps Next disabled", False, bad=[field] if red else None); await cross(shown)
    if state is not None:
        await r.fill(field, leave if leave is not None else valid[0])


# Rows on one path share a page: (job, layer, function). The phone row stays on its own (safety layer).
async def _walk_s1_join(r):
    st = {"missMode": "join"}
    await to_s1(r, "missJoin", "407"); await check_row(r, ROWS["S1 Join flight"], st)
    await r.act("cta", "msec"); await check_row(r, ROWS["S1 SEC"], st)

async def _walk_s1_transit(r):
    await to_s1(r, "missTransit", "450"); await check_row(r, ROWS["S1 Transit flight"], {"missMode": "transit"})

async def _walk_s2_join(r):
    st = {"callMode": "join"}
    await to_s2(r, "callJoin", "407"); await check_row(r, ROWS["S2 Join flight"], st)
    await r.act("cta", "msec"); await check_row(r, ROWS["S2 SEC"], st, "123")
    await r.act("cta", "callgate"); await check_row(r, ROWS["S2 gate"], st)

async def _walk_s2_transit(r):
    await to_s2(r, "callTransit", "565"); await check_row(r, ROWS["S2 Transit flight"], {"callMode": "transit"})

async def _walk_s4_tight(r):
    st = {"status": "possible"}
    await to_s4(r, "stPossible", ""); await check_row(r, ROWS["S4 Tight Connection flight"], st, "407")
    await r.act("cta", "dtransfer"); await check_row(r, ROWS["S4 Connecting flight"], st)
    await check_row(r, ROWS["S4 Connecting airline"], st)
    await r.act("cta", "darrange"); await r.act("arKnown"); st = dict(st, arrange="known")
    await r.fill("altTime", "1530"); await check_row(r, ROWS["S4 Protect to flight"], st)
    await check_row(r, ROWS["S4 Protect to time"], st)
    await r.act("arUnknown"); st = dict(st, arrange="unknown")
    await r.act("cta", "darrive"); await check_row(r, ROWS["S4 Arrive time"], st)

async def _walk_s4_delayed(r):
    await to_s4(r, "stDelayed", "407", ""); await check_row(r, ROWS["S4 Delayed time"], {"status": "delayed"})

async def _walk_s4_gate(r):
    await _s4_gate_flight(r); await check_row(r, ROWS["S4 Already at Gate flight"], {"status": "gate", "gateStatus": "cancelled"}, "407")
    await r.act("gsDelayed"); await check_row(r, ROWS["S4 Already at Gate delay time"], {"status": "gate", "gateStatus": "delayed"})
    await r.act("gsCancelled"); await r.act("cta", "dnew"); await fill_protect(r, "401", "B", "", "1945")
    await check_row(r, ROWS["S4 Protect to gate"], {"status": "gate", "gateStatus": "cancelled"})

async def _walk_s5(r):
    await r.phone(); await r.act("goWpp", "wflight"); await check_row(r, ROWS["S5 arrival flight"], {})
    await r.act("cta", "bag1"); await check_row(r, ROWS["S5 bag tag"], {})
    await check_row(r, ROWS["S5 bag airline"], {})

WALKS = {
    "Phone number": ("safety", lambda r: check_row(r, ROWS["Phone number"])),
    "S1 Join": ("input", _walk_s1_join), "S1 Transit": ("input", _walk_s1_transit),
    "S2 Join": ("input", _walk_s2_join), "S2 Transit": ("input", _walk_s2_transit),
    "S4 Tight Connection": ("input", _walk_s4_tight), "S4 Flight Delayed": ("input", _walk_s4_delayed),
    "S4 Already at Gate": ("input", _walk_s4_gate), "S5": ("input", _walk_s5),
}
_walked = {"Phone number", "S1 Join flight", "S1 SEC", "S1 Transit flight", "S2 Join flight", "S2 SEC", "S2 gate",
           "S2 Transit flight", "S4 Tight Connection flight", "S4 Connecting flight", "S4 Connecting airline",
           "S4 Protect to flight", "S4 Protect to time", "S4 Arrive time", "S4 Delayed time", "S4 Already at Gate flight",
           "S4 Already at Gate delay time", "S4 Protect to gate", "S5 arrival flight", "S5 bag tag", "S5 bag airline"}
assert _walked == set(ROWS), sorted(set(ROWS) ^ _walked)  # every row is typed on a real page


# ---- rule matrix (probe only) --------------------------------------------------------
NUMS = [str(i) for i in range(1, 1000)]
GENERAL = set(COPY["rules.cx.general"]); TRANSIT = set(COPY["rules.cx.transit"])
TPE_DEP = GENERAL - set(COPY["rules.cx.nonTpeOriginTransit"])
_DEST = COPY["rules.transit.destinations"]
TPE_HKG = {n for n in TPE_DEP if _DEST.get(n, _DEST["451"])["en"] == "Hong Kong"}
TIMES = [f"{h:02d}:{m:02d}" for h in range(26) for m in range(100)]
TIME_OK = {t for t in TIMES if int(t[:2]) <= 23 and int(t[3:]) <= 59}
TIMES_EDGE = [t for t in TIMES if t[3:] in ("00", "01", "30", "58", "59", "60", "99")]  # same time rule: every hour, minute edges
GATES = [(z, g) for z in COPY["rules.gate.zones"] for g in ("1", "2", "3", "4", "5", "6", "7", "8", "9", "1R")]
GATE_OK = {(z, g) for z, g in GATES if not (g == "1R" and z != COPY["rules.gate.b1rZone"])}
_DN = {"dFlight": "407", "gGateZone": "B", "gGate": "5", "gDepTime": "19:45"}
_AR = {"dFlight": "407", "altA": "CX", "altTime": "15:30"}

# (label, step, field, values, other fields, state, accepted values, red on the refused ones?)
MATRIX = [
    ("S1 Join flight accepts exactly the general CX list", "mflight", "mFlight", NUMS, {}, {"missMode": "join"}, GENERAL, True),
    ("S1 Transit flight accepts exactly the transit list", "mflight", "mFlight", NUMS, {}, {"missMode": "transit"}, TRANSIT, True),
    ("S1/S2 SEC accepts 0 to the maximum", "msec", "mSec", ["0"] + NUMS, {}, {}, {str(i) for i in range(COPY["rules.sec.max"] + 1)}, True),
    ("S2 Join flight accepts exactly the general CX list", "callflight", "callFlight", NUMS, {}, {"callMode": "join"}, GENERAL, True),
    ("S2 Transit flight accepts exactly the transit list", "callflight", "callFlight", NUMS, {}, {"callMode": "transit"}, TRANSIT, True),
    ("S4 Tight Connection flight accepts exactly TPE departures to Hong Kong", "dflight", "dFlight", NUMS, {}, {"status": "possible"}, TPE_HKG, True),
    ("S4 Flight Delayed flight accepts exactly TPE departures to Hong Kong", "dflight", "dFlight", NUMS, {"delayTime": "18:00"}, {"status": "delayed"}, TPE_HKG, True),
    ("S4 Flight Suspended flight accepts exactly TPE departures to Hong Kong", "dflight", "dFlight", NUMS, {}, {"status": "unknown"}, TPE_HKG, True),
    ("S4 Already at Gate flight accepts exactly the TPE departures", "dflight", "dFlight", NUMS, {}, {"status": "gate", "gateStatus": "cancelled"}, TPE_DEP, True),
    ("S4 Connecting CX flight refuses exactly the TPE departures", "dtransfer", "tN", NUMS, {"tA": "CX"}, {"status": "possible"}, set(NUMS) - TPE_DEP, True),
    ("S4 Connecting non-CX flight accepts every number", "dtransfer", "tN", NUMS, {"tA": "KA"}, {"status": "possible"}, set(NUMS), True),
    ("S4 Protect to CX flight accepts exactly the other TPE departures to Hong Kong", "darrange", "altN", NUMS, _AR, {"status": "possible", "arrange": "known"}, TPE_HKG - {"407"}, True),
    ("S4 Protect to non-CX flight accepts every number", "darrange", "altN", NUMS, dict(_AR, altA="BR"), {"status": "possible", "arrange": "known"}, set(NUMS), True),
    ("S4 Already at Gate Protect to accepts exactly the other TPE departures", "dnew", "gNewN", NUMS, _DN, {"status": "gate", "gateStatus": "cancelled"}, TPE_DEP - {"407"}, True),
    ("S5 arrival flight accepts every number", "wflight", "wFlight", NUMS, {}, {}, set(NUMS), True),
    ("S4 Arrive time accepts exactly 00:00-23:59", "darrive", "arriveTime", TIMES, {}, {"status": "possible"}, TIME_OK, True),
    ("S4 Delayed time accepts exactly 00:00-23:59", "dflight", "delayTime", TIMES_EDGE, {"dFlight": "407"}, {"status": "delayed"}, TIME_OK, True),
    ("S4 Protect to time accepts exactly 00:00-23:59", "darrange", "altTime", TIMES_EDGE, dict(_AR, altN="401"), {"status": "possible", "arrange": "known"}, TIME_OK, True),
    ("S4 Already at Gate DEP time accepts exactly 00:00-23:59", "dnew", "gDepTime", TIMES_EDGE, dict(_DN, gNewN="401"), {"status": "gate", "gateStatus": "cancelled"}, TIME_OK, True),
]
GATE_MATRIX = [
    ("S2 gate accepts B/C 1-9 and only B1R", "callgate", "callGateZone", "callGate", {}, {"callMode": "join"}),
    ("S4 Protect to gate accepts B/C 1-9 and only B1R", "dnew", "gGateZone", "gGate", dict(_DN, gNewN="401"), {"status": "gate", "gateStatus": "cancelled"}),
]

def _short(xs):
    xs = sorted(xs, key=lambda x: (len(str(x)), str(x)))
    return ", ".join(map(str, xs[:12])) + (" ..." if len(xs) > 12 else "")

async def rule_matrix(r):
    """Every flight number 1-999, SEC and time on every rule, asked of the probe in one go per rule."""
    for label, step, field, values, others, state, want, red in MATRIX:
        want = want & set(values)
        ans = await probe_all(r.pg, "check", [{"step": step, "fields": dict(others, **{field: v}), "state": state} for v in values])
        took = {v for v, a in zip(values, ans) if a["ok"]}
        reds = {v for v, a in zip(values, ans) if field in a["bad"]}
        ok = took == want and (not red or reds == set(values) - want)
        ck(f"[{r.name}] {label} (rule)", ok, f"wrongly accepted {_short(took - want)}; wrongly refused {_short(want - took)}"
           + (f"; red wrongly {_short(reds ^ (set(values) - want))}" if red else ""))
    for label, step, zf, gf, others, state in GATE_MATRIX:
        ans = await probe_all(r.pg, "check", [{"step": step, "fields": dict(others, **{zf: z, gf: g}), "state": state} for z, g in GATES])
        took = {zg for zg, a in zip(GATES, ans) if a["ok"]}
        ck(f"[{r.name}] {label} (rule)", took == GATE_OK, f"wrongly accepted {_short(took - GATE_OK)}; wrongly refused {_short(GATE_OK - took)}")


def table_jobs(browser):
    return [run_job(browser, "validation: " + n, fn, layer) for n, (layer, fn) in WALKS.items()] + \
           [run_job(browser, "validation: rule matrix", rule_matrix, "input")]
