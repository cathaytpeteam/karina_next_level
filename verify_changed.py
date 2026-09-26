#!/usr/bin/env python3
"""Find Pax — check while editing (no browser, a few seconds).

  python3 verify_changed.py            detect changed files from SHA256SUMS.txt and check them
  python3 verify_changed.py app.js     check the named files instead
  python3 verify_changed.py --all      treat every file as changed
  add -v to also print PASS lines

Runs: syntax + wiring for changed files, every static lock (verify_release.py --static),
the colour lock, and hygiene rules (size limits, history tags in comments, unused CSS,
orphan files). Prints only FAIL lines and one summary line.
Before handing over a ZIP, run: python3 verify_release.py --fast
"""
from pathlib import Path
import hashlib, json, re, shutil, subprocess, sys, time

sys.dont_write_bytecode = True
T0 = time.time()
R = Path(__file__).resolve().parent
ARGS = [a for a in sys.argv[1:] if not a.startswith('-')]
ALL = '--all' in sys.argv
NO_STATIC = '--no-static' in sys.argv  # internal: verify_release.py already ran the static locks
VERBOSE = '-v' in sys.argv

# Files that are not deployed but belong to the release (everything else must be in sw.js ASSETS).
CONTROL_FILES = {'README.md', 'AI-GUIDE.md', 'PLAN.md', 'locks.json',
                 'flow-behavior-spec.json', 'verify_release.py', 'verify_behavior.py',
                 'verify_changed.py', 'SHA256SUMS.txt'}
SIZE_LIMITS = {'AI-GUIDE.md': 4096, 'README.md': 20480, 'PLAN.md': 12288}
MAX_CHANGELOG_ENTRIES = 2

# No historical comments or unused selectors are allowed.
KNOWN_HISTORY_COMMENTS = set()
KNOWN_UNUSED_CSS = set()

STALE = re.compile(r'(\b[rR]\d{1,2}\b|\bv\d+\.\d+|\bR\d+(?:\.\d+)+|20\d\d-\d\d-\d\d|'
                   r'\b[Ff]ormer(?:ly)?\b|[Mm]essage master \d|user build|[Uu]ser-approved)')
NAMED = set('''aqua aquamarine beige black blue blueviolet brown chartreuse chocolate coral
crimson cyan darkblue darkgray darkgreen darkgrey darkorange darkred deeppink deepskyblue
dimgray dodgerblue firebrick fuchsia gold goldenrod gray green grey hotpink indigo ivory
khaki lavender lightblue lightgray lightgreen lightgrey lime magenta maroon navy olive orange
orangered orchid pink plum purple red royalblue salmon silver skyblue tan teal tomato
turquoise violet wheat white yellow'''.split())

failed = False
n_pass = 0


def ck(name, ok, detail=''):
    global failed, n_pass
    if ok:
        n_pass += 1
        if VERBOSE:
            print('PASS', name)
    else:
        failed = True
        print('FAIL', name + ('  -> ' + detail if detail else ''), flush=True)


def text(name):
    p = R / name
    return p.read_text(encoding='utf-8', errors='replace') if p.is_file() else ''


def release_files():
    out = {}
    for p in R.rglob('*'):
        rel = p.relative_to(R)
        if not p.is_file() or '__pycache__' in rel.parts or any(x.startswith('.git') for x in rel.parts):
            continue
        if p.name in ('.nojekyll', 'CNAME'):
            continue
        out[rel.as_posix()] = p
    return out


# ---- which files changed -------------------------------------------------------
files = release_files()
listed = {}
for line in text('SHA256SUMS.txt').splitlines():
    parts = line.split('  ', 1)
    if len(parts) == 2:
        listed[parts[1]] = parts[0]
if ARGS:
    changed = sorted(Path(a).name for a in ARGS)
elif ALL or not listed:
    changed = sorted(files)
else:
    changed = sorted(f for f, p in files.items() if f != 'SHA256SUMS.txt'
                     and hashlib.sha256(p.read_bytes()).hexdigest() != listed.get(f))
deleted = sorted(f for f in listed if f not in files)

