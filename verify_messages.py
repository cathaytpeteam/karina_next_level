from pathlib import Path
import hashlib, json, re, sys

root=Path(__file__).resolve().parent
src=(root/"index.html").read_text(encoding="utf-8")
master_path=root/"message-master.json"
lock=json.loads((root/"message-copy-lock.json").read_text(encoding="utf-8"))
master=json.loads(master_path.read_text(encoding="utf-8"))

def extract_func(source,name):
    marker=f"  function {name}("
    try:
        start=source.index(marker)
    except ValueError:
        return None
    m=re.search(r"\n  function \w+\(", source[start+1:])
    end=start+1+m.start() if m else len(source)
    return source[start:end].rstrip()

bad=[]
print("Find Pax Message Copy Check")
print("Message Master:", lock["message_master_version"])

master_expected=lock.get("message_master_sha256")
master_actual=hashlib.sha256(master_path.read_bytes()).hexdigest()
master_ok=(master_expected==master_actual and str(master.get("version"))==str(lock.get("message_master_version")))
print(("PASS" if master_ok else "FAIL"), "message-master.json integrity")
if not master_ok:
    bad.append(("message-master.json", master_expected or "MISSING LOCK", master_actual))

for name,expected in lock["functions"].items():
    body=extract_func(src,name)
    actual=hashlib.sha256(body.encode("utf-8")).hexdigest() if body is not None else "MISSING"
    ok=actual==expected
    print(("PASS" if ok else "FAIL"), name)
    if not ok: bad.append((name,expected,actual))

if bad:
    print("\nMessage master or executable copy changed. Do not release until the copy is explicitly re-confirmed and the lock is intentionally updated.")
    for name,expected,actual in bad:
        print(f"- {name}\n  expected {expected}\n  actual   {actual}")
    sys.exit(1)

print(f"\nPASS: message-master.json integrity and all executable message generators match Find Pax Message Master v{lock['message_master_version']}.")
