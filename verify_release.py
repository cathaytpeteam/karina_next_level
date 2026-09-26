#!/usr/bin/env python3
"""Find Pax — release gate.

  python3 verify_release.py --fast    normal changes: static locks + hygiene + focused browser gate
  python3 verify_release.py --full    release only: --fast plus exhaustive browser + Service Worker suites
  python3 verify_release.py ... -v    also print every PASS line (default prints only FAIL lines + a summary)

While editing, use verify_changed.py instead (no browser, a few seconds).
On success, --fast/--full rewrite SHA256SUMS.txt so it records the verified tree.
Lock values live in locks.json; never edit them to make a failing check pass.
"""
from pathlib import Path
import json, hashlib, re, sys, subprocess, time

T0=time.time()
r=Path(__file__).resolve().parent
FAST='--fast' in sys.argv
FULL='--full' in sys.argv
STATIC='--static' in sys.argv  # internal: used by verify_changed.py (static lock checks only)
VERBOSE='-v' in sys.argv or '--verbose' in sys.argv

for _old,_new in (('--quick','python3 verify_changed.py'),('--gate','python3 verify_release.py --fast')):
    if _old in sys.argv:
        print(f'{_old} was removed. Use: {_new}'); raise SystemExit(2)
_mode_count=sum((FAST, FULL, STATIC))
if _mode_count!=1:
    print('CHECK MODE REQUIRED' if _mode_count==0 else 'ERROR: choose exactly one of --fast / --full')
    print('  normal change: python3 verify_release.py --fast')
    print('  release:       python3 verify_release.py --full')
    print('No verification was run.')
    raise SystemExit(2)
s_html=(r/'index.html').read_text(encoding='utf-8')
css_external=(r/'app.css').read_text(encoding='utf-8') if (r/'app.css').is_file() else ''
app_js=(r/'app.js').read_text(encoding='utf-8') if (r/'app.js').is_file() else ''
copy_js=(r/'copy.js').read_text(encoding='utf-8') if (r/'copy.js').is_file() else ''
s=s_html+'\n<style>'+css_external+'</style>\n<script>'+copy_js+'</script>\n<script>'+app_js+'</script>'
LOCKS=json.loads((r/'locks.json').read_text(encoding='utf-8'))
b=LOCKS['baseline']
c=LOCKS['message_copy']

def load_copy_js():
    m=re.search(r'window\.FIND_PAX_COPY\s*=\s*Object\.freeze\((\{.*\})\);',copy_js,re.S)
    return json.loads(m.group(1)) if m else {}
COPY=load_copy_js()

def sh(x): return hashlib.sha256(x.encode('utf-8')).hexdigest()
def ef(n):
    L=s.splitlines()
    i=next((i for i,x in enumerate(L) if x.startswith('  function '+n+'(')),None)
    if i is None: return None
    for j in range(i+1,len(L)):
        if L[j]=='  }': return '\n'.join(L[i:j+1])
    return None

def ec(n):
    L=s.splitlines()
    i=next((i for i,x in enumerate(L) if x.startswith('  const '+n+'=')),None)
    if i is None: return None
    for j in range(i+1,len(L)):
        if L[j]=='  };': return '\n'.join(L[i:j+1])
    return None

def layout_lock():
    """Screen order, per-screen markup, control order, header/footer."""
    lock=LOCKS['layout']
    def sha(x): return hashlib.sha256(x.encode()).hexdigest()
    msgs=[]
    def fail(msg): msgs.append('FAIL layout: '+msg); return False
    ok=True
    found={}
    for m in re.finditer(r'<section\b[^>]*\bid="(s-[^"]+)"[^>]*>.*?</section>',s,re.S): found[m.group(1)]=m.group(0)
    order=list(found)
    if order!=lock['screen_order']:
        ok=fail('screen order changed') and ok
    for sid,want in lock['screen_sha256'].items():
        if sid not in found: ok=fail(f'{sid} missing') and ok
        else:
            markup=found[sid]
            if sid=='s-phone':
                # The separately checked release label is the only approved
                # variable inside this otherwise byte-locked screen.
                markup=markup.replace('<span class="appVersion" aria-label="App version">K1.2</span>',
                                      '<span class="appVersion" aria-label="App version">K1.1</span>')
            if sha(markup)!=want: ok=fail(f'{sid} protected markup changed') and ok
    for sid,want_ids in lock['control_order'].items():
        if sid in found:
            got_ids=re.findall(r'\bid="([^"]+)"',found[sid])[1:]
            if got_ids!=want_ids: ok=fail(f'{sid} field/control order changed') and ok
    patterns={
     'topbar':r'<header\b[^>]*class="head"[^>]*>.*?</header>',
     'footer':r'<footer\b[^>]*id="foot"[^>]*>.*?</footer>'
    }
    for name,pat in patterns.items():
        m=re.search(pat,s,re.S)
        if not m: ok=fail(f'{name} missing') and ok
        elif sha(m.group(0))!=lock['chrome_sha256'][name]: ok=fail(f'{name} protected markup changed') and ok
    return ok,msgs

