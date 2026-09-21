from pathlib import Path
import hashlib, json, re, sys

root=Path(__file__).resolve().parent
src=(root/"index.html").read_text(encoding="utf-8")
lock=json.loads((root/"message-copy-lock.json").read_text(encoding="utf-8"))

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
for name,expected in lock["functions"].items():
    body=extract_func(src,name)
    actual=hashlib.sha256(body.encode("utf-8")).hexdigest() if body is not None else "MISSING"
    ok=actual==expected
    print(("PASS" if ok else "FAIL"), name)
    if not ok: bad.append((name,expected,actual))

if bad:
    print("\nMessage copy changed. Do not release until the copy is explicitly re-confirmed and the lock is intentionally updated.")
    for name,expected,actual in bad:
        print(f"- {name}\n  expected {expected}\n  actual   {actual}")
    sys.exit(1)

print("\nPASS: all executable message generators match Find Pax Message Master v1.0.")
