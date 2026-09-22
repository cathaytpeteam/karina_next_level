from pathlib import Path
import json,hashlib,re,sys,subprocess
r=Path(__file__).parent;s=(r/'index.html').read_text();b=json.loads((r/'baseline-lock.json').read_text());c=json.loads((r/'message-copy-lock.json').read_text());m=json.loads((r/'message-master.json').read_text())
def sh(x):return hashlib.sha256(x.encode()).hexdigest()
def ef(n):
 L=s.splitlines();i=next((i for i,x in enumerate(L) if x.startswith('  function '+n+'(')),None)
 if i is None:return None
 for j in range(i+1,len(L)):
  if L[j]=='  }':return '\n'.join(L[i:j+1])
def ec(n):
 L=s.splitlines();i=next((i for i,x in enumerate(L) if x.startswith('  const '+n+'=')),None)
 if i is None:return None
 for j in range(i+1,len(L)):
  if L[j]=='  };':return '\n'.join(L[i:j+1])
def ck(n,x):
 print(('PASS' if x else 'FAIL'),n)
 if not x: global bad;bad=True
bad=False
ck('release',b['release']=='v1.0.15');ck('Language heading','Message Language' not in s and 'First Message Language' not in s and '>Language<' in s)
ck('Scenario 1 Join Japanese',b['protected']['japanese_sms']['scenario1_approved_copy'] in ef('textMiss'))
ck('Scenario 1 Transit Japanese',b['protected']['scenario1_transit_copy']['ja'] in ef('textMissTransit'))
ck('Scenario 3 no Japanese','const ja=' not in ef('textWpp'))
ck('general whitelist',all(('"'+x[2:]+'"') in s for x in b['protected']['flight_rules_v114']['general_cx']))
ck('S1 Join whitelist','S.missMode==="join"?generalCxOk' in s);ck('S1 Transit special','S.missMode==="transit"?transitCxOk' in s)
ck('S2 Join whitelist','S.callMode==="join") return generalCxOk' in s);ck('S2 Transit special','S.callMode==="transit") return transitCxOk' in s)
ck('S4 whitelist','dflight:()=>isFlt(v("dFlight"))&&generalCxOk' in s);ck('S3 arrival exception','wflight:()=>isFlt(v("wFlight"))' in s)
ck('Connecting exception','dtransfer:()=>isAir(v("tA"))&&isFlt(v("tN"))' in s);ck('Protect exception','isAir(v("altA"))&&isFlt(v("altN"))' in s)
ck('Transit IATA UI',all(x in s for x in ['missTransitIataValue','callTransitIataValue','callSec']))
ck('Origin IATA mapping',all(x in s for x in ['"450":"HKG"','"530":"HKG"','"564":"HKG"','"451":"NRT"','"531":"NGO"','"565":"KIX"']))
ck('Destination IATA preserved',all(x in s for x in ['"450":"NRT"','"564":"KIX"','"530":"NGO"','"451":"HKG"','"565":"HKG"','"531":"HKG"']))
ck('+81 validation', 'if(n.startsWith("81"))' in s and '/^[6789]\d{9}$/' in s)
ck('SMS routing','isiOS?"&":"?"' in s);ck('WhatsApp routing','whatsapp://send?phone=' in s and 'https://wa.me/' in s)
for n,h in c['functions'].items():ck('copy '+n,sh(ef(n))==h)
for n,h in c['constants'].items():ck('constant '+n,sh(ec(n))==h)
ck('master hash',hashlib.sha256((r/'message-master.json').read_bytes()).hexdigest()==c['message_master_sha256'])
ck('service worker','const APP_VERSION="v1.0.15";' in (r/'sw.js').read_text())
if bad:sys.exit(1)
print('PASS: v1.0.15 full release guard')