def navigation_lock():
    """Flow steps, routes, progress labels, history, Scenario 4 rules."""
    lock=LOCKS['navigation']
    checks=[]
    def ck(name,cond):
        checks.append((name,bool(cond)))
    def section(sid):
        m=re.search(r'<section\b[^>]*\bid="'+re.escape(sid)+r'"[^>]*>.*?</section>',s,re.S)
        return m.group(0) if m else ''
    def obj_block(name):
        m=re.search(r'const\s+'+re.escape(name)+r'=\{(.*?)\n\s*\};',s,re.S)
        return m.group(1) if m else ''
    def func_body(name):
        m=re.search(r'function\s+'+re.escape(name)+r'\([^)]*\)\s*\{',s)
        if not m:return ''
        i=m.end(); depth=1
        while i<len(s) and depth:
            if s[i]=='{': depth+=1
            elif s[i]=='}': depth-=1
            i+=1
        return s[m.end():i-1] if depth==0 else ''

    # Exact flow step mappings: protects progress denominators and page sequence.
    for key,v in lock['flows'].items():
        steps=','.join('"'+x+'"' for x in v['steps'])
        title_id='dp' if key=='dpgate' else key
        exact=f'{key}:{{name:copy("progress.flow.{title_id}"),steps:[{steps}]}}'
        ck(f'{key} flow mapping', exact in s)

    # Scenario 1 routes and labels must never move during other flow edits.
    for x in [
     '$("goMiss").onclick=()=>{clearMissCase();flow="miss";S.callNoMessage=false;S.order="zh";S.orderSet=false;go("misstype");};',
     '$("missJoin").onclick=()=>{clearMissForModeChange("join");flow="miss";S.missMode="join";S.callNoMessage=false;S.order="zh";S.orderSet=false;go("mflight");};',
     '$("missTransit").onclick=()=>{clearMissForModeChange("transit");flow="miss";S.missMode="transit";S.callNoMessage=false;S.order="zh";S.orderSet=false;go("mflight");};',
    ]: ck('Scenario 1 route '+x.split('"')[1], x in s)
    ck('Scenario 1 progress label order', 'flow==="miss" && cur!=="misstype" && (S.missMode==="join"||S.missMode==="transit")' in s and 'renderProgressTitle(f.name+" - "+passengerType,progressText)' in s)

    # Scenario 2 routes + approved Final Call labels.
    for x in [
     '$("goCall").onclick=()=>{clearCallCase();flow="call";S.order="zh";S.orderSet=false;go("calltype");};',
     '$("callJoin").onclick=()=>{clearCallForModeChange("join");S.callMode="join";S.callNoMessage=false;S.order="zh";S.orderSet=false;go("callflight");};',
     '$("callTransit").onclick=()=>{clearCallForModeChange("transit");S.callMode="transit";S.callNoMessage=false;S.order="zh";S.orderSet=false;go("callflight");};',
     '$("goDirect").onclick=()=>{clearCallCase();flow="call";S.missMode="";S.callMode="direct";S.callNoMessage=true;S.order="zh";S.orderSet=false;clearDrafts();go("preview");};'
    ]: ck('Scenario 2 route '+x.split('"')[1], x in s)
    ck('Scenario 2 progress label order', 'flow==="call" && cur!=="calltype" && (S.callMode==="join"||S.callMode==="transit")' in s and 'renderProgressTitle(f.name+" - "+passengerType,progressText)' in s)
    ck('Scenario 1 Back hides Passenger Type annotation', 'cur!=="misstype"' in s)
    ck('Scenario 2 Back hides Passenger Type annotation', 'cur!=="calltype"' in s)
    ck('Scenario 1 Passenger Type is progress step 1/3', 'miss:{name:copy("progress.flow.miss"),steps:["misstype","mflight","msec"]}' in s)
    ck('Scenario 2 SEC page removed', 'id="s-callsec"' not in s and 'callSec' not in s and '"callsec"' not in s)
    ck('Scenario 1 preview keeps completed 3/3', 'const missCompletedPreview=flow==="miss"&&cur==="preview"' in s)
    ck('Progress calculation uses locked flow denominator', 'const progressText=(idx+1)+"/"+f.steps.length;' in s)
    ck('Call Directly progress 1/1', 'renderProgressTitle(directName,"1/1")' in s and 'const directName=S.missMode==="direct"?copy("progress.flow.miss"):(S.callMode==="direct"?copy("progress.flow.direct"):copy("progress.flow.call"));' in s)
    ck('Browser Back/Forward state direction', 'history.replaceState({findPax:true,pos:0,id:"phone"}' in s and 'history.pushState({findPax:true,pos:navPos,id}' in s and 'navPos=st.pos;' in s and 'showScreen(st.id);' in s)

    # Scenario 4 structural + behavior regression checks.
    dstatus=section('s-dstatus')
    dflight=section('s-dflight')
    ck('Scenario 4 Flight Type is step 1/6', 'dp:{name:copy("progress.flow.dp"),steps:["dstatus","dflight","dtransfer","darrange","darrive","preview"]}' in s)
    ck('Scenario 4 entry routes to Flight Type', '$("goDp").onclick=()=>{clearDpCase();flow="dp";S.order="en";S.orderSet=false;go("dstatus");};' in s)
    ck('Scenario 4 Flight Type labels', '<h1>Passenger Type</h1>' in dstatus and '>Already at Gate<' in dstatus and '>Tight Connection<' in dstatus and '>Delayed<' in dstatus and '>Suspended<' in dstatus)
    # Passenger Type page. "At Gate" group: Already at Gate (tinted, full row);
    # "Not at the Airport" group: Tight Connection (full row, same size, neutral colour), then Delayed | Suspended.
    ck('Scenario 4 Flight Type hierarchy', dstatus.count('choice passengerPrimary')==2 and dstatus.count('choice passengerSecondary')==2 and all(f'id="{i}"' in dstatus for i in ('stGate','stPossible','stDelayed','stUnknown')) and [dstatus.index(f'id="{i}"') for i in ('stGate','stPossible','stDelayed','stUnknown')]==sorted(dstatus.index(f'id="{i}"') for i in ('stGate','stPossible','stDelayed','stUnknown')))
    # Already at Gate sits alone in the "At Gate" group, above "Not at the Airport".
    ck('Scenario 4 Already at Gate choice', '<div class="choiceGroup">At Gate</div>' in dstatus and '<div class="choiceGroup">Not at the Airport</div>' in dstatus and dstatus.index('>At Gate<') < dstatus.index('id="stGate"') < dstatus.index('>Not at the Airport<') < dstatus.index('id="stPossible"') and '#s-dstatus #stPossible.passengerPrimary{background:var(--surface)}' in s and '#s-dstatus .choiceGroup::after' in s and '#s-dstatus .choiceGroup::before' not in s)
    ck('Scenario 4 Flight Type has no delayed-time field', 'delayWrap' not in dstatus and 'delayTime' not in dstatus and '<input' not in dstatus)
    ck('Scenario 4 delayed time merged into step 2/6', all(x in dflight for x in ['id="dFlight"','id="delayWrap"','Delayed to','id="delayTime"']) and dflight.index('id="dFlight"') < dflight.index('id="delayWrap"') < dflight.index('id="delayTime"'))

    # Flight Type uses the same default heading placement as Passenger Type: no special center override.
    css=(re.search(r'<style>(.*?)</style>',s,re.S) or [None,''])[1]
    centered=False
    for sel,body in re.findall(r'([^{}]+)\{([^{}]*)\}',css,re.S):
        if '#s-dstatus h1' in sel and 'text-align:center' in re.sub(r'\s+','',body):
            centered=True
    ck('Scenario 4 Flight Type title placement matches Passenger Type', not centered)
    ck('Scenario 4 Flight Type header matches Passenger Type', 'const hasWho=cur!=="phone"&&cur!=="calltype"&&cur!=="misstype"&&cur!=="dstatus"' in s)

    # Choice pages navigate immediately; there is no footer/Next and no NEXT[dstatus] path.
    ck('Scenario 4 Flight Type footer/Next hidden', 'const showFoot=cur!=="scenario"&&cur!=="calltype"&&cur!=="misstype"&&cur!=="dstatus";' in s)
    next_block=obj_block('NEXT')
    ck('Scenario 4 Flight Type has no NEXT handler', 'dstatus:' not in next_block)
    sel_body=func_body('selectDpFlightType')
    ck('Scenario 4 selection helper clears stale delay on branch change', 'S.status&&S.status!==nextStatus' in sel_body and '$("delayTime").value="";' in sel_body)
    ck('Scenario 4 selection helper immediately opens step 2/6', 'S.status=nextStatus;' in sel_body and 'go("dflight");' in sel_body)
    for bid,status in [('stPossible','possible'),('stDelayed','delayed'),('stUnknown','unknown'),('stGate','gate')]:
        ck(f'Scenario 4 {bid} direct navigation', f'$("{bid}").onclick=()=>selectDpFlightType("{status}");' in s)

    # Validation ownership: only Delayed requires delayed time, and only on step 2/6.
    ok_block=obj_block('OK')
    hint_block=obj_block('HINT')
    ck('Scenario 4 Flight Type selection itself is always continuable', 'dstatus:()=>S.status==="possible"||S.status==="delayed"||S.status==="unknown"' in ok_block and 'delayTime' not in re.search(r'dstatus:\(\)=>[^,\n]*',ok_block).group(0))
    ck('Scenario 4 Delayed time validates on step 2/6 only', 'dflight:()=>isFlt(v("dFlight"))&&generalCxOk(v("dFlight"))&&(S.status!=="delayed"||timeOk("delayTime"))' in ok_block)
    ck('Scenario 4 Suspended has no delay-time dependency', 'S.status!=="delayed"||timeOk("delayTime")' in ok_block)
    ck('Scenario 4 delayed hint belongs to step 2/6', 'dflight:()=>!isFlt(v("dFlight"))?copy("hint.flight.digits")' in hint_block and 'timeState("delayTime")==="bad"?copy("error.time.invalid")' in hint_block and 'dstatus:()=>""' in hint_block)
    ck('Scenario 4 delay field visibility belongs to dflight', 'if(cur==="dflight"){' in s and '$("delayWrap").hidden=!gateDelay&&S.status!=="delayed";' in s and 'if(cur==="dstatus")' in s)


    ck('Scenario 4 disrupted flight has explicit TPE departure whitelist', 'const TPE_NON_ORIGIN_TRANSIT_FLIGHTS=new Set(copyObj("rules.cx.nonTpeOriginTransit"));' in s and 'const TPE_DEPARTURE_FLIGHTS=new Set([...GENERAL_CX_FLIGHTS].filter' in s and 'const generalCxOk=raw=>GENERAL_CX_FLIGHTS.has' in s and 'const tpeDepartureCxOk=raw=>TPE_DEPARTURE_FLIGHTS.has' in s)
    ck('Scenario 4 disrupted flight visibly marks non-whitelist flight', 'id="dFlight"' in dflight and 'bad("dFlight",listBad("dFlight",v("dFlight"),S.status==="gate"?TPE_DEPARTURE_FLIGHTS:DP_HKG_FLIGHTS));' in s)
    ck('Scenario 4 Delayed valid 3-digit flight auto-focuses Delayed to', 'id==="dFlight" && S.status==="delayed" && this.value.length===3 && generalCxOk(this.value)' in s and '$("delayTime").focus()' in s)
    ck('Scenario 4 Delayed to remains editable HHMM input', 'id="delayTime" inputmode="numeric" maxlength="5"' in dflight and '["delayTime","altTime","arriveTime","gDepTime"].forEach' in s and 'fmtTime(this);render();' in s)

    # Scenario 4 "Pax already at Gate" branch.
    dnew=section('s-dnew')
    dgateaction=section('s-dgateaction')
    ck('Scenario 4 gate branch flow', 'dpgate:{name:copy("progress.flow.dp"),steps:["dstatus","dflight","dnew","dgateaction","preview"]}' in s and 'flow==="dp"&&S.status==="gate"&&cur!=="dstatus"?DP_BRANCH_FLOWS.dpgate:FLOWS[flow]' in s)
    ck('Scenario 4 gate branch routing', 'if(S.status==="gate")go("dnew");else go("dtransfer");' in next_block and 'dnew:()=>{normalizeFlightField("gNewN");go("dgateaction");}' in next_block)
    ck('Scenario 4 gate Flight status on step 2', all(x in dflight for x in ['id="gStatusWrap" hidden','>Flight status<','id="gsDelayed"','>Delayed<','id="gsCancelled"','>Cancelled<']) and dflight.index('id="dFlight"') < dflight.index('id="gStatusWrap"') < dflight.index('id="delayWrap"') and '$("gStatusWrap").hidden=S.status!=="gate";' in s)
    ck('Scenario 4 gate step 2 validation', 'dflight:()=>isFlt(v("dFlight"))&&generalCxOk(v("dFlight"))&&(S.status!=="delayed"||timeOk("delayTime"))&&(S.status!=="gate"||S.gateStatus==="cancelled"||(S.gateStatus==="delayed"&&timeOk("delayTime")))&&disruptedFlightOk(v("dFlight")),' in ok_block)
    ck('Scenario 4 Protect to page fields', all(x in dnew for x in ['<h1>Protect to</h1>','id="gNewN"','id="gGateZone"','id="gGate"','id="gDepTime"']) and all(x not in dnew for x in ['>Proceed to Gate<','id="gOriginalFlight"','id="gpAsap"']))
    ck('Scenario 4 Proceed to Gate page fields', all(x in dgateaction for x in ['<h1>Proceed to Gate</h1>','id="gOriginalFlight"','id="gProtectedFlight"','id="gpAsap"','>ASAP<','id="gpWait"','>Wait for Staff<']))
    ck('Scenario 4 Protect to validation', 'dnew:()=>isFlt(v("gNewN"))&&protectFlightOk("CX",v("gNewN"),v("dFlight"))&&!!dnGateFull()&&timeOk("gDepTime"),' in ok_block)
    ck('Scenario 4 Proceed to Gate validation', 'dgateaction:()=> (S.gateTarget==="original"||S.gateTarget==="new")&&(S.gateGo==="asap"||S.gateGo==="wait"),' in ok_block)
    ck('Scenario 4 Delayed to opens smoothly on step 2 (gate branch)', '$("delayWrap").classList.toggle("gateDelayOpen",delayOpen);' in s and '#s-dflight #delayWrap.gateDelay.gateDelayOpen{grid-template-rows:1fr' in s)
    ck('Scenario 4 Cancelled clears Delayed-to', '$("gsCancelled").onclick=()=>{S.gateStatus="cancelled";$("delayTime").value="";render();};' in s)
    ck('Scenario 4 gate progress label', 'S.status==="gate"?copy("progress.dp.gate")' in s)
    # Passenger Type pages of Scenario 1 (漏查) and Scenario 2 (Final Call):
    # Joining Passenger (big card) / Transit Passenger / Call Directly, one full-width row each; "& Message" is
    # shown as a message icon and Call Directly as a phone icon, both beside the arrow.
    ICON_MSG='<path d="M6.5 3h11A2.5 2.5 0 0 1 20 5.5v8a2.5 2.5 0 0 1-2.5 2.5H10l-4.5 4v-4A2.5 2.5 0 0 1 4 13.5v-8A2.5 2.5 0 0 1 6.5 3z"/><path d="M8 8h8M8 11.5h5"/>'
    ICON_PHONE='<rect x="4.5" y="3" width="10.5" height="18" rx="2.4"/><path d="M8.6 17.6h2.3M18.2 8.6a4.6 4.6 0 0 1 0 6.8M20.9 6a8.4 8.4 0 0 1 0 12"/>'
    def btn(sec,bid):
        m=re.search(r'<button[^>]*\bid="'+bid+r'".*?</button>',sec,re.S); return m.group(0) if m else ''
    for sid,pre in (('s-misstype','miss'),('s-calltype','call')):
        sec=section(sid)
        j,t=btn(sec,pre+'Join'),btn(sec,pre+'Transit')
        ck(f'{sid} labels and order', 'data-scenario-label="joining"' in j and 'data-scenario-label="transit"' in t and f'id="{pre}Direct"' not in sec and 'Message' not in re.sub(r'aria-label="[^"]*"','',sec) and sec.index(pre+'Join')<sec.index(pre+'Transit'))
        ck(f'{sid} screen readers still hear "& Message"', 'data-scenario-label="joining"' in j and 'data-scenario-label="transit"' in t)
        ck(f'{sid} message icons beside the arrow', all(ICON_MSG in b and b.index('class="actIco"')<b.index('class="chev"') for b in (j,t)) and sec.count('class="actIco"')==2)
    ck('Passenger Type rows full width, icons one column', '#s-calltype .choice.passengerSecondary,#s-misstype .choice.passengerSecondary{grid-column:1/-1}' in s and '#s-calltype .actIco,#s-misstype .actIco{flex:none;width:26px;height:26px;margin-left:10px;color:var(--brand-strong)}' in s)
    # ICON POLICY: small action icons (message) appear ONLY on the Scenario 1 and 2
    # Passenger Type pages. Scenario 4 Disrupted Passenger always sends a message, so its pages stay icon-free.
    # The Scenario page uses the illustrated scenario icons (not action icons).
    ck('ICON POLICY: action icons only on Scenario 1/2 Passenger Type', s.count('class="actIco"')==4 and all('<svg' not in section(x) for x in ('s-dstatus','s-dflight','s-dnew','s-dgateaction','s-dtransfer','s-darrange','s-darrive')))
    # Scenario page = 漏查, Final Call, Call Directly, Disrupted Passenger, Wrong Pick-Up,
    # no numbers; Final Call uses the carry-on runner illustration, Call Directly scenario-icon-2.png.
    sc=section('s-scenario')
    order=[sc.index(f'id="{i}"') for i in ('goMiss','goCall','goDirect','goDp','goWpp')]
    ck('Scenario page order and labels', order==sorted(order) and all(f'<span>{t}</span>' in sc for t in ('漏查','Final Call','Call Directly','Disrupted Passenger','Wrong Pick-Up')) and 'class="num"' not in sc and 'dp:{name:copy("progress.flow.dp")' in s and 'wpp:{name:copy("progress.flow.wpp")' in s)
    ck('Scenario page icons', 'class="scIco" viewBox="2 1 82 60"' in btn(sc,'goCall') and 'scenario-icon-2.png' in btn(sc,'goDirect') and 'scenario-icon-1.png' in btn(sc,'goMiss') and 'scenario-icon-4.png' in btn(sc,'goDp') and 'scenario-icon-3.png' in btn(sc,'goWpp') and '#s-scenario .ico .scIco{fill:none;stroke:none}' in s)
    ck('Scenario page icon size', '#s-scenario .ico img,#s-scenario .ico .scIco{width:42px;height:30px;' in s and '#s-scenario .ctext span{white-space:normal;overflow-wrap:normal;text-wrap:balance}' in s)
    return checks

