from pathlib import Path
import json, hashlib, re, sys, subprocess

r=Path(__file__).resolve().parent
s=(r/'index.html').read_text(encoding='utf-8')
b=json.loads((r/'baseline-lock.json').read_text(encoding='utf-8'))
c=json.loads((r/'message-copy-lock.json').read_text(encoding='utf-8'))

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

bad=False
def ck(n,x):
    global bad
    ok=bool(x)
    print(('PASS' if ok else 'FAIL'),n)
    if not ok: bad=True

ck('release', b.get('release')=='v1.0.16')
ck('Language heading', 'Message Language' not in s and 'First Message Language' not in s and '>Language<' in s)
ck('Scenario 1 Join Japanese', b['protected']['japanese_sms']['scenario1_approved_copy'] in ef('textMiss'))
ck('Scenario 1 Transit Japanese', b['protected']['scenario1_transit_copy']['ja'] in ef('textMissTransit'))
ck('Scenario 3 no Japanese', 'const ja=' not in ef('textWpp'))

# Flight rules and exceptions.
ck('general whitelist', all(('"'+x[2:]+'"') in s for x in b['protected']['flight_rules_v114']['general_cx']))
ck('S1 Join whitelist', 'S.missMode==="join"?generalCxOk' in s)
ck('S1 Transit special', 'S.missMode==="transit"?transitCxOk' in s)
ck('S2 Join whitelist', 'S.callMode==="join") return generalCxOk' in s)
ck('S2 Transit special', 'S.callMode==="transit") return transitCxOk' in s)
ck('S4 whitelist', 'dflight:()=>isFlt(v("dFlight"))&&generalCxOk' in s)
ck('S3 arrival exception', 'wflight:()=>isFlt(v("wFlight"))' in s)
ck('Connecting exception', 'dtransfer:()=>isCarrier(v("tA"))&&isFlt(v("tN"))' in s)
ck('Protect CX whitelist + same-flight guard', 'isCarrier(v("altA"))&&isFlt(v("altN"))&&protectFlightOk(v("altA"),v("altN"),v("dFlight"))' in s and 'sameProtectedCxFlight' in s and 'CX flight must depart TPE' in s and 'Same as Flight from TPE — not allowed' in s)
ck('Alphanumeric airline designator', 'const isCarrier=s=>/^[A-Z0-9]{2}$/.test(s);' in s and 'replace(/[^A-Za-z0-9]/g,"")' in s)

# SEC origin UI/rules. Scenario 1 keeps SEC; Scenario 2 Final Call intentionally has no SEC page.
ck('Scenario 1 SEC origin UI', all(x in s for x in ['mSecPrefix','mSec']) and 'missTransitIataValue' not in s)
ck('Scenario 2 SEC removed', 'id="s-callsec"' not in s and 'callSec' not in s and '"callsec"' not in s)
ck('No obsolete callTransitIataValue requirement', 'callTransitIataValue' not in s)
ck('Origin IATA mapping', all(x in s for x in ['"450":"HKG"','"530":"HKG"','"564":"HKG"','"451":"NRT"','"531":"NGO"','"565":"KIX"']))
ck('Destination IATA preserved', all(x in s for x in ['"450":"NRT"','"564":"KIX"','"530":"NGO"','"451":"HKG"','"565":"HKG"','"531":"HKG"']))
ck('Final Call Transit Dep from row', 'if(S.callMode==="transit"){const origin=transitOriginIata(callFlightNumber());if(origin)rows.push(["Dep from",origin]);}' in s)
ck('SEC prefix TPE/Transit mapping', all(x in s for x in ['"450":{join:"TPE",transit:"HKG"}','"451":{join:"TPE",transit:"NRT"}','"531":{join:"TPE",transit:"NGO"}','"565":{join:"TPE",transit:"KIX"}']))

# Phone validation hardening.
vp=ef('validatePhone') or ''
ck('+81 mobile-only validation', 'if(n.startsWith("81"))' in vp and r'/^[6789]0\d{8}$/' in vp and '!mobile.startsWith("800")' in vp)
ck('Strict phone validity', 'typeof ph.isValid==="function"' in vp and 'if(!ph.isValid()) continue;' in vp)
ck('Canonical E.164 output', 'String(ph.number||"").replace(/^\\+/,"")' in vp)
ck('SMS routing', 'isiOS?"&":"?"' in s)
ck('WhatsApp routing', 'whatsapp://send?phone=' in s and 'https://wa.me/' in s)

