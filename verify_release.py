from pathlib import Path
import json, hashlib, re, sys

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
ck('Protect exception', 'isCarrier(v("altA"))&&isFlt(v("altN"))' in s)
ck('Alphanumeric airline designator', 'const isCarrier=s=>/^[A-Z0-9]{2}$/.test(s);' in s and 'replace(/[^A-Za-z0-9]/g,"")' in s)

# Transit SEC origin UI/rules. Scenario 2 now intentionally uses callSecPrefix.
ck('Transit SEC origin UI', all(x in s for x in ['missTransitIataValue','callSecPrefix','callSec']))
ck('No obsolete callTransitIataValue requirement', 'callTransitIataValue' not in s)
ck('Origin IATA mapping', all(x in s for x in ['"450":"HKG"','"530":"HKG"','"564":"HKG"','"451":"NRT"','"531":"NGO"','"565":"KIX"']))
ck('Destination IATA preserved', all(x in s for x in ['"450":"NRT"','"564":"KIX"','"530":"NGO"','"451":"HKG"','"565":"HKG"','"531":"HKG"']))
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
ck('Scenario 4 language reset', '$("goDp").onclick=()=>{clearDpCase();flow="dp";S.order="en";S.orderSet=false;go("dflight");};' in s)
ck('Scenario 1 clean re-entry', '$("goMiss").onclick=()=>{clearMissCase();' in s)
ck('Scenario 2 clean re-entry', '$("goCall").onclick=()=>{clearCallCase();' in s)
ck('Scenario 1 type switch guard', 'clearMissForModeChange("join")' in s and 'clearMissForModeChange("transit")' in s and 'clearMissForModeChange("direct")' in s)
ck('Scenario 2 type switch guard', 'clearCallForModeChange("join")' in s and 'clearCallForModeChange("transit")' in s and 'clearCallForModeChange("direct")' in s)
ck('Scenario 2 gate clears on type change', '["callFlight","callSec","callGate"].forEach' in (ef('clearCallForModeChange') or ''))
ck('Call progress stable five-step', 'call:{name:"Call Passenger",steps:["calltype","callflight","callsec","callgate","preview"]}' in s and 'FLOWS.call.steps=' not in s)
ck('Call Directly progress hidden', 'const directPreview=cur==="preview"&&flow==="call"&&S.callNoMessage;' in s and '$("bar").hidden=idx<0||directPreview;' in s)
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
ck('progress includes passenger type', 'progressName+=" "+(S.missMode==="join"?"Join Pax":"Transit Pax")' in s and 'progressName+=" "+(S.callMode==="join"?"Join Pax":"Transit Pax")' in s)
ck('direct phone in confirm details', 'rows.push(["Phone Number",(S.country?flagFor(S.country)+" ":"")+"+"+S.phone])' in s)
ck('direct phone hidden from header', '!directPreview&&(cur!=="preview"||flow==="call")&&S.phone' in s)

# Service Worker checks: defined runtime list, existing local assets, current cache version.
sw=(r/'sw.js').read_text(encoding='utf-8')
ck('service worker version', 'const APP_VERSION="v1.0.16";' in sw)
ck('service worker cache revision', 'const CACHE_REV="r4";' in sw)
ck('service worker ASSETS declared', 'const ASSETS=[' in sw and 'cache.addAll(ASSETS)' in sw)
required={
    './','./index.html','./manifest.webmanifest','./apple-touch-icon.png','./icon-192.png','./icon-512.png',
    './icon-maskable-192.png','./icon-maskable-512.png','./phone-bottom-icon.png','./scenario-icon-1.png',
    './scenario-icon-2.png','./scenario-icon-3.png','./scenario-icon-4.png','./libphonenumber-max.js'
}
m=re.search(r'const ASSETS=\[(.*?)\];',sw,re.S)
assets=set(re.findall(r'"([^"]+)"',m.group(1))) if m else set()
ck('service worker asset list exact', assets==required)
ck('service worker assets exist', all(a=='./' or (r/a[2:]).is_file() for a in assets))
ck('phone library local', './libphonenumber-max.js' in s and './libphonenumber-max.js' in assets and (r/'libphonenumber-max.js').is_file())
ck('phone CDN removed', 'cdn.jsdelivr.net/npm/libphonenumber-js' not in s and 'cdn.jsdelivr.net/npm/libphonenumber-js' not in sw)

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
actual_files={p.relative_to(r).as_posix():p for p in r.rglob('*') if p.is_file() and p.name!='SHA256SUMS.txt' and '__pycache__' not in p.parts}
if sha_ok and set(listed)!=set(actual_files): sha_ok=False
if sha_ok:
    for rel,p in actual_files.items():
        if hashlib.sha256(p.read_bytes()).hexdigest()!=listed.get(rel): sha_ok=False; break
ck('SHA256SUMS integrity',sha_ok)

if bad: sys.exit(1)
print('PASS: v1.0.16 full release guard + UI/state navigation hotfix')