bad=False
N_PASS=0
def ck(n,x):
    global bad,N_PASS
    ok=bool(x)
    if ok:
        N_PASS+=1
        if VERBOSE: print('PASS',n)
    else:
        print('FAIL',n,flush=True); bad=True

ck('Language heading', 'Message Language' not in s and 'First Message Language' not in s and '>Language<' in s)
ck('copy.js loaded before app.js', 0 <= s_html.find('./copy.js') < s_html.find('./app.js'))
ck('Scenario 1 Join Japanese', COPY.get('s1.join.ja') == b['protected']['japanese_sms']['scenario1_approved_copy'])
ck('Scenario 1 Transit Japanese', COPY.get('s1.transit.ja') == b['protected']['scenario1_transit_copy']['ja'])
ck('Scenario 3 no Japanese', 's3.ja' not in COPY)

# Flight rules and exceptions.
ck('general whitelist', COPY.get('rules.cx.general') == [x[2:] for x in b['protected']['flight_rules']['general_cx']])
ck('S1 Join whitelist', 'S.missMode==="join"?generalCxOk' in s)
ck('S1 Transit special', 'S.missMode==="transit"?transitCxOk' in s)
ck('S2 Join whitelist', 'S.callMode==="join") return generalCxOk' in s)
ck('S2 Transit special', 'S.callMode==="transit") return transitCxOk' in s)
ck('S4 whitelist', 'dflight:()=>isFlt(v("dFlight"))&&generalCxOk' in s)
ck('S3 arrival exception', 'wflight:()=>isFlt(v("wFlight"))' in s)
ck('Connecting exception', 'dtransfer:()=>isCarrier(v("tA"))&&isFlt(v("tN"))' in s)
ck('Protect CX whitelist + same-flight guard', 'protectFlightOk(v("altA"),v("altN"),v("dFlight"))' in s and 'sameProtectedCxFlight' in s and 'copy("error.protect.tpe")' in s and 'copy("error.protect.same")' in s)
ck('Alphanumeric airline designator', 'const isCarrier=s=>/^[A-Z0-9]{2}$/.test(s);' in s and 'replace(/[^A-Za-z0-9]/g,"")' in s)