# Cross-scenario consistency + UI/state navigation fixes.
ck('Scenario 3 language reset', '$("goWpp").onclick=()=>{clearWppCase();flow="wpp";S.order="zh";S.orderSet=false;go("wflight");};' in s)
ck('Scenario 4 language reset', '$("goDp").onclick=()=>{clearDpCase();flow="dp";S.order="en";S.orderSet=false;go("dstatus");};' in s)
ck('Scenario 1 clean re-entry', '$("goMiss").onclick=()=>{clearMissCase();' in s)
ck('Scenario 2 clean re-entry', '$("goCall").onclick=()=>{clearCallCase();' in s)
ck('Scenario 1 type switch guard', 'clearMissForModeChange("join")' in s and 'clearMissForModeChange("transit")' in s and 'clearMissForModeChange("direct")' in s)
ck('Scenario 2 type switch guard', 'clearCallForModeChange("join")' in s and 'clearCallForModeChange("transit")' in s and 'clearCallForModeChange("direct")' in s)
ck('Scenario 2 gate clears on type change', '["callFlight","callGate"].forEach' in (ef('clearCallForModeChange') or ''))
ck('Call progress stable four-step', 'call:{name:"Final Call",steps:["calltype","callflight","callgate","preview"]}' in s and 'FLOWS.call.steps=' not in s)
ck('Call Directly progress 1/1', 'const directProgress=directPreview;' in s and 'textContent:"1/1"' in s and 'document.createTextNode(" - Call Directly")' in s)
cp=ef('closePreviewEditor') or ''
ck('Read-only preview does not create draft', 'edits[S.order]=m.value' not in cp)
np=ef('normalizePhone') or ''
ck('Blocked warning before phone validity', 'const blockedDigits=blockedCandidateFor(n);' in np and np.find('const blockedDigits=blockedCandidateFor(n);') < np.find('const p=validatePhone(n);'))
dc=ef('dateCode') or ''
ck('Taipei dateCode timezone', 'timeZone:"Asia/Taipei"' in dc and 'getUTCDate()' in dc)

# Executable-copy locks.
for n,h in c['functions'].items(): ck('copy '+n, ef(n) is not None and sh(ef(n))==h)
for n,h in c.get('constants',{}).items(): ck('constant '+n, ec(n) is not None and sh(ec(n))==h)
ck('master hash', hashlib.sha256((r/'message-master.json').read_bytes()).hexdigest()==c['message_master_sha256'])

# Protected behavior hashes that were previously stored but not enforced.
for section in ('phone_validation','japanese_sms','datetime'):
    funcs=b['protected'].get(section,{}).get('functions',{})
    for n,h in funcs.items():
        body=ef(n)
        ck('protected '+n, body is not None and sh(body)==h)

# UI regression checks: passenger type in progress and Direct phone placement.
ck('progress labels approved', 'const progressText=(idx+1)+"/"+f.steps.length;' in s and 'document.createTextNode(f.name+" - ")' in s and 'document.createTextNode(" - "+passengerType)' in s and 'flow==="miss" && cur!=="misstype" && (S.missMode==="join"||S.missMode==="transit")' in s and 'flow==="call" && cur!=="calltype" && (S.callMode==="join"||S.callMode==="transit")' in s and '.step{font-size:20px;font-weight:700' in s and 'className:"progressCount"' in s and '.step .progressCount{color:#718584' in s)
ck('direct phone in confirm details', 'rows.push(["Phone Number",(S.country?flagFor(S.country)+" ":"")+"+"+S.phone])' in s)
ck('direct phone hidden from header', '!directPreview&&(cur!=="preview"||flow==="call")&&S.phone' in s)

# Message Preview is intentionally read-only. Editing/copying is delegated to WhatsApp/SMS.
ck('preview readonly', '<textarea class="msg" id="msg" autocomplete="off" readonly' in s)
ck('preview edit/copy controls removed', 'id="editMsg"' not in s and 'id="copyMsg"' not in s and 'Copy Text' not in s and 'Done Editing' not in s)

# Explicitly authorized final visual/copy tuning.
ck('language order labels 18px/700', '.msgToggle small{font-size:18px;font-weight:700' in s)
ck('Scenario 3 step 2/4 restored and 4/4 unclaimed bag label aligned', '<section class="screen" id="s-bag1" hidden>\n      <h1>Bag Tag 1</h1>\n      <p class="bagHelp" lang="zh-Hant">無人領取的行李</p>' in s and 'className="bagConfirmNote"' in s and '.sum dd .bagConfirmNote{font-size:18px' in s)
ck('Scenario 1 Join suffix compact', 'const tag=String(Number(v("mFlight")))+"/"+String(Number(v("mSec"))).padStart(3,"0");' in s and 'const tag="cx"' not in s)

