#!/usr/bin/env python3
"""Find Pax — release gate.

  python3 verify_release.py --fast    normal changes: static locks + hygiene + FAST browser checks
  python3 verify_release.py --full    release only: every browser test once + Service Worker suite
  python3 verify_release.py ... -v    also print every PASS line (default prints only FAIL lines + a summary)
  python3 verify_release.py ... --jobs 1|2|3    browser jobs at the same time (default 3 with --fast, 1 with --full;
                                                the two Service Worker modes run side by side unless --jobs is given)
  python3 verify_release.py --fast --look | --no-look    force or skip the appearance layer
  add --timing to list the slowest browser jobs

Browser checks run in layers (安全, 送出內容, 資料清除, 輸入規則, 流程, 能開能更新, 外觀; see vb_priority.py).
Safety runs first and is the only layer whose failure stops the rest; a summary line per layer ends the run.
In --fast the appearance layer runs only when app.css, index.html, the app.js layout part or a test file
changed since the last passing check (recorded in SHA256SUMS.txt).

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
METRICS='--metrics' in sys.argv

for _old,_new in (('--quick','python3 verify_changed.py'),('--gate','python3 verify_release.py --fast')):
    if _old in sys.argv:
        print(f'{_old} was removed. Use: {_new}'); raise SystemExit(2)
JOBS=sys.argv[sys.argv.index('--jobs')+1] if '--jobs' in sys.argv and sys.argv.index('--jobs')+1<len(sys.argv) else ('3' if FAST else '1')
if JOBS not in ('1','2','3'):
    print(f'ERROR: --jobs must be 1, 2 or 3 (got {JOBS!r}). No verification was run.'); raise SystemExit(2)
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
                # The release label is the only variable inside this byte-locked screen
                # (checked separately against CACHE_REV). The hash was recorded with K1.1.
                markup=re.sub(r'(<span class="appVersion" aria-label="App version">)[^<]*(</span>)',r'\1K1.1\2',markup)
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

    # Entry routes are compared with every S.order="..." assignment removed: the confirm page
    # sets the language from defaultMessageOrder(), so that value does not change behaviour.
    s_routes=re.sub(r'S\.order="[a-z]+";','',s)

    # Scenario 1 routes and labels must never move during other flow edits.
    for x in [
     '$("goMiss").onclick=()=>{if(!keepRetryCase("miss"))clearCaseData();flow="miss";S.callNoMessage=false;S.orderSet=false;go("misstype");};',
     '$("missJoin").onclick=()=>{clearMissForModeChange("join");flow="miss";S.missMode="join";S.callNoMessage=false;S.orderSet=false;go("mflight");};',
     '$("missTransit").onclick=()=>{clearMissForModeChange("transit");flow="miss";S.missMode="transit";S.callNoMessage=false;S.orderSet=false;go("mflight");};',
    ]: ck('Scenario 1 route '+x.split('"')[1], x in s_routes)
    ck('Scenario 1 progress label order', 'flow==="miss" && cur!=="misstype" && (S.missMode==="join"||S.missMode==="transit")' in s and 'renderProgressTitle(f.name+" - "+passengerType,progressText)' in s)

    # Scenario 2 routes + approved Final Call labels.
    for x in [
     '$("goCall").onclick=()=>{if(!keepRetryCase("call"))clearCaseData();flow="call";S.orderSet=false;go("calltype");};',
     '$("callJoin").onclick=()=>{clearCallForModeChange("join");S.callMode="join";S.callNoMessage=false;S.orderSet=false;go("callflight");};',
     '$("callTransit").onclick=()=>{clearCallForModeChange("transit");S.callMode="transit";S.callNoMessage=false;S.orderSet=false;go("callflight");};',
     '$("goDirect").onclick=()=>{if(!keepRetryCase("direct"))clearCaseData();flow="call";S.missMode="";S.callMode="direct";S.callNoMessage=true;S.orderSet=false;clearDrafts();go("preview");};'
    ]: ck('Scenario 2 route '+x.split('"')[1], x in s_routes)
    ck('Scenario 2 progress label order', 'flow==="call" && cur!=="calltype" && (S.callMode==="join"||S.callMode==="transit")' in s and 'renderProgressTitle(f.name+" - "+passengerType,progressText)' in s)
    ck('Browser Back/Forward state direction', 'history.replaceState({findPax:true,pos:0,id:"phone"}' in s and 'history.pushState({findPax:true,pos:navPos,id}' in s and 'navPos=st.pos;' in s and 'showScreen(st.id);' in s)

    # Scenario 4 structural + behavior regression checks.
    dstatus=section('s-dstatus')
    dflight=section('s-dflight')
    ck('Scenario 4 entry routes to Flight Type', '$("goDp").onclick=()=>{if(!keepRetryCase("dp"))clearCaseData();flow="dp";S.orderSet=false;go("dstatus");};' in s_routes)
    # Passenger Type page. "At Gate" group: Already at Gate (tinted, full row);
    # "Not at the Airport" group: Tight Connection (full row, same size, neutral colour), then Delayed | Suspended.
    # Already at Gate sits alone in the "At Gate" group, above "Not at the Airport".
    ck('Scenario 4 Already at Gate choice', '<div class="choiceGroup">At Gate</div>' in dstatus and '<div class="choiceGroup">Not at the Airport</div>' in dstatus and dstatus.index('>At Gate<') < dstatus.index('id="stGate"') < dstatus.index('>Not at the Airport<') < dstatus.index('id="stPossible"') and '#s-dstatus .choiceGroup::after' in s and '#s-dstatus .choiceGroup::before' not in s)

    # Choice pages navigate immediately; there is no footer/Next and no NEXT[dstatus] path.
    ck('Scenario 4 Flight Type footer/Next hidden', 'const showFoot=cur!=="scenario"&&cur!=="calltype"&&cur!=="misstype"&&cur!=="dstatus";' in s)
    next_block=obj_block('NEXT')
    sel_body=func_body('selectDpFlightType')
    for bid,status in [('stPossible','possible'),('stDelayed','delayed'),('stUnknown','unknown'),('stGate','gate')]:
        ck(f'Scenario 4 {bid} direct navigation', f'$("{bid}").onclick=()=>selectDpFlightType("{status}");' in s)

    # Validation ownership: only Delayed requires delayed time, and only on step 2/6.
    ok_block=obj_block('OK')
    hint_block=obj_block('HINT')
    ck('Scenario 4 delayed hint belongs to step 2/6', 'dflight:()=>!isFlt(v("dFlight"))?copy("hint.flight.digits")' in hint_block and 'timeState("delayTime")==="bad"?copy("error.time.invalid")' in hint_block and 'dstatus:()=>""' in hint_block)
    ck('Scenario 4 delay field visibility belongs to dflight', 'if(cur==="dflight"){' in s and '$("delayWrap").hidden=!gateDelay&&S.status!=="delayed";' in s and 'if(cur==="dstatus")' in s)


    ck('Scenario 4 disrupted flight has explicit TPE departure whitelist', 'const TPE_NON_ORIGIN_TRANSIT_FLIGHTS=new Set(copyObj("rules.cx.nonTpeOriginTransit"));' in s and 'const TPE_DEPARTURE_FLIGHTS=new Set([...GENERAL_CX_FLIGHTS].filter' in s and 'const generalCxOk=raw=>GENERAL_CX_FLIGHTS.has' in s and 'const tpeDepartureCxOk=raw=>TPE_DEPARTURE_FLIGHTS.has' in s)
    ck('Scenario 4 Delayed valid 3-digit flight auto-focuses Delayed to', 'id==="dFlight" && S.status==="delayed" && this.value.length===3 && generalCxOk(this.value)' in s and '$("delayTime").focus()' in s)

    # Scenario 4 "Pax already at Gate" branch.
    dnew=section('s-dnew')
    dgateaction=section('s-dgateaction')
    ck('Scenario 4 gate Flight status on step 2', all(x in dflight for x in ['id="gStatusWrap" hidden','>Flight Status<','id="gsDelayed"','>Delayed<','id="gsCancelled"','>Cancelled<']) and dflight.index('id="dFlight"') < dflight.index('id="gStatusWrap"') < dflight.index('id="delayWrap"') and '$("gStatusWrap").hidden=S.status!=="gate";' in s)
    ck('Scenario 4 Proceed to Gate validation', 'dgateaction:()=> (S.gateTarget==="original"||S.gateTarget==="new")&&(S.gateGo==="asap"||S.gateGo==="wait"),' in ok_block)
    # Passenger Type pages of Scenario 1 (漏查) and Scenario 2 (Final Call):
    # Joining Passenger (big card) / Transit Passenger / Call Directly, one full-width row each; "& Message" is
    # shown as a message icon and Call Directly as a phone icon, both beside the arrow.
    ICON_MSG='<path d="M6.5 3h11A2.5 2.5 0 0 1 20 5.5v8a2.5 2.5 0 0 1-2.5 2.5H10l-4.5 4v-4A2.5 2.5 0 0 1 4 13.5v-8A2.5 2.5 0 0 1 6.5 3z"/><path d="M8 8h8M8 11.5h5"/>'
    ICON_PHONE='<rect x="4.5" y="3" width="10.5" height="18" rx="2.4"/><path d="M8.6 17.6h2.3M18.2 8.6a4.6 4.6 0 0 1 0 6.8M20.9 6a8.4 8.4 0 0 1 0 12"/>'
    def btn(sec,bid):
        m=re.search(r'<button[^>]*\bid="'+bid+r'".*?</button>',sec,re.S); return m.group(0) if m else ''
    # ICON POLICY: small action icons (message) appear ONLY on the Scenario 1 and 2
    # Passenger Type pages. Scenario 4 Disrupted Passenger always sends a message, so its pages stay icon-free.
    # The Scenario page uses the illustrated scenario icons (not action icons).
    # Scenario page = 漏查, Final Call, Call Directly, Disrupted Passenger, Wrong Pick-Up,
    # no numbers; Final Call uses the carry-on runner illustration, Call Directly scenario-icon-2.png.
    sc=section('s-scenario')
    order=[sc.index(f'id="{i}"') for i in ('goMiss','goCall','goDirect','goDp','goWpp')]
    ck('Scenario page card text wraps evenly', '#s-scenario .ctext span{white-space:normal;overflow-wrap:normal;text-wrap:balance}' in s)
    return checks

bad=False
N_PASS=0
SAFETY_FAIL=0  # static privacy-lock failures: they stop the browser checks
def ck(n,x,safety=False):
    global bad,N_PASS,SAFETY_FAIL
    ok=bool(x)
    if ok:
        N_PASS+=1
        if VERBOSE: print('PASS',n)
    else:
        print('FAIL',n,flush=True); bad=True
        if safety: SAFETY_FAIL+=1


# Flight rules and exceptions.

ck('Final Call Transit Dep from row', 'if(S.callMode==="transit"){const origin=transitOriginIata(callFlightNumber());if(origin)rows.push(["Dep from",origin]);}' in s)

vp=ef('validatePhone') or ''

ck('Scenario 1 clean re-entry', '$("goMiss").onclick=()=>{if(!keepRetryCase("miss"))clearCaseData();' in s)
ck('Scenario 2 clean re-entry', '$("goCall").onclick=()=>{if(!keepRetryCase("call"))clearCaseData();' in s)
ck('Scenario 2 type switch guard', 'clearCallForModeChange("join")' in s and 'clearCallForModeChange("transit")' in s)
ck('Scenario 2 SEC clears on type change', '["callFlight","mSec","callGate"].forEach' in (ef('clearCallForModeChange') or ''))
cp=ef('closePreviewEditor') or ''
np=ef('normalizePhone') or ''
dc=ef('dateCode') or ''

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
ck('progress labels approved', 'const progressText=(idx+1)+"/"+f.steps.length;' in s and 'function renderProgressTitle(label,count)' in s and 'renderProgressTitle(f.name+" - "+passengerType,progressText)' in s and 'flow==="miss" && cur!=="misstype" && (S.missMode==="join"||S.missMode==="transit")' in s and 'flow==="call" && cur!=="calltype" && (S.callMode==="join"||S.callMode==="transit")' in s and 'className:"progressCount"' in s and '.step .progressCount{margin-left:auto;color:var(--progress-count)' in s)
ck('direct phone in confirm details', 'rows.push(["Phone Number",(S.country?flagFor(S.country)+" ":"")+groupedPhone(S.phone)])' in s)

# Message Preview is intentionally read-only. Editing/copying is delegated to WhatsApp/SMS.
# Sizes, colours and alignment are checked once, in the browser (appearance layer), never as CSS strings here.

ck('Scenario 5 step 2/4 restored and 4/4 unclaimed bag label aligned', '<section class="screen" id="s-bag1" hidden>\n      <h1>Bag Tag 1</h1>\n      <p class="bagHelp" lang="zh-Hant">無人領取的行李</p>' in s and 'className="bagConfirmNote"' in s)


# Service Worker checks: defined runtime list, existing local assets, current cache version.
sw=(r/'sw.js').read_text(encoding='utf-8')
ck('service worker cache revision', bool(re.search(r'const CACHE_REV="K\d+\.\d+-r\d+";', sw)))
ck('phone library preload', '<link rel="preload" href="./libphonenumber-mobile.js" as="script">' in s)
ck('phone library retries after timeout', 'setTimeout(()=>{if(!phoneLibReady){old.dataset.failed="1";retryPhoneLibrary();}},2000);' in s)
_app_m=re.search(r'const APP_VERSION="([^"]+)";',sw)
_rev_m=re.search(r'const CACHE_REV="([^"]+)";',sw)
_display_version=(_rev_m.group(1).split('-r',1)[0] if _rev_m else '')
ck('search engines told not to index the app', '<meta name="robots" content="noindex, nofollow">' in s)
ck('homepage version label matches service worker', bool(_display_version) and f'<span class="appVersion" aria-label="App version">{_display_version}</span>' in s)
# Launch is cache-only: no network request for a cached file.
ck('service worker no forced startup update/reload', 'reg.update()' not in s and 'controllerchange' not in s and 'location.reload()' not in s)
required={
    './','./index.html','./app.css','./copy.js','./app.js','./manifest.webmanifest','./apple-touch-icon.png','./icon-192.png','./icon-512.png','./icon-maskable-512.png',
    './phone-bottom-icon.png','./scenario-icon-1.png',
    './scenario-icon-2.png','./scenario-icon-3.png','./scenario-icon-4.png','./libphonenumber-mobile.js'
}
m=re.search(r'const ASSETS=\[(.*?)\];',sw,re.S)
assets=set(re.findall(r'"([^"]+)"',m.group(1))) if m else set()
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
ck('phone CDN removed', 'cdn.jsdelivr.net/npm/libphonenumber-js' not in s and 'cdn.jsdelivr.net/npm/libphonenumber-js' not in sw)

# Android cold-start optimisation (static routes + phone-input idle window).
ck('SW registers in phone-input idle window only', s.count('navigator.serviceWorker.register(')==1 and 'function startServiceWorker(){' in s and 'postMessage({type:"refresh"})' in s)
ck('phone-input idle window runs after load', 'window.addEventListener("load",openPhoneWindow,{once:true});' in s and 'requestIdleCallback(fn,{timeout:1000})' in s)

# Authorized Scenario 4 Flight Type change.

# Priority regression locks: these target the real-device failures that hash-only checks missed.
ck('legacy Android JS: no optional chaining', '?.' not in s)
ck('legacy Android JS: no native replaceChildren dependency', '.replaceChildren(' not in s and 'replaceChildrenCompat' in s)
ck('legacy Android Home: critical row geometry uses explicit flex margins', '#s-scenario .choice{min-height:80px;border-radius:18px;padding:8px 14px 8px 12px;display:flex;gap:0;' in s and '#s-scenario .ctext{flex:1 1 auto;' in s and 'margin-left:14px' in s and '#s-scenario .chev{flex:0 0 20px;margin-left:14px;' in s)
ck('legacy Android Passenger Type: action-icon spacing is explicit', '#s-calltype .actIco,#s-misstype .actIco{flex:none;width:26px;height:26px;margin-left:10px' in s and '#s-calltype .choice .chev,#s-misstype .choice .chev{font-size:26px;width:14px;margin-left:10px' in s)

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

# Privacy lock: the privacy section of verify_changed.py is itself hash-locked, so it cannot be
# weakened quietly. Changing it means recomputing locks.json "privacy", which the handoff must list.
_vc=(r/'verify_changed.py').read_text(encoding='utf-8')
_pm=re.search(r'# ---- privacy lock .*?(?=# ---- summary)',_vc,re.S)
ck('privacy lock present in verify_changed.py', bool(_pm),safety=True)
ck('privacy lock unchanged (locks.json privacy)', bool(_pm) and hashlib.sha256(_pm.group(0).encode()).hexdigest()==LOCKS.get('privacy',{}).get('verify_changed_sha256'),safety=True)
_priv=LOCKS.get('privacy',{})
ck('privacy lock: phone library is the pinned official build', hashlib.sha256((r/'libphonenumber-mobile.js').read_bytes()).hexdigest()==_priv.get('phone_library_sha256'),safety=True)
ck('privacy lock: sw.js unchanged apart from CACHE_REV', hashlib.sha256(re.sub(r'const CACHE_REV="[^"]+";','const CACHE_REV="*";',sw).encode()).hexdigest()==_priv.get('service_worker_sha256'),safety=True)
ck('privacy lock: Content-Security-Policy present and unchanged', '<meta http-equiv="Content-Security-Policy" content="'+_priv.get('csp','-')+'">' in s and s.find('Content-Security-Policy')<s.find('<link rel="stylesheet"'),safety=True)

# Test probe (app.js [test probe]): built only when navigator.webdriver is true, so it never exists on a
# staff phone. The browser safety layer also checks it is absent when webdriver is false.
_probe_js='if(navigator.webdriver===true){\n    Object.defineProperty(window,"__findPaxProbe",{value:Object.freeze({check:probeCheck,message:probeMessage})});\n  }'
ck('test probe exists only under automated tests (navigator.webdriver)', app_js.count('__findPaxProbe')==1 and app_js.count(_probe_js)==1
   and app_js.count('probeCheck')==2 and app_js.count('probeMessage')==2 and '__findPaxProbe' not in copy_js+s_html,safety=True)

# Packaging hygiene: temporary Python files are never valid release content.
_junk=[p.relative_to(r).as_posix() for p in r.rglob('*') if p.is_file() and ('__pycache__' in p.parts or p.suffix in ('.pyc','.pyo'))]
ck('release tree contains no Python temp files', not _junk)

# Anti-bloat budget is lock-protected: raising it is a reviewed lock change, not a way to silence the gate.
_vbudget=r/'verification_budget.json'
_vlock=LOCKS.get('verification',{})
ck('verification budget file is present', _vbudget.is_file())
ck('verification budget unchanged (locks.json verification)', _vbudget.is_file() and hashlib.sha256(_vbudget.read_bytes()).hexdigest()==_vlock.get('budget_sha256'))

if STATIC:
    # Called by verify_changed.py: static lock checks only, no browser, no SHA write.
    print(('FAIL' if bad else 'PASS')+f': static lock checks ({N_PASS} passed)')
    sys.exit(1 if bad else 0)

STATIC_LOCK_PASS=N_PASS
STATIC_LOCK_BAD=bad

# Hygiene, colour lock and wiring for the whole tree (the static locks above already ran).
# A failing privacy line from verify_changed.py is a safety failure.
def run_live(cmd):
    """Stream a sub-suite. Prints only non-PASS lines unless -v; collects its LAYER totals.
    Returns (returncode, pass_count, privacy_fail_lines)."""
    pr=subprocess.Popen(cmd,cwd=r,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,encoding='utf-8',errors='replace',bufsize=1)
    n=priv=0
    for line in pr.stdout:
        if line.startswith('LAYER '):
            k,*v=line.split()[1:]
            if v==['skip']: LAYER_SKIP.add(k)
            else: LAYER_SUM[k][0]+=int(v[0]); LAYER_SUM[k][1]+=int(v[1])
            continue
        if line.startswith('PASS'):
            n+=1
            if VERBOSE: print(line,end='',flush=True)
            continue
        if line.startswith('FAIL privacy lock'): priv+=1
        print(line,end='',flush=True)
    return pr.wait(),n,priv

LAYERS=[('safety','安全'),('send','送出內容'),('clear','資料清除'),('input','輸入規則'),('flow','流程'),('open','能開能更新'),('look','外觀')]
LAYER_SUM={k:[0,0] for k,_ in LAYERS}
LAYER_SKIP=set()
_rc,_n,_priv=run_live([sys.executable,str(r/'verify_changed.py'),'--all','--no-static'])
N_PASS+=_n
ck('hygiene, colour lock and wiring (verify_changed.py --all)', _rc==0, safety=_priv>0)
STATIC_BAD=bad
STATIC_PASS=N_PASS

# Appearance ("look") in --fast runs only when something that shapes the screen changed since the last
# passing check: app.css, index.html, the layout part of app.js (from its [render] marker to the end) or a
# browser-test file. SHA256SUMS.txt records each file plus that app.js part as "app.js#layout".
LAYOUT_MARK='  // ==== [render] ===='
def _sha_file(f): return hashlib.sha256((r/f).read_bytes()).hexdigest() if (r/f).is_file() else ''
def _app_layout_sha(): return hashlib.sha256(app_js[app_js.find(LAYOUT_MARK):].encode('utf-8')).hexdigest() if LAYOUT_MARK in app_js else ''
def look_changed():
    sums={}
    for line in ((r/'SHA256SUMS.txt').read_text(encoding='utf-8') if (r/'SHA256SUMS.txt').is_file() else '').splitlines():
        if '  ' in line: h,f=line.split('  ',1); sums[f]=h
    now={f:_sha_file(f) for f in ['app.css','index.html','verify_behavior.py']+sorted(p.name for p in r.glob('vb_*.py'))}
    now['app.js#layout']=_app_layout_sha()
    return sorted(f for f,h in now.items() if not h or sums.get(f)!=h)

if SAFETY_FAIL:
    print('FAIL 安全（靜態隱私鎖）失敗：瀏覽器檢查沒有執行。先修好上面的 privacy lock。',flush=True)
    LAYER_SUM['safety'][1]+=SAFETY_FAIL
    LAYER_SKIP.update(k for k,_ in LAYERS if k!='safety')
else:
    look=FULL or '--look' in sys.argv
    if FAST and not look and '--no-look' not in sys.argv:
        _changed=look_changed(); look=bool(_changed)
        print('--- 外觀：'+('有改動，會執行（'+', '.join(_changed[:4])+('…' if len(_changed)>4 else '')+'）' if look else '沒有改動，略過')+' ---',flush=True)
    print('--- BROWSER: '+('FULL' if FULL else 'FAST')+' (安全先跑；安全失敗才中斷) ---',flush=True)
    cmd=[sys.executable,str(r/'verify_behavior.py'),'--full' if FULL else '--fast','--jobs',JOBS]+([] if look else ['--no-look'])+(['--timing'] if '--timing' in sys.argv else [])
    _rc,_n,_=run_live(cmd); N_PASS+=_n
    ck('browser checks ('+('every test once' if FULL else 'FAST selection')+')', _rc==0)
    if FULL and 'safety' not in LAYER_SKIP and LAYER_SUM['safety'][1]==0:
        # Service Worker: install, launch, offline, update, broken deploy, cache miss, with and
        # without Static Routing (plus upgrade from a previous build when --previous DIR is given).
        print('--- SERVICE WORKER (能開能更新) ---', flush=True)
        sw_cmd=[sys.executable, str(r/'verify_behavior.py'), '--sw', '--jobs', JOBS if '--jobs' in sys.argv else '2']  # the two modes are independent
        if '--previous' in sys.argv: sw_cmd+=['--previous', sys.argv[sys.argv.index('--previous')+1]]
        _rc3,_n,_=run_live(sw_cmd); N_PASS+=_n
        ck('service worker scenarios (install, launch, offline, update, broken deploy, cache miss)', _rc3==0)

def _mark(k):
    if k in LAYER_SKIP and not sum(LAYER_SUM[k]): return '未執行' if LAYER_SUM['safety'][1] or k!='look' else '略過'
    return '✓' if not LAYER_SUM[k][1] else f'✗ {LAYER_SUM[k][1]}'
print('層級：靜態 '+('✓' if not STATIC_BAD else '✗')+'  '+'  '.join(f'{name} {_mark(k)}' for k,name in LAYERS),flush=True)

# SHA256SUMS records the verified tree. Written only when every check passed.
# Repository / hosting plumbing is not part of the release: .git*, .github, .nojekyll, CNAME.
def _release_file(p):
    rel=p.relative_to(r)
    if p.name in ('SHA256SUMS.txt','verification_report.json','.nojekyll','CNAME') or '__pycache__' in rel.parts: return False
    return not any(x.startswith('.git') for x in rel.parts)
if METRICS:
    print(f'METRIC static {STATIC_LOCK_PASS} '+('PASS' if not STATIC_LOCK_BAD else 'FAIL'))
    for _k,_ in LAYERS:
        _p,_f=LAYER_SUM[_k]
        _state='SKIP' if _k in LAYER_SKIP and not (_p or _f) else ('PASS' if _f==0 else 'FAIL')
        print(f'METRIC layer {_k} {_p} {_f} {_state}')

if not bad:
    _files=sorted(p.relative_to(r).as_posix() for p in r.rglob('*') if p.is_file() and _release_file(p))
    _lines=[hashlib.sha256((r/f).read_bytes()).hexdigest()+'  '+f for f in _files]
    _lines.insert(_files.index('app.js')+1,_app_layout_sha()+'  app.js#layout')
    (r/'SHA256SUMS.txt').write_text(''.join(x+'\n' for x in _lines),encoding='utf-8')

_mode='FULL' if FULL else 'FAST'
if bad:
    print(f'FAIL: {_mode} check — fix the FAIL lines above. SHA256SUMS.txt was not updated.')
    sys.exit(1)
print(f'PASS: {_display_version} {_mode} check — {N_PASS} checks passed in {time.time()-T0:.0f}s (--jobs {JOBS}). SHA256SUMS.txt updated.')