ck('Scenario 1 SEC origin UI', all(x in s for x in ['mSecPrefix','mSec']) and 'missTransitIataValue' not in s)
ck('Scenario 2 SEC removed', 'id="s-callsec"' not in s and 'callSec' not in s and '"callsec"' not in s)
ck('No obsolete callTransitIataValue requirement', 'callTransitIataValue' not in s)
ck('Origin IATA mapping', COPY.get('rules.transit.origins') == {'450':'HKG','530':'HKG','564':'HKG','451':'NRT','531':'NGO','565':'KIX'})
ck('Destination IATA preserved', COPY.get('rules.transit.destinationCodes') == {'450':'NRT','564':'KIX','530':'NGO','451':'HKG','565':'HKG','531':'HKG'})
ck('Final Call Transit Dep from row', 'if(S.callMode==="transit"){const origin=transitOriginIata(callFlightNumber());if(origin)rows.push(["Dep from",origin]);}' in s)
ck('SEC prefix TPE/Transit mapping', COPY.get('rules.sec.prefixes',{}).get('450')=={'join':'TPE','transit':'HKG'} and COPY.get('rules.sec.prefixes',{}).get('451')=={'join':'TPE','transit':'NRT'} and COPY.get('rules.sec.prefixes',{}).get('531')=={'join':'TPE','transit':'NGO'} and COPY.get('rules.sec.prefixes',{}).get('565')=={'join':'TPE','transit':'KIX'})