# Explicitly authorized consistency fixes (r9).
ck('history Back/Forward state aware', 'history.replaceState({findPax:true,pos:0,id:"phone"}' in s and 'history.pushState({findPax:true,pos:navPos,id}' in s and 'navPos=st.pos;' in s and 'showScreen(st.id);' in s)
ck('Arrangement no arbitrary break', '.sum dt{color:var(--muted);flex:0 1 auto;min-width:0;display:flex;flex-wrap:wrap;align-items:center;gap:4px 14px;overflow-wrap:normal;word-break:normal}' in s)
ck('Final Call flight alignment selectors', '#s-callflight .field .code, #s-callgate .field .code{width:72px' in s and '#s-callflight .field input:not(.code), #s-callgate .field input:not(.code){flex:0 0 auto' in s and '#s-callflight .field .code .code' not in s and '#s-callflight .field input:not(.code) input:not(.code)' not in s)
ck('Scenario 1 confirm SEC includes IATA', '["Sec",(secPrefix(v("mFlight"),S.missMode)||"")+" "+String(Number(v("mSec"))).padStart(3,"0")]' in s)
ck('listed CX helper removed', 'Please select a listed CX flight' not in s)

# Service Worker checks: defined runtime list, existing local assets, current cache version.
sw=(r/'sw.js').read_text(encoding='utf-8')
ck('service worker version', 'const APP_VERSION="v1.1";' in sw)
ck('service worker cache revision', 'const CACHE_REV="r34";' in sw)
_app_m=re.search(r'const APP_VERSION="([^"]+)";',sw)
_rev_m=re.search(r'const CACHE_REV="([^"]+)";',sw)
_display_version=_rev_m.group(1) if _rev_m else ''
ck('homepage version label matches service worker', bool(_display_version) and f'<span class="appVersion" aria-label="App version">{_display_version}</span>' in s)
ck('service worker ASSETS declared', 'const ASSETS=[' in sw and 'cache.addAll(ASSETS)' in sw)
ck('service worker cache-first runtime', 'const cached=await cache.match(key);' in sw and 'if(cached) return cached;' in sw and 'e.waitUntil(network.then(()=>{}).catch(()=>{}));' in sw)
ck('service worker cache write failure isolated', 'await cache.put(key,r.clone()).catch(()=>{});' in sw)
ck('service worker navigation redirect not cached', '!(req.mode==="navigate"&&r.redirected)' in sw)
ck('service worker no forced startup update/reload', 'reg.update()' not in s and 'controllerchange' not in s and 'location.reload()' not in s)
required={
    './','./index.html','./manifest.webmanifest','./apple-touch-icon.png','./icon-192.png','./icon-512.png','./icon-maskable-192.png','./icon-maskable-512.png',
    './phone-bottom-icon.png','./scenario-icon-1.png',
    './scenario-icon-2.png','./scenario-icon-3.png','./scenario-icon-4.png','./libphonenumber-max.js'
}
m=re.search(r'const ASSETS=\[(.*?)\];',sw,re.S)
assets=set(re.findall(r'"([^"]+)"',m.group(1))) if m else set()
ck('service worker asset list exact', assets==required)
manifest=(r/'manifest.webmanifest').read_text(encoding='utf-8')
ck('manifest separates any and maskable icons', all(x in manifest for x in ['./icon-192.png','./icon-512.png','./icon-maskable-192.png','./icon-maskable-512.png','\"purpose\": \"any\"','\"purpose\": \"maskable\"']) and 'any maskable' not in manifest)
ck('maskable icons distinct', hashlib.sha256((r/'icon-192.png').read_bytes()).hexdigest()!=hashlib.sha256((r/'icon-maskable-192.png').read_bytes()).hexdigest() and hashlib.sha256((r/'icon-512.png').read_bytes()).hexdigest()!=hashlib.sha256((r/'icon-maskable-512.png').read_bytes()).hexdigest())
ck('service worker assets exist', all(a=='./' or (r/a[2:]).is_file() for a in assets))
ck('phone library local', './libphonenumber-max.js' in s and './libphonenumber-max.js' in assets and (r/'libphonenumber-max.js').is_file())
ck('phone library does not block first paint', '<script src="./libphonenumber-max.js"></script>' not in s and 'requestAnimationFrame(()=>requestAnimationFrame(loadPhoneLibrary))' in s and 'script.async=true;' in s)
ck('startup has no second clear/render pass', 'window.addEventListener("load",()=>{if(stack.length===1&&cur==="phone"){clearFields();render();}});' not in s)
ck('service worker strategy retained while cache revision advances', 'if(cached) return cached;' in sw and 'e.waitUntil(network.then(()=>{}).catch(()=>{}));' in sw)
ck('phone CDN removed', 'cdn.jsdelivr.net/npm/libphonenumber-js' not in s and 'cdn.jsdelivr.net/npm/libphonenumber-js' not in sw)