# ---- syntax -----------------------------------------------------------------------
node = shutil.which('node')
for name in changed:
    p = R / name
    if not p.is_file():
        ck(name + ' exists', False)
        continue
    if name.endswith('.json') or name.endswith('.webmanifest'):
        try:
            json.loads(text(name)); ck(name + ' JSON syntax', True)
        except Exception as e:
            ck(name + ' JSON syntax', False, str(e))
    elif name.endswith('.js'):
        if node:
            r = subprocess.run([node, '--check', str(p)], capture_output=True, text=True)
            ck(name + ' JavaScript syntax', r.returncode == 0, (r.stderr or r.stdout).strip()[:300])
        else:
            s = text(name)
            ck(name + ' brace balance (node not installed)', s.count('{') == s.count('}') and s.count('(') == s.count(')'))
    elif name.endswith('.py'):
        r = subprocess.run([sys.executable, '-B', '-c', 'import ast,sys; ast.parse(open(sys.argv[1],encoding="utf-8").read())', str(p)],
                           capture_output=True, text=True)
        ck(name + ' Python syntax', r.returncode == 0, (r.stderr or r.stdout).strip()[-300:])
    elif name.endswith('.css'):
        t = re.sub(r'/\*.*?\*/', '', text(name), flags=re.S)
        ck(name + ' brace balance', t.count('{') == t.count('}'))
    elif name.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
        ck(name + ' is non-empty', p.stat().st_size > 0)

if 'libphonenumber-mobile.js' in changed or 'app.js' in changed:
    ck('Node is required for phone regression checks', bool(node))
if ('libphonenumber-mobile.js' in changed or 'app.js' in changed) and node:
    probe = r'''const fs=require('fs'),lp=require(process.argv[1]);
const source=fs.readFileSync(process.argv[2],'utf8');
const start=source.indexOf('  function validatePhone(raw){');
const end=source.indexOf('\n  }',start)+4;
if(start<0||end<4) throw Error('validatePhone function missing');
const markStart=source.indexOf('  function phoneInputIsBad(raw,p){');
const markEnd=source.indexOf('\n  }',markStart)+4;
if(markStart<0||markEnd<4) throw Error('phoneInputIsBad function missing');
const byCode={};
lp.getCountries().forEach(country=>{
  const code=String(lp.getCountryCallingCode(country));
  (byCode[code]||(byCode[code]=[])).push(country);
});
const meta={byCode,codes:Object.keys(byCode).sort((a,b)=>b.length-a.length)};
const digits=raw=>String(raw).replace(/\D/g,'');
const callingCodeFor=n=>meta.codes.find(code=>n.startsWith(code))||'';
const {validatePhone,phoneInputIsBad}=new Function('PHONE_META','window','digits','callingCodeFor','phoneLibReady',
  source.slice(start,end)+source.slice(markStart,markEnd)+'; return {validatePhone,phoneInputIsBad};')(
  meta,{libphonenumber:lp},digits,callingCodeFor,true);
const cases=[['+886 2 2345 6789',false],['+852 2123 4567',false],
['+81 3 1234 5678',false],['+81 120 123 456',false],
['+886 912 345 678',true],['+852 9123 4567',true],
['+81 90 1234 5678',true],['+81 60 1234 5678',true],
['+1 202 555 0123',true],['+44 7911 123456',true]];
const bad=cases.filter(([number,expected])=>{
  const p=validatePhone(number);
  return !!p!==expected||phoneInputIsBad(number,p)===expected;
});
const partial=['','+8','+81','+81 0','+81 90 123','+886 912','+852 91'];
const premature=partial.filter(number=>phoneInputIsBad(number,validatePhone(number)));
if(lp.getCountries().length!==245||bad.length||premature.length){
  console.error(JSON.stringify({countries:lp.getCountries().length,bad,premature}));process.exit(1);
}'''
    result = subprocess.run([node, '-e', probe, str(R / 'libphonenumber-mobile.js'),str(R / 'app.js')],
                            capture_output=True, text=True)
    ck('mobile library 245 regions and fixed phone matrix', result.returncode == 0,
       result.stderr.strip()[:300])

# ---- wiring -----------------------------------------------------------------------
h, a, sw, cp = text('index.html'), text('app.js'), text('sw.js'), text('copy.js')
ck('index.html loads app.css', '<link rel="stylesheet" href="./app.css">' in h)
ck('index.html loads copy.js before app.js', 0 <= h.find('./copy.js') < h.find('./app.js'))
ck('index.html has no inline application script', '<script>\n(function(){' not in h)
ids = re.findall(r'\bid="([^"]+)"', h)
ck('index.html element ids are unique', len(ids) == len(set(ids)), ', '.join(sorted({x for x in ids if ids.count(x) > 1})))
ck('app.js avoids optional chaining (older Android)', '?.' not in a)
ck('app.js avoids native replaceChildren (older Android)', '.replaceChildren(' not in a and 'replaceChildrenCompat' in a)
for req in ('function go(', 'function showScreen(', 'const FLOWS=', 'function resetAll('):
    ck('app.js keeps ' + req, req in a)