vp=ef('validatePhone') or ''
ck('+81 mobile-only validation', 'if(n.startsWith("81"))' in vp and r'/^[6789]0\d{8}$/' in vp and '!mobile.startsWith("800")' in vp)
ck('Strict phone validity', 'typeof ph.isValid==="function"' in vp and 'if(!ph.isValid()) continue;' in vp and 'validatePhoneNumberLength' not in vp)
ck('Canonical E.164 output', 'String(ph.number||"").replace(/^\\+/,"")' in vp)
ck('SMS routing', 'isiOS?"&":"?"' in s)
ck('WhatsApp routing', 'whatsapp://send?phone=' in s and 'https://wa.me/' in s)

ck('Scenario 3 language reset', '$("goWpp").onclick=()=>{clearWppCase();flow="wpp";S.order="zh";S.orderSet=false;go("wflight");};' in s)
ck('Scenario 4 language reset', '$("goDp").onclick=()=>{clearDpCase();flow="dp";S.order="en";S.orderSet=false;go("dstatus");};' in s)
ck('Scenario 1 clean re-entry', '$("goMiss").onclick=()=>{clearMissCase();' in s)
ck('Scenario 2 clean re-entry', '$("goCall").onclick=()=>{clearCallCase();' in s)
ck('Scenario 1 type switch guard', 'clearMissForModeChange("join")' in s and 'clearMissForModeChange("transit")' in s)
ck('Scenario 2 type switch guard', 'clearCallForModeChange("join")' in s and 'clearCallForModeChange("transit")' in s)
ck('Scenario 2 gate clears on type change', '["callFlight","callGate"].forEach' in (ef('clearCallForModeChange') or ''))
ck('Call progress stable four-step', 'call:{name:copy("progress.flow.call"),steps:["calltype","callflight","callgate","preview"]}' in s and 'FLOWS.call.steps=' not in s)
ck('Call Directly progress 1/1', 'const directProgress=directPreview;' in s and 'renderProgressTitle(directName,"1/1")' in s and 'copy("progress.flow.direct")' in s)
cp=ef('closePreviewEditor') or ''
ck('Read-only preview does not create draft', 'edits[S.order]=m.value' not in cp)
np=ef('normalizePhone') or ''
ck('Blocked warning before phone validity', 'const blockedDigits=blockedCandidateFor(n);' in np and np.find('const blockedDigits=blockedCandidateFor(n);') < np.find('const p=validatePhone(n);'))
dc=ef('dateCode') or ''
ck('Taipei dateCode timezone', 'timeZone:"Asia/Taipei"' in dc and 'getUTCDate()' in dc)

# Stable-ID copy lock: values were migrated byte-for-byte from the locked master.
copy_hashes=c.get('copy_ids',{})
ck('copy ID set', set(COPY)==set(copy_hashes))
for cid,want in copy_hashes.items():
    got=hashlib.sha256(json.dumps(COPY[cid],ensure_ascii=False,sort_keys=True,separators=(',',':')).encode('utf-8')).hexdigest() if cid in COPY else ''
    ck('copy '+cid, got==want)

# Protected behavior hashes that were previously stored but not enforced.
for section in ('phone_validation','japanese_sms','datetime'):
    funcs=b['protected'].get(section,{}).get('functions',{})
    for n,h in funcs.items():
        body=ef(n)
        ck('protected '+n, body is not None and sh(body)==h)