# Authorized Scenario 4 Flight Type change.
ck('Scenario 4 Flight Type first', 'dp:{name:"Disrupted Pax",steps:["dstatus","dflight","dtransfer","darrange","darrive","preview"]}' in s and 'go("dstatus")' in s)
ck('Scenario 4 Flight Type copy', '<h1>Flight Type</h1>' in s and '>Tight Connection<' in s and '>Delayed<' in s and '>Suspended<' in s)
ck('Scenario 4 Flight Type behaves like Passenger Type', 'cur!=="calltype"&&cur!=="misstype"&&cur!=="dstatus"' in s and 'cur!=="scenario"&&cur!=="calltype"&&cur!=="misstype"&&cur!=="dstatus"' in s)
ck('Scenario 4 Delayed time lives on step 2 only', 'id="s-dflight"' in s and 'id="delayWrap"' in s and 'if(cur==="dflight"){' in s and '$("delayWrap").hidden=S.status!=="delayed";' in s and 'dflight:()=>isFlt(v("dFlight"))&&generalCxOk(v("dFlight"))&&(S.status!=="delayed"||timeOk("delayTime"))' in s)

# Layout lock: approved screen structure/field placement may change only with explicit user approval.
layout_run=subprocess.run([sys.executable, str(r/'verify_layout.py')], cwd=r, capture_output=True, text=True)
ck('layout lock', layout_run.returncode==0)
if layout_run.returncode!=0 and layout_run.stdout: print(layout_run.stdout.strip())

# Navigation lock: step counts/order and routing are protected independently from layout markup.
nav_run=subprocess.run([sys.executable, str(r/'verify_navigation.py')], cwd=r, capture_output=True, text=True)
ck('navigation lock', nav_run.returncode==0)
if nav_run.returncode!=0 and nav_run.stdout: print(nav_run.stdout.strip())

# Flow behaviour: drives the real UI in headless Chromium and executes every outgoing
# branch in flow-behavior-spec.json (plus Back/Forward, guards, state rules, send URLs).
beh_run=subprocess.run([sys.executable, str(r/'verify_behavior.py')], cwd=r, capture_output=True, text=True)
ck('flow behaviour (all branches, Back/Forward, guards, state rules)', beh_run.returncode==0)
if beh_run.returncode!=0:
    print('\n'.join(x for x in (beh_run.stdout+beh_run.stderr).splitlines() if not x.startswith('PASS'))[-4000:])

# SHA256SUMS integrity and completeness (SHA file itself is intentionally excluded).
sha_path=r/'SHA256SUMS.txt'
sha_ok=sha_path.exists()
listed={}
if sha_ok:
    for line in sha_path.read_text(encoding='utf-8').splitlines():
        if not line.strip(): continue
        parts=line.split('  ',1)
        if len(parts)!=2: sha_ok=False; break
        listed[parts[1]]=parts[0]
# Repository / hosting plumbing is not part of the app release: .git, .github (CI workflow),
# .gitignore/.gitattributes, and GitHub Pages files (.nojekyll, CNAME).
def _release_file(p):
    rel=p.relative_to(r)
    if p.name in ('SHA256SUMS.txt','.nojekyll','CNAME') or '__pycache__' in rel.parts: return False
    return not any(x.startswith('.git') for x in rel.parts)
actual_files={p.relative_to(r).as_posix():p for p in r.rglob('*') if p.is_file() and _release_file(p)}
if sha_ok and set(listed)!=set(actual_files): sha_ok=False
if sha_ok:
    for rel,p in actual_files.items():
        if hashlib.sha256(p.read_bytes()).hexdigest()!=listed.get(rel): sha_ok=False; break
ck('SHA256SUMS integrity',sha_ok)

if bad: sys.exit(1)
print('PASS: v1.1 Golden Baseline + layout lock')
