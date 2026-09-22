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
    marker=f"  function {name}("
    try: start=source.index(marker)
    except ValueError: return None
    m=re.search(r"\n  function \w+\(",source[start+1:])
    end=start+1+m.start() if m else len(source)
    return source[start:end].rstrip()

failures=[]
def check(label,ok,detail=''):
    print(('PASS' if ok else 'FAIL'),label+(f' — {detail}' if detail else ''))
    if not ok: failures.append(label)

print('Find Pax v1.0.6 Release Guard')
print('Baseline status:',lock.get('status'))
check('baseline is LOCKED',lock.get('status')=='LOCKED')
pm=lock['protected']['message_copy']
check('message master version',str(master.get('version'))==str(pm['message_master_version']))
check('message master SHA-256',sha_file(master_path)==pm['message_master_sha256'])
check('Japanese Scenario 1 exists in master',bool(master.get('scenarios',{}).get('scenario1_missing_baggage_xray',{}).get('ja')))
for name,expected in pm['functions'].items():
    body=extract_func(src,name); check('copy function '+name,body is not None and sha_text(body)==expected)
check('message-copy lock version',copy_lock.get('message_master_version')==pm['message_master_version'])
check('message-copy master hash',copy_lock.get('message_master_sha256')==pm['message_master_sha256'])

pp=lock['protected']['phone_validation']
for name,expected in pp['functions'].items():
    body=extract_func(src,name); check('phone function '+name,body is not None and sha_text(body)==expected)

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
    except Exception as e:
        check('Japan +81 runtime cases',False,str(e))
else:
    check('Japan +81 runtime cases',False,'validatePhone missing')

jp=lock['protected']['scenario1_japanese_sms']
for name,expected in jp['functions'].items():
    body=extract_func(src,name); check('Japanese SMS function '+name,body is not None and sha_text(body)==expected)
lang_match=re.search(r'<div class="seg" id="previewLangSeg".*?</div>',src,re.S)
check('Japanese language selector block',bool(lang_match) and sha_text(lang_match.group(0).strip())==jp['language_selector_html_sha256'])
for marker in jp['required_markers']: check('required marker '+marker,marker in src)
approved_ja=jp.get('approved_japanese_sms_copy','')
check('approved Japanese SMS copy in executable', approved_ja in src)
check('Japanese SMS has no flight/SEC/date suffix', 'if(S.order==="ja") return ja+"\\n\\n"+tag;' not in src and 'if(S.order==="ja") return ja;' in src)
sw=(root/'sw.js').read_text(encoding='utf-8')
check('service worker v1.0.6','const APP_VERSION="v1.0.6";' in sw)

if failures:
    print('\nRELEASE BLOCKED. Protected baseline changed or a regression test failed.')
    print('Do not update the lock merely to make the test pass. Restore the approved baseline, or obtain explicit approval for the protected change.')
    sys.exit(1)
print('\nPASS: locked message copy, Japan phone validation, and Scenario 1 Japanese SMS routing all match the approved baseline.')