# UI regression checks: passenger type in progress and Direct phone placement.
ck('progress labels approved', 'const progressText=(idx+1)+"/"+f.steps.length;' in s and 'function renderProgressTitle(label,count)' in s and 'renderProgressTitle(f.name+" - "+passengerType,progressText)' in s and 'flow==="miss" && cur!=="misstype" && (S.missMode==="join"||S.missMode==="transit")' in s and 'flow==="call" && cur!=="calltype" && (S.callMode==="join"||S.callMode==="transit")' in s and '.step{font-size:17px;font-weight:700' in s and 'className:"progressCount"' in s and '.step .progressCount{margin-left:auto;color:var(--progress-count)' in s)
ck('direct phone in confirm details', 'rows.push(["Phone Number",(S.country?flagFor(S.country)+" ":"")+groupedPhone(S.phone)])' in s)
ck('direct phone hidden from header', 'const hasWho=cur!=="phone"&&cur!=="calltype"&&cur!=="misstype"&&cur!=="dstatus"&&!directPreview&&S.phone;' in s)
# Header number: no background, muted grey, regular weight, grouped by country
# (+886 983 952 902); shown on Confirm details too, so there is no "Send to" row. Links keep the plain digits.
ck('header number style', '.who{margin-left:auto;display:flex;align-items:center;gap:6px;background:var(--clear);color:var(--muted);border-radius:0;padding:6px 0;font-size:15px;font-weight:500;' in s)
ck('header number grouped for display only', '$("whoNum").textContent=groupedPhone(S.phone);' in s and 'ph.formatInternational()' in s and '"whatsapp://send?phone="+encodeURIComponent(S.phone)' in s and '"https://wa.me/"+S.phone' in s)
ck('no Send to row on Confirm details', '"Send to"' not in s and 'const rows=[];' in s)

# Message Preview is intentionally read-only. Editing/copying is delegated to WhatsApp/SMS.
ck('preview readonly', '<textarea class="msg" id="msg" autocomplete="off" readonly' in s)
ck('preview edit/copy controls removed', 'id="editMsg"' not in s and 'id="copyMsg"' not in s and 'Copy Text' not in s and 'Done Editing' not in s)

# Explicitly authorized final visual/copy tuning.
ck('language order labels 18px/700', '.msgToggle small{font-size:18px;font-weight:700' in s)
ck('Scenario 3 step 2/4 restored and 4/4 unclaimed bag label aligned', '<section class="screen" id="s-bag1" hidden>\n      <h1>Bag Tag 1</h1>\n      <p class="bagHelp" lang="zh-Hant">無人領取的行李</p>' in s and 'className="bagConfirmNote"' in s and '.sum dd .bagConfirmNote{font-size:18px' in s)
ck('Scenario 1 Join suffix compact', 'tag=flight+"/"+String(Number(v("mSec"))).padStart(3,"0")' in s and 'const tag="cx"' not in s)

# Consistency fixes.
ck('history Back/Forward state aware', 'history.replaceState({findPax:true,pos:0,id:"phone"}' in s and 'history.pushState({findPax:true,pos:navPos,id}' in s and 'navPos=st.pos;' in s and 'showScreen(st.id);' in s)
ck('Arrangement no arbitrary break', '.sum dt{color:var(--muted);flex:0 1 auto;min-width:0;display:flex;flex-wrap:wrap;align-items:center;gap:4px 14px;overflow-wrap:normal;word-break:normal}' in s)
ck('Final Call flight alignment selectors', '#s-callflight .field .code, #s-callgate .field .code{width:72px' in s and '#s-callflight .field input:not(.code), #s-callgate .field input:not(.code){flex:0 0 auto' in s and '#s-callflight .field .code .code' not in s and '#s-callflight .field input:not(.code) input:not(.code)' not in s)
ck('Scenario 1 confirm SEC includes IATA', '["Sec",(secPrefix(v("mFlight"),S.missMode)||"")+" "+String(Number(v("mSec"))).padStart(3,"0")]' in s)
ck('listed CX helper removed', 'Please select a listed CX flight' not in s)

# Service Worker checks: defined runtime list, existing local assets, current cache version.
sw=(r/'sw.js').read_text(encoding='utf-8')
ck('service worker version', 'const APP_VERSION="v1.2";' in sw)
ck('service worker cache revision', 'const CACHE_REV="K1.2-r2";' in sw)
ck('phone library preload', '<link rel="preload" href="./libphonenumber-mobile.js" as="script">' in s)
ck('phone library retries after timeout', 'setTimeout(()=>{if(!phoneLibReady){old.dataset.failed="1";retryPhoneLibrary();}},2000);' in s)
for gate in ('callGate','gGate'):
    tag=re.search(r'<input\b[^>]*\bid="'+gate+r'"[^>]*>',s)
    ck(gate+' numeric keyboard',tag is not None and 'inputmode="numeric"' in tag.group(0) and 'pattern="[0-9]*"' in tag.group(0))