ck('copy.js exposes FIND_PAX_COPY', 'window.FIND_PAX_COPY' in cp and 'window.FIND_PAX_COPY' in a)
m = re.search(r'const ASSETS=\[(.*?)\];', sw, re.S)
assets = {x[2:] for x in re.findall(r'"(\./[^"]*)"', m.group(1))} - {''} if m else set()
ck('sw.js ASSETS parsed', bool(assets))
ck('sw.js has an explicit cache revision', bool(re.search(r'const CACHE_REV="[^"]+";', sw)))
for f in sorted(assets):
    ck('sw.js asset exists: ' + f, f in files)
if deleted:
    ck('deleted files are not referenced', not any(d in h + a + sw + text('manifest.webmanifest') for d in deleted), ', '.join(deleted))

# ---- static locks (layout, navigation, message copy, baseline) ------------------
if not NO_STATIC:
    r = subprocess.run([sys.executable, '-B', str(R / 'verify_release.py'), '--static'] + (['-v'] if VERBOSE else []),
                       cwd=R, capture_output=True, text=True, encoding='utf-8', errors='replace')
    for line in r.stdout.splitlines():
        if line.startswith('FAIL') and not line.startswith('FAIL:'):
            print(line)
        elif VERBOSE and line.startswith(('PASS', '  PASS')):
            print(line)
    ck('static locks (verify_release.py --static)', r.returncode == 0, '' if r.returncode == 0 else (r.stderr.strip()[-300:] or 'see FAIL lines above'))

# ---- colour lock -------------------------------------------------------------------
def norm_hex(x):
    x = x.upper()
    return '#' + ''.join(c * 2 for c in x[1:]) if len(x) == 4 else x


def colours(t, css):
    out = set()
    if css:
        t = re.sub(r'/\*.*?\*/', '', t, flags=re.S)
        for decl in re.findall(r'\{([^{}]*)\}', t):
            for prop, val in re.findall(r'([\w-]+)\s*:\s*([^;]+)', decl):
                out |= {norm_hex(x) for x in re.findall(r'#[0-9a-fA-F]{3,8}\b', val)}
                out |= {re.sub(r'\s+', '', x.lower()) for x in re.findall(r'(?:rgba?|hsla?)\([^)]*\)', val)}
                if prop not in ('font-family', 'transition', 'animation', 'content') and not prop.startswith('--font'):
                    out |= {'named:' + w for w in re.findall(r'\b[a-z]+\b', val.lower()) if w in NAMED}
    else:
        out |= {norm_hex(x) for x in re.findall(r'(?:fill|stroke|stop-color|color|content|background)\s*[=:]\s*["\']?(#[0-9a-fA-F]{3,8})\b', t)}
        out |= {norm_hex(x) for x in re.findall(r'["\'](#[0-9a-fA-F]{3,8})["\']', t)}
        out |= {re.sub(r'\s+', '', x.lower()) for x in re.findall(r'(?:rgba?|hsla?)\([^)]*\)', t)}
    return out


approved = set(json.loads(text('locks.json')).get('colors', {}).get('approved', []))
for f in ('app.css', 'index.html', 'app.js', 'copy.js', 'manifest.webmanifest'):
    new = colours(text(f), f.endswith('.css')) - approved
    ck('colour lock: ' + f, not new, 'unapproved colour(s): ' + ', '.join(sorted(new)))

# Phase 2: all deployed colour literals are centralized in :root (manifest keeps its own theme colours).
_css=text('app.css')
_root_m=re.search(r':root\{(.*?)\}',_css,re.S)
_css_rest=_css[:_root_m.start()]+_css[_root_m.end():] if _root_m else _css
_literal_re=re.compile(r'#[0-9a-fA-F]{3,8}\b|(?:rgba?|hsla?)\([^)]*\)')
ck('app.css colour literals only in :root', not _literal_re.search(re.sub(r'/\*.*?\*/','',_css_rest,flags=re.S)))
ck('index.html has no literal hex colours', not re.search(r'#[0-9a-fA-F]{3,8}\b', h))

# Copy wiring and stable IDs.
def load_copy():
    m=re.search(r'window\.FIND_PAX_COPY\s*=\s*Object\.freeze\((\{.*\})\);',cp,re.S)
    try: return json.loads(m.group(1)) if m else {}
    except Exception: return {}
