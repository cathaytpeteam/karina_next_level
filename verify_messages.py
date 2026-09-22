from pathlib import Path
import hashlib, json, re, sys

root=Path(__file__).resolve().parent
src=(root/'index.html').read_text(encoding='utf-8')
master_path=root/'message-master.json'
lock=json.loads((root/'message-copy-lock.json').read_text(encoding='utf-8'))
master=json.loads(master_path.read_text(encoding='utf-8'))

def sha_text(s): return hashlib.sha256(s.encode('utf-8')).hexdigest()
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

bad=[]
print('Find Pax Message Copy Check')
print('Message Master:',lock['message_master_version'])
master_actual=hashlib.sha256(master_path.read_bytes()).hexdigest()
master_ok=(master_actual==lock['message_master_sha256'] and str(master.get('version'))==str(lock['message_master_version']) and master.get('status')=='LOCKED')
print(('PASS' if master_ok else 'FAIL'),'message-master.json integrity')
if not master_ok: bad.append('message-master.json')

for name,expected in lock['functions'].items():
    body=extract_func(src,name)
    actual=sha_text(body) if body is not None else 'MISSING'
    ok=actual==expected
    print(('PASS' if ok else 'FAIL'),'copy function '+name)
    if not ok: bad.append(name)
for name,expected in lock.get('constants',{}).items():
    body=extract_const(src,name)
    actual=sha_text(body) if body is not None else 'MISSING'
    ok=actual==expected
    print(('PASS' if ok else 'FAIL'),'copy constant '+name)
    if not ok: bad.append(name)

if bad:
    print('\nMessage copy or its locked mapping changed. Do not release until the change is explicitly approved and the lock is intentionally regenerated.')
    sys.exit(1)
print('\nPASS: message master and executable copy match the locked v1.0.15 release.')
