#!/usr/bin/env python3
from pathlib import Path
import re, hashlib, json, sys
r=Path(__file__).resolve().parent
s=(r/'index.html').read_text(encoding='utf-8')
lock=json.loads((r/'layout-lock.json').read_text(encoding='utf-8'))
def sha(x): return hashlib.sha256(x.encode()).hexdigest()
def fail(msg): print('FAIL layout:',msg); return False
ok=True
found={}
for m in re.finditer(r'<section\b[^>]*\bid="(s-[^"]+)"[^>]*>.*?</section>',s,re.S): found[m.group(1)]=m.group(0)
order=list(found)
if order!=lock['screen_order']:
    ok=fail('screen order changed') and ok
for sid,want in lock['screen_sha256'].items():
    if sid not in found: ok=fail(f'{sid} missing') and ok
    elif sha(found[sid])!=want: ok=fail(f'{sid} protected markup changed') and ok
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
if ok:
    print('PASS layout lock: approved screens, field placement, progress/header and footer are unchanged')
    sys.exit(0)
sys.exit(1)