_copy=load_copy()
ck('copy.js parses to stable-ID object', bool(_copy))
_refs=set(re.findall(r'(?:copy(?:Obj)?|fillCopy)\("([^"]+)"',a))
_dynamic={x for x in _refs if x.endswith('.')}
_missing=sorted(x for x in _refs if x not in _copy and x not in _dynamic)
ck('every referenced copy ID exists', not _missing, ', '.join(_missing))
# Dynamic message IDs are generated from the complete scenario/language/state cartesian branches.
_used={x for x in _refs if x in _copy}
if 'fillCopy("s4.zh."+status+"."+arrange' in a and 'fillCopy("s4.en."+status+"."+arrange' in a: _used.update(k for k in _copy if re.match(r's4\.(?:zh|en)\.(?:possible|delayed|unknown)\.(?:known|airport)$',k))
if 'fillCopy("s4.zh.gate."+st+"."+target+"."+go' in a: _used.update(k for k in _copy if k.startswith('s4.zh.gate.'))
if 'fillCopy("s4.en.gate."+st+"."+target+"."+go' in a: _used.update(k for k in _copy if k.startswith('s4.en.gate.'))
# Rules are referenced with copyObj/copy; all other message IDs are direct literals.
_unused=sorted(k for k in _copy if k not in _used)
ck('every copy ID is used', not _unused, ', '.join(_unused[:12]))
# No Chinese/Japanese string literals remain in app.js. Comments are ignored.
_a_no_comments=re.sub(r'/\*.*?\*/|//[^\n]*','',a,flags=re.S)
_strs=re.findall(r'(["\'`])((?:\\.|(?!\1).)*)\1',_a_no_comments)
_cjk=[v for _,v in _strs if re.search(r'[\u3040-\u30ff\u3400-\u9fff]',v)]
ck('app.js has no Chinese/Japanese string literals', not _cjk, '; '.join(_cjk[:5]))

# ---- hygiene -----------------------------------------------------------------------
for f, limit in SIZE_LIMITS.items():
    if f in files:
        size = files[f].stat().st_size
        ck(f'{f} within {limit // 1024} KB', size <= limit, f'{size} bytes — trim it before adding more')
log = text('README.md').split('## Change log', 1)
entries = len(re.findall(r'^### ', log[1], re.M)) if len(log) == 2 else 0
ck(f'README change log keeps at most {MAX_CHANGELOG_ENTRIES} entries', entries <= MAX_CHANGELOG_ENTRIES,
   f'{entries} entries — remove the oldest (history lives in git)')


def comments(name, t):
    if name.endswith('.py'):
        for ln in t.split('\n'):
            st = ln.strip()
            if st.startswith('#'):
                yield st[1:].strip()
            elif '  # ' in ln:
                yield ln.split('  # ', 1)[1].strip()
        for mm in re.finditer(r'"""(.*?)"""', t, re.S):
            yield ' '.join(mm.group(1).split())
    elif name.endswith('.html'):
        for mm in re.finditer(r'<!--(.*?)-->', t, re.S):
            yield ' '.join(mm.group(1).split())
    else:
        for ln in t.split('\n'):
            mm = re.search(r'(?<![:"\'\w\\])//(.*)$', ln)
            if mm:
                yield mm.group(1).strip()
        for mm in re.finditer(r'/\*(.*?)\*/', t, re.S):
            yield ' '.join(mm.group(1).split())


def known(f, c):
    return any(f == kf and (c == kc or (kc.endswith('*') and c.startswith(kc[:-1]))) for kf, kc in KNOWN_HISTORY_COMMENTS)


code_files = [f for f in files if f.endswith(('.js', '.css', '.html', '.py'))]
bad_comments = [(f, c) for f in sorted(code_files) for c in comments(f, text(f)) if STALE.search(c) and not known(f, c)]
ck('comments describe current behaviour (no rNN / v1.x / dates / "formerly")', not bad_comments,
   '; '.join(f'{f}: {c[:70]}' for f, c in bad_comments[:5]))

css = re.sub(r'/\*.*?\*/', '', text('app.css'), flags=re.S)
selectors = ' '.join(re.findall(r'([^{}]+)\{', css))
tokens = {t for t in re.findall(r'[.#]([A-Za-z][\w-]*)', selectors) if not re.fullmatch(r'[0-9a-fA-F]{3,8}', t)}
source = h + a + cp
unused = sorted(t for t in tokens if t not in source)
new_unused = [t for t in unused if t not in KNOWN_UNUSED_CSS]
ck('no unused CSS classes/ids', not new_unused, ', '.join(new_unused))

orphans = sorted(f for f in files if f not in CONTROL_FILES and f not in assets and f != 'sw.js')
ck('no orphan files (every file is deployed or a listed control file)', not orphans, ', '.join(orphans))


# ---- summary --------------------------------------------------------------------
scope = 'all files' if (ALL or not listed) and not ARGS else (', '.join(changed + ['-' + d for d in deleted]) or 'no changes')
if len(scope) > 120:
    scope = f'{len(changed)} files'
secs = time.time() - T0
if failed:
    print(f'FAIL: verify_changed — {scope} ({secs:.1f}s)')
    raise SystemExit(1)
print(f'PASS: verify_changed — {scope} — {n_pass} checks ({secs:.1f}s)')