ck('B1R suggestion only for area B and gate 1', '$(bid).hidden=v(zid)!=="B"||!/^1R?$/.test(g);' in s)
ck('B1R toggle preserves focus', '$(bid).addEventListener("pointerdown",e=>e.preventDefault());' in s and '$(iid).value=v(iid)==="1R"?"1":"1R";' in s)
ck('C1R removed when area changes', 'if(v(zid)==="C"&&el.value==="1R") el.value="1";' in s and '$(zid).addEventListener("change",normalize);' in s)
ck('C1R rejected by message gate helpers', 'z!==copy("rules.gate.b1rZone")&&n===copy("rules.gate.b1rNumber")' in ef('callGateFull') and 'z!==copy("rules.gate.b1rZone")&&x===copy("rules.gate.b1rNumber")' in ef('dnGateFull'))
ck('B1R row reserves height', 'min-height:36px' in s and '@media(max-width:380px){#s-dnew #gGateField .code{width:44px}}' in s)
_app_m=re.search(r'const APP_VERSION="([^"]+)";',sw)
_rev_m=re.search(r'const CACHE_REV="([^"]+)";',sw)
_display_version=(_rev_m.group(1).split('-r',1)[0] if _rev_m else '')
ck('homepage version label matches service worker', bool(_display_version) and f'<span class="appVersion" aria-label="App version">{_display_version}</span>' in s)
ck('service worker ASSETS declared', 'const ASSETS=[' in sw and 'cache.addAll(ASSETS)' in sw)
# Launch is cache-only: no network request for a cached file.
ck('service worker cache-first runtime', 'const cached=await cache.match(key);' in sw and 'if(cached) return cached;' in sw and 'const r=await fetch(req);' in sw and 'e.waitUntil(network' not in sw)
ck('service worker cache write failure isolated', 'if(canCache) e.waitUntil(cache.put(key,r.clone()).catch(()=>{}));' in sw and 'await cache.put(url,r).catch(()=>{});' in sw)
ck('service worker navigation redirect not cached', '!(req.mode==="navigate"&&r.redirected)' in sw)
ck('service worker no forced startup update/reload', 'reg.update()' not in s and 'controllerchange' not in s and 'location.reload()' not in s)
required={
    './','./index.html','./app.css','./copy.js','./app.js','./manifest.webmanifest','./apple-touch-icon.png','./icon-192.png','./icon-512.png','./icon-maskable-512.png',
    './phone-bottom-icon.png','./scenario-icon-1.png',
    './scenario-icon-2.png','./scenario-icon-3.png','./scenario-icon-4.png','./libphonenumber-mobile.js'
}
m=re.search(r'const ASSETS=\[(.*?)\];',sw,re.S)
assets=set(re.findall(r'"([^"]+)"',m.group(1))) if m else set()
ck('service worker asset list exact', assets==required)
manifest=(r/'manifest.webmanifest').read_text(encoding='utf-8')
_icons=json.loads(manifest)['icons']
ck('manifest has one 512 maskable icon',
   [(i['src'],i['sizes']) for i in _icons if i['purpose']=='maskable']==[('./icon-maskable-512.png','512x512')]
   and [(i['src'],i['sizes']) for i in _icons if i['purpose']=='any']==[('./icon-192.png','192x192'),('./icon-512.png','512x512')])
ck('maskable icon distinct', hashlib.sha256((r/'icon-512.png').read_bytes()).hexdigest()!=hashlib.sha256((r/'icon-maskable-512.png').read_bytes()).hexdigest())
_maskable=(r/'icon-maskable-512.png').read_bytes()
_chunks={}; _offset=8
while _offset+12<=len(_maskable):
    _length=int.from_bytes(_maskable[_offset:_offset+4],'big')
    _chunks[_maskable[_offset+4:_offset+8]]=_maskable[_offset+8:_offset+8+_length]
    _offset+=12+_length
ck('maskable PNG is 512 square with 64-colour palette',
   _maskable[:8]==b'\x89PNG\r\n\x1a\n' and _chunks.get(b'IHDR',b'')[:8]==(512).to_bytes(4,'big')*2
   and len(_chunks.get(b'PLTE',b''))==64*3 and _chunks.get(b'IHDR',b'')[9:10]==b'\x03')
ck('retired maskable and max-library files absent', not (r/'icon-maskable-192.png').exists() and not (r/'libphonenumber-max.js').exists())
ck('service worker assets exist', all(a=='./' or (r/a[2:]).is_file() for a in assets))
ck('phone library local', './libphonenumber-mobile.js' in s and './libphonenumber-mobile.js' in assets and (r/'libphonenumber-mobile.js').is_file() and (r/'libphonenumber-mobile.js').stat().st_size==193372)
ck('phone library does not block first paint', '<script src="./libphonenumber-mobile.js"></script>' not in s and 'requestAnimationFrame(()=>requestAnimationFrame(loadPhoneLibrary))' in s and 'script.async=true;' in s)
ck('startup has no second clear/render pass', 'window.addEventListener("load",()=>{if(stack.length===1&&cur==="phone"){clearFields();render();}});' not in s)
ck('service worker strategy retained while cache revision advances', 'if(cached) return cached;' in sw and 'e.waitUntil(network' not in sw)
ck('phone CDN removed', 'cdn.jsdelivr.net/npm/libphonenumber-js' not in s and 'cdn.jsdelivr.net/npm/libphonenumber-js' not in sw)

# Android cold-start optimisation (static routes + phone-input idle window).
ck('SW static routes for launch assets', 'e.addRoutes(staticRoutes())' in sw and 'source:"cache"' in sw and 'search:""' in sw)
ck('SW assets refreshed off the launch path, in parallel, for all browsers', 'if(!e.data||e.data.type!=="refresh") return;' in sw and '{cache:"no-cache"}' in sw and '.then(()=>{ startRefresh(); })' in sw and 'await Promise.all(ASSETS.map(a=>refreshOne(cache,a)));' in sw and 'for(const a of ASSETS)' not in sw)
ck('SW registers in phone-input idle window only', s.count('navigator.serviceWorker.register(')==1 and 'function startServiceWorker(){' in s and 'postMessage({type:"refresh"})' in s)
ck('phone-input idle window runs after load', 'window.addEventListener("load",openPhoneWindow,{once:true});' in s and 'requestIdleCallback(fn,{timeout:1000})' in s)

# Authorized Scenario 4 Flight Type change.
ck('Scenario 4 Flight Type first', 'dp:{name:copy("progress.flow.dp"),steps:["dstatus","dflight","dtransfer","darrange","darrive","preview"]}' in s and 'go("dstatus")' in s)
ck('Scenario 4 Flight Type copy', '<h1>Passenger Type</h1>' in s and '>Already at Gate<' in s and '>Tight Connection<' in s and '>Delayed<' in s and '>Suspended<' in s)
ck('Scenario 4 Flight Type behaves like Passenger Type', 'cur!=="calltype"&&cur!=="misstype"&&cur!=="dstatus"' in s and 'cur!=="scenario"&&cur!=="calltype"&&cur!=="misstype"&&cur!=="dstatus"' in s)
ck('Scenario 4 Delayed time lives on step 2 only', 'id="s-dflight"' in s and 'id="delayWrap"' in s and 'if(cur==="dflight"){' in s and '$("delayWrap").hidden=!gateDelay&&S.status!=="delayed";' in s and 'dflight:()=>isFlt(v("dFlight"))&&generalCxOk(v("dFlight"))&&(S.status!=="delayed"||timeOk("delayTime"))' in s)

