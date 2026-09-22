from pathlib import Path
import hashlib, json, re, sys, subprocess

root=Path(__file__).resolve().parent
src=(root/'index.html').read_text(encoding='utf-8')
lock=json.loads((root/'baseline-lock.json').read_text(encoding='utf-8'))
copy_lock=json.loads((root/'message-copy-lock.json').read_text(encoding='utf-8'))
master_path=root/'message-master.json'
master=json.loads(master_path.read_text(encoding='utf-8'))

def sha_text(s): return hashlib.sha256(s.encode('utf-8')).hexdigest()
def sha_file(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def extract_func(source,name):
    lines=source.splitlines()
    start=next((i for i,l in enumerate(lines) if l.startswith(f'  function {name}(')),None)
    if start is None: return None
    for j in range(start+1,len(lines)):
        if lines[j]=='  }': return '\n'.join(lines[start:j+1])
    return None

def extract_const(source,name):
    lines=source.splitlines()
    start=next((i for i,l in enumerate(lines) if l.startswith(f'  const {name}=')),None)
    if start is None: return None
    for j in range(start+1,len(lines)):
        if lines[j]=='  };': return '\n'.join(lines[start:j+1])
    return None

failures=[]
def check(label,ok,detail=''):
    print(('PASS' if ok else 'FAIL'),label+(f' — {detail}' if detail else ''))
    if not ok: failures.append(label)

print('Find Pax v1.0.8 Release Guard')
print('Baseline status:',lock.get('status'))
check('baseline is LOCKED',lock.get('status')=='LOCKED')

pm=lock['protected']['message_copy']
check('message master version',str(master.get('version'))==str(pm['message_master_version']))
check('message master status',master.get('status')=='LOCKED')
check('message master SHA-256',sha_file(master_path)==pm['message_master_sha256'])
check('message-copy lock version',copy_lock.get('message_master_version')==pm['message_master_version'])
check('message-copy master hash',copy_lock.get('message_master_sha256')==pm['message_master_sha256'])
for name,expected in pm['functions'].items():
    body=extract_func(src,name)
    check('copy function '+name,body is not None and sha_text(body)==expected)
for name,expected in pm.get('constants',{}).items():
    body=extract_const(src,name)
    check('copy constant '+name,body is not None and sha_text(body)==expected)

# Japan +81 phone behavior stays unchanged.
pp=lock['protected']['phone_validation']
for name,expected in pp['functions'].items():
    body=extract_func(src,name)
    check('phone function '+name,body is not None and sha_text(body)==expected)
validate_body=extract_func(src,'validatePhone')
if validate_body:
    accepted={
      '819012345678':'819012345678','+819012345678':'819012345678','8109012345678':'819012345678','81009012345678':'819012345678','810009012345678':'819012345678',
      '818012345678':'818012345678','817012345678':'817012345678','816012345678':'816012345678','810008012345678':'818012345678','810007012345678':'817012345678','810006012345678':'816012345678'}
    rejected=['812012345678','8102012345678','81002012345678','815012345678','8105012345678','81005012345678','81312345678','810312345678','81612345678','810612345678','81901234567','8190123456789','8100009012345678']
    js='const digits=s=>String(s||"").replace(/\\D/g,"");\nconst window={libphonenumber:{}};\nconst PHONE_META={codes:["81"],byCode:{"81":["JP"]}};\nconst callingCodeFor=n=>n.startsWith("81")?"81":"";\n'+validate_body+'\nconst accepted='+json.dumps(accepted)+';\nconst rejected='+json.dumps(rejected)+';\nlet bad=[];\nfor(const [raw,want] of Object.entries(accepted)){const p=validatePhone(raw);if(!p||p.digits!==want||p.country!=="JP")bad.push(`accept ${raw}: ${JSON.stringify(p)}`)}\nfor(const raw of rejected){const p=validatePhone(raw);if(p)bad.push(`reject ${raw}: ${JSON.stringify(p)}`)}\nif(bad.length){console.error(bad.join("\\n"));process.exit(1)}console.log("Japan cases OK");'
    try:
        cp=subprocess.run(['node','-e',js],capture_output=True,text=True,timeout=15)
        check('Japan +81 runtime cases',cp.returncode==0,(cp.stdout or cp.stderr).strip())
    except Exception as e: check('Japan +81 runtime cases',False,str(e))
else: check('Japan +81 runtime cases',False,'validatePhone missing')

# Japanese SMS routing and approved Scenario 2 mechanics.
jp=lock['protected']['japanese_sms']
for name,expected in jp['functions'].items():
    body=extract_func(src,name)
    check('routing function '+name,body is not None and sha_text(body)==expected)
lang_match=re.search(r'<div class="seg" id="previewLangSeg".*?</div>',src,re.S)
check('Japanese language selector block',bool(lang_match) and sha_text(lang_match.group(0).strip())==jp['language_selector_html_sha256'])
check('Scenario 1 approved Japanese copy',jp['scenario1_approved_copy'] in src)
check('Scenario 1 Japanese has no suffix','if(S.order==="ja") return ja;' in extract_func(src,'textMiss'))
check('Scenario 2 Join Japanese has no suffix','if(S.order==="ja") return ja;' in extract_func(src,'textJoin'))
check('Scenario 2 Transit Japanese has no suffix','if(S.order==="ja") return ja;' in extract_func(src,'textTransit'))
check('Transit Japanese Taipei time marker','現在の台北時間は${taipeiTime()}です。' in extract_func(src,'textTransit'))
check('Join Japanese has no Taipei time','taipeiTime()' not in extract_func(src,'textJoin'))
check('Taipei timezone is explicit','timeZone:"Asia/Taipei"' in extract_func(src,'taipeiTime'))
check('Japanese CTA marker','SMSを送信' in src)
check('Join and Transit Japanese SMS routing','S.callMode==="join"||S.callMode==="transit"' in extract_func(src,'send') and 'S.callMode==="join"||S.callMode==="transit"' in extract_func(src,'sendSMS'))

# Scenario 2 structure and exact flight rules.
s2=lock['protected']['scenario2']
for marker in ['id="callJoin"','>Join Pax</span>','id="callTransit"','>Transit Pax</span>','id="callDirect"','>Call Directly</span>','id="callFlight"']:
    check('Scenario 2 marker '+marker,marker in src)
check('old No message option removed','>No message<' not in src and '>No Message<' not in src)
const_dest=extract_const(src,'TRANSIT_DESTINATIONS')
check('Transit destination mapping lock',const_dest is not None and sha_text(const_dest)==s2['destination_constant_sha256'])
check('Join has no whitelist','return S.callMode==="transit"?Object.prototype.hasOwnProperty.call(TRANSIT_DESTINATIONS,n):S.callMode==="join";' in extract_func(src,'callFlightOk'))
for flt in ['450','451','530','531','564','565']:
    check('Transit flight '+flt,('"'+flt+'":') in const_dest)

# Runtime Scenario 2 flight validation and generated message behavior.
needed=['normalizeCallGate','callGateNumber','callGateFull','callFlightNumber','callFlightFull','callFlightOk','taipeiTime','textJoin','textTransit']
if all(extract_func(src,n) for n in needed) and const_dest:
    js='''const digits=s=>String(s||"").replace(/\\D/g,"");\nlet vals={callFlight:"",callGateZone:"B",callGate:"9"};\nconst v=id=>vals[id]||"";\nconst S={callMode:"join",order:"zh"};\n'''+ '\n'.join([extract_func(src,n) for n in ['normalizeCallGate','callGateNumber','callGateFull','callFlightNumber','callFlightFull']])+'\n'+const_dest+'\n'+extract_func(src,'callFlightOk')+'\n'+extract_func(src,'taipeiTime')+'\n'+extract_func(src,'textJoin')+'\n'+extract_func(src,'textTransit')+'''\nlet bad=[];\nfor(const f of ["1","360","999"]){vals.callFlight=f;S.callMode="join";if(!callFlightOk())bad.push("join rejects "+f)}\nfor(const f of ["450","451","530","531","564","565"]){vals.callFlight=f;S.callMode="transit";if(!callFlightOk())bad.push("transit rejects "+f)}\nfor(const f of ["360","999","452"]){vals.callFlight=f;S.callMode="transit";if(callFlightOk())bad.push("transit accepts "+f)}\nvals.callFlight="450";S.callMode="join";S.order="ja";const j=textJoin(true);if(!j.includes("CX450")||!j.includes("B9")||j.includes("台北時間"))bad.push("join ja dynamic");\nS.callMode="transit";S.order="ja";const t=textTransit(true);if(!t.includes("台北発東京（成田）行きCX450便")||!t.includes("B9番搭乗口")||!t.match(/現在の台北時間は\\d{2}:\\d{2}です。/))bad.push("transit ja dynamic");\nS.order="zh";const z=textTransit(true);if(!z.includes("台北往東京成田CX450航班")||!z.includes("B9號登機門"))bad.push("transit zh dynamic");\nif(bad.length){console.error(bad.join("\\n"));process.exit(1)}console.log("Scenario 2 cases OK");'''
    try:
        cp=subprocess.run(['node','-e',js],capture_output=True,text=True,timeout=15)
        check('Scenario 2 runtime cases',cp.returncode==0,(cp.stdout or cp.stderr).strip())
    except Exception as e: check('Scenario 2 runtime cases',False,str(e))
else: check('Scenario 2 runtime cases',False,'required functions missing')

sw=(root/'sw.js').read_text(encoding='utf-8')
check('service worker v1.0.8','const APP_VERSION="v1.0.8";' in sw)

if failures:
    print('\nRELEASE BLOCKED. A locked behavior changed or a regression test failed.')
    print('Restore the approved behavior, or obtain explicit approval before intentionally regenerating the lock.')
    sys.exit(1)
print('\nPASS: v1.0.8 locked copy, phone validation, Scenario 2 structure, destinations, Japanese SMS routing, and Taipei-time rule all match the approved release.')