# Priority regression locks: these target the real-device failures that hash-only checks missed.
ck('legacy Android JS: no optional chaining', '?.' not in s)
ck('legacy Android JS: no native replaceChildren dependency', '.replaceChildren(' not in s and 'replaceChildrenCompat' in s)
ck('legacy Android Home: critical row geometry uses explicit flex margins', '#s-scenario .choice{min-height:80px;border-radius:18px;padding:8px 14px 8px 12px;display:flex;gap:0;' in s and '#s-scenario .ctext{flex:1 1 auto;' in s and 'margin-left:14px' in s and '#s-scenario .chev{flex:0 0 20px;margin-left:14px;' in s)
ck('legacy Android Passenger Type: action-icon spacing is explicit', '#s-calltype .actIco,#s-misstype .actIco{flex:none;width:26px;height:26px;margin-left:10px' in s and '#s-calltype .choice .chev,#s-misstype .choice .chev{font-size:26px;width:14px;margin-left:10px' in s)
ck('Scenario 1/2 label is Joining Passenger only', COPY.get('s.passenger.joining')=='Joining Passenger' and len(re.findall(r'<span data-scenario-label="joining"></span>',s_html))==2)
ck('Scenario 1/2 progress wording uses Passenger', 'copy("s.passenger.joining")' in s and 'copy("s.passenger.transit")' in s)
ck('Scenario 4 TPE departure split is explicit', 'const TPE_NON_ORIGIN_TRANSIT_FLIGHTS=new Set(copyObj("rules.cx.nonTpeOriginTransit"));' in s and 'const tpeDepartureCxOk=raw=>TPE_DEPARTURE_FLIGHTS.has' in s)
ck('fresh case clears stale invalid borders', 'function clearInvalidMarks(ids)' in s and 'clearInvalidMarks(["dFlight","tA","tN","delayTime","altA","altN","altTime","arriveTime"]);' in s)

# Layout lock: approved screen structure/field placement may change only with explicit user approval.
_lay_ok,_lay_msgs=layout_lock()
ck('layout lock', _lay_ok)
for _m in _lay_msgs: print(_m)
if VERBOSE and _lay_ok: print('  PASS layout lock: approved screens, field placement, progress/header and footer are unchanged')

# Navigation lock: step counts/order and routing are protected independently from layout markup.
_nav=navigation_lock()
ck('navigation lock', all(v for _,v in _nav))
for _n,_v in _nav:
    if not _v: print('FAIL',_n)
    elif VERBOSE: print('  PASS',_n)

def run_live(cmd):
    """Stream a sub-suite. Prints only non-PASS lines unless -v. Returns (returncode, pass_count)."""
    pr=subprocess.Popen(cmd,cwd=r,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,encoding='utf-8',errors='replace',bufsize=1)
    n=0
    for line in pr.stdout:
        if line.startswith('PASS'):
            n+=1
            if VERBOSE: print(line,end='',flush=True)
        else:
            print(line,end='',flush=True)
    return pr.wait(),n

# Packaging hygiene: temporary Python files are never valid release content.
_junk=[p.relative_to(r).as_posix() for p in r.rglob('*') if p.is_file() and ('__pycache__' in p.parts or p.suffix in ('.pyc','.pyo'))]
ck('release tree contains no Python temp files', not _junk)

if STATIC:
    # Called by verify_changed.py: static lock checks only, no browser, no SHA write.
    print(('FAIL' if bad else 'PASS')+f': static lock checks ({N_PASS} passed)')
    sys.exit(1 if bad else 0)

# Hygiene, colour lock and wiring for the whole tree (the static locks above already ran).
_rc,_n=run_live([sys.executable,str(r/'verify_changed.py'),'--all','--no-static'])
N_PASS+=_n
ck('hygiene, colour lock and wiring (verify_changed.py --all)', _rc==0)

# Browser verification is layered: the focused priority gate first; the exhaustive
# suite and the Service Worker matrix only in --full and only after the gate passes.
print('--- PRIORITY GATE: phone, Home geometry, S1/S2 Next, S3 confirm, S4 validation ---', flush=True)
_rc,_n=run_live([sys.executable, str(r/'verify_behavior.py'), '--priority']); N_PASS+=_n
ck('priority release gate (focused user-facing regressions)', _rc==0)
if FULL:
    if _rc==0:
        print('--- EXHAUSTIVE FLOW SUITE ---', flush=True)
        _rc2,_n=run_live([sys.executable, str(r/'verify_behavior.py')]); N_PASS+=_n
        ck('flow behaviour (all branches, Back/Forward, guards, state rules)', _rc2==0)
        # Service Worker: install, launch, offline, update, broken deploy, cache miss, with and
        # without Static Routing (plus upgrade from a previous build when --previous DIR is given).
        print('--- SERVICE WORKER SUITE ---', flush=True)
        sw_cmd=[sys.executable, str(r/'verify_behavior.py'), '--sw']
        if '--previous' in sys.argv: sw_cmd+=['--previous', sys.argv[sys.argv.index('--previous')+1]]
        _rc3,_n=run_live(sw_cmd); N_PASS+=_n
        ck('service worker scenarios (install, launch, offline, update, broken deploy, cache miss)', _rc3==0)
    else:
        ck('exhaustive suites (skipped because the priority gate failed)', False)

# SHA256SUMS records the verified tree. Written only when every check passed.
# Repository / hosting plumbing is not part of the release: .git*, .github, .nojekyll, CNAME.
def _release_file(p):
    rel=p.relative_to(r)
    if p.name in ('SHA256SUMS.txt','.nojekyll','CNAME') or '__pycache__' in rel.parts: return False
    return not any(x.startswith('.git') for x in rel.parts)
if not bad:
    _files=sorted(p.relative_to(r).as_posix() for p in r.rglob('*') if p.is_file() and _release_file(p))
    (r/'SHA256SUMS.txt').write_text(''.join(hashlib.sha256((r/f).read_bytes()).hexdigest()+'  '+f+'\n' for f in _files),encoding='utf-8')

_mode='FULL' if FULL else 'FAST'
if bad:
    print(f'FAIL: {_mode} check — fix the FAIL lines above. SHA256SUMS.txt was not updated.')
    sys.exit(1)
print(f'PASS: {_display_version} {_mode} check — {N_PASS} checks passed in {time.time()-T0:.0f}s. SHA256SUMS.txt updated.')
