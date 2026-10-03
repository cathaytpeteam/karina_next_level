#!/usr/bin/env python3
"""Find Pax — verification architecture audit and mutation proof.
  python3 verify_architecture.py             fast architecture/coverage audit
  python3 verify_architecture.py --mutate    audit + five static mutation proofs
This file never edits deployed files. Mutation proofs run against temporary copies and
must be rejected by verify_release.py --static. They prove the release locks fail closed.
"""
from pathlib import Path
import ast, json, re, shutil, subprocess, sys, tempfile, time
sys.dont_write_bytecode = True
R = Path(__file__).resolve().parent
T0 = time.time()
VERBOSE = '-v' in sys.argv or '--verbose' in sys.argv
MUTATE = '--mutate' in sys.argv
failed = False
passed = 0
def ck(name, ok, detail=''):
    global failed, passed
    if ok:
        passed += 1
        if VERBOSE:
            print('PASS', name)
    else:
        failed = True
        print('FAIL', name + ('  -> ' + detail if detail else ''), flush=True)
def text(name):
    return (R / name).read_text(encoding='utf-8', errors='replace')
CHECK_FILES = sorted([p.name for p in R.glob('verify_*.py')] + [p.name for p in R.glob('vb_*.py')])

# Budgets ratchet implementation size while allowing coverage to grow through data/cases.
budget = json.loads(text('verification_budget.json'))
loc = {name: len(text(name).splitlines()) for name in CHECK_FILES}
total_loc = sum(loc.values())
for name, limit in sorted(budget.get('document_byte_limits', {}).items()):
    size = (R / name).stat().st_size if (R / name).is_file() else 10**9
    ck('budget: ' + name + ' stays within byte budget', size <= limit, f'{size} > {limit} bytes')
ck('budget: verification file set matches baseline', set(CHECK_FILES) == set(budget['files']),
   'added/removed: ' + ', '.join(sorted(set(CHECK_FILES) ^ set(budget['files']))))
ck('budget: total verification LOC stays within ratchet', total_loc <= budget['max_total_loc'],
   f"{total_loc} > {budget['max_total_loc']} — refactor first or explicitly review the budget")
for name, limit in sorted(budget.get('file_loc_limits', {}).items()):
    ck('budget: ' + name + ' stays within its ratchet', loc.get(name, 10**9) <= limit,
       f"{loc.get(name, 'missing')} > {limit}")
hard = budget['hard_file_loc_limit']
oversized = [f'{name}={n}' for name, n in loc.items() if n > hard]
ck(f'budget: no verification file exceeds {hard} lines', not oversized, ', '.join(oversized))

runtime = budget.get('runtime', {})
perf = runtime.get('performance_warn_seconds', {})
ck('runtime: performance warning budgets exist', all(isinstance(perf.get(k), (int, float)) and perf[k] > 0
   for k in ('architecture_mutation','verify_changed_all','release_fast','release_full')))
ck('runtime: environment blockers are explicit', bool(runtime.get('environment_block_markers')))
support = runtime.get('support_matrix', {})
ck('runtime: Android Chrome is the primary support target', bool(support.get('primary')) and all('Android Chrome' in x for x in support.get('primary', [])))
ck('runtime: Safari is smoke-only, not a primary release target', 'Safari' in support.get('optional_smoke', ''))
ck('policy: finalization uses FAST handoff and local FULL certification', '`這版定案`' in text('AI-GUIDE.md') and 'does **not** update the README Change log' in text('AI-GUIDE.md') and 'Do not run FULL in the assistant environment' in text('AI-GUIDE.md') and 'passing local FULL updates `SHA256SUMS.txt`' in text('AI-GUIDE.md'))


def duplicate_windows(window):
    """Count repeated normalized code windows; comments/blank lines do not buy budget."""
    hits = {}
    for name in CHECK_FILES:
        rows = []
        for raw in text(name).splitlines():
            line = raw.strip()
            if not line or line.startswith('#'):
                continue
            line = re.sub(r'([\"\']).*?\1', 'S', line)
            line = re.sub(r'\b\d+(?:\.\d+)?\b', 'N', line)
            line = re.sub(r'\s+', ' ', line)
            rows.append(line)
        for i in range(max(0, len(rows) - window + 1)):
            key = '\n'.join(rows[i:i + window])
            hits.setdefault(key, []).append((name, i))
    repeated = 0
    for positions in hits.values():
        if len(positions) < 2:
            continue
        if any(a[0] != b[0] or abs(a[1] - b[1]) >= window
               for x, a in enumerate(positions) for b in positions[x + 1:]):
            repeated += 1
    return repeated


dup_window = budget['duplicate_window_lines']
dup_count = duplicate_windows(dup_window)
ck('budget: normalized duplicate-code windows do not increase', dup_count <= budget['max_duplicate_windows'],
   f"{dup_count} > {budget['max_duplicate_windows']} repeated {dup_window}-line windows")
# Registry: literal ck names; dynamic checks are covered by plan/spec audits.
literal = []
for name in CHECK_FILES:
    try:
        tree = ast.parse(text(name), filename=name)
    except SyntaxError as e:
        ck('registry: Python parses: ' + name, False, str(e)); continue
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == 'ck' and node.args:
            a = node.args[0]
            if isinstance(a, ast.Constant) and isinstance(a.value, str):
                literal.append((a.value, name, node.lineno))

ck('registry: verification files discovered', len(CHECK_FILES) >= 10, str(CHECK_FILES))
ck('registry: literal check names discovered', len(literal) >= 100, str(len(literal)))
# Duplicate names are useful to see, but only exact duplicates inside the same file are considered accidental.
seen = set(); same_file_dupes = []
for n, f, line in literal:
    key = (f, n)
    if key in seen: same_file_dupes.append(f'{f}:{line} {n}')
    seen.add(key)
ck('registry: no accidental duplicate literal check names in one file', not same_file_dupes, '; '.join(same_file_dupes[:8]))
# Coverage map: declared behaviour requirements map to browser layers/plans.
spec = json.loads(text('flow-behavior-spec.json'))
vp = __import__('vb_priority')
problems = vp.plan_problems()
ck('coverage: every spec guard/state rule maps to a test layer', not problems, ', '.join(problems[:8]))
ck('coverage: every spec edge has required fields', all({'from','trigger','to'} <= set(e) for e in spec.get('edges', [])))
ck('coverage: every spec screen is unique', len(spec.get('screens', [])) == len(set(spec.get('screens', []))))
ck('coverage: FAST plan is non-empty and layered', bool(vp.FAST) and set(vp.SPEC_LAYER.values()) <= set(vp.LAYER_ORDER))

# Lock map: the major release-contract domains must stay represented in locks.json.
locks = json.loads(text('locks.json'))
for key in ('baseline', 'layout', 'navigation', 'message_copy', 'colors', 'privacy', 'verification'):
    ck('coverage: lock domain ' + key, key in locks)
protected = locks.get('baseline', {}).get('protected', {})
for key in ('phone_validation', 'japanese_sms', 'datetime', 'flight_rules'):
    ck('coverage: protected baseline ' + key, key in protected)

# Layer visibility: no browser layer can silently disappear from the declared run order.
expected_layers = {'safety','send','clear','input','flow','open','look'}
ck('coverage: browser layer set complete', set(vp.LAYER_ORDER) == expected_layers, str(vp.LAYER_ORDER))

# Scenario setup matrices are explicit coverage contracts: refactors may share runners, not drop cases.
go = __import__('vb_guards_other')
ck('coverage: re-entry matrix covers S1 S2 S4 S5', set(go.REENTRY) == {'S1','S2','S4','S5'}, str(sorted(go.REENTRY)))
ck('coverage: Home setup matrix covers S1-S5', {x[0].split()[0] for x in go.HOME_CASES} == {'S1','S2','S3','S4','S5'}, str([x[0] for x in go.HOME_CASES]))
ck('coverage: retry send uses shared external navigation capture', 'await await_external(r.pg, r.nav, n0, r.counts, c0)' in text('vb_guards_other.py'))


# Data-driven case floors prevent LOC reductions from being achieved by deleting coverage.
validation = __import__('vb_validation')
case_tables = {
    'REENTRY': len(go.REENTRY),
    'HOME_CASES': len(go.HOME_CASES),
    'HOME_DROP_CASES': len(go.HOME_DROP_CASES),
    'MATRIX': len(validation.MATRIX),
    'GATE_MATRIX': len(validation.GATE_MATRIX),
}
case_floor = budget['min_case_rows']
for name, minimum in sorted(case_floor.items()):
    ck('budget: case table ' + name + ' does not shrink', case_tables.get(name, -1) >= minimum,
       f"{case_tables.get(name, 'missing')} < {minimum}")
case_rows = sum(case_tables.values())
base_cases = sum(case_floor.values())
if VERBOSE:
    print(f'METRIC verification budget: {total_loc} LOC / {case_rows} protected data rows; '
          f'baseline <= {budget["max_total_loc"]} LOC / >= {base_cases} rows; duplicate windows={dup_count}')


def document_bloat_mutation(filename, limit):
    with tempfile.TemporaryDirectory(prefix='find-pax-doc-mut-') as td:
        dst = Path(td) / 'tree'; shutil.copytree(R, dst, ignore=shutil.ignore_patterns('__pycache__', '*.pyc', '*.pyo'))
        (dst / filename).write_text('X' * (limit + 1), encoding='utf-8')
        q = subprocess.run([sys.executable, '-B', 'verify_architecture.py'], cwd=dst, capture_output=True, text=True)
        ck('mutation rejected: document bloat ' + filename, q.returncode != 0, 'architecture gate unexpectedly passed')


def mutation(name, filename, old, new):
    """Mutate one protected fact in a temp tree; static release gate must reject it."""
    with tempfile.TemporaryDirectory(prefix='find-pax-mut-') as td:
        dst = Path(td) / 'tree'
        shutil.copytree(R, dst, ignore=shutil.ignore_patterns('__pycache__', '*.pyc', '*.pyo'))
        p = dst / filename
        src = p.read_text(encoding='utf-8')
        if old not in src:
            ck('mutation: ' + name, False, 'mutation anchor missing')
            return
        p.write_text(src.replace(old, new, 1), encoding='utf-8')
        q = subprocess.run([sys.executable, '-B', 'verify_release.py', '--static'], cwd=dst,
                           capture_output=True, text=True, encoding='utf-8', errors='replace')
        ck('mutation rejected: ' + name, q.returncode != 0,
           'static gate unexpectedly passed' if q.returncode == 0 else '')
        if VERBOSE and q.returncode != 0:
            fails = [x for x in q.stdout.splitlines() if x.startswith('FAIL')][:3]
            print('  caught by:', ' | '.join(fails))


if MUTATE:
    mutation('phone validation function changed', 'app.js',
             '  function validatePhone(raw){', '  function validatePhone(raw){/* mutation proof */')
    mutation('Scenario 1 entry route changed', 'app.js',
             'flow="miss";S.callNoMessage=false;', 'flow="call";S.callNoMessage=false;')
    mutation('approved message copy changed', 'copy.js',
             'window.FIND_PAX_COPY', 'window.FIND_PAX_COPY_MUTATED')
    mutation('Content-Security-Policy removed', 'index.html',
             '<meta http-equiv="Content-Security-Policy"', '<meta http-equiv="X-Content-Security-Policy"')
    mutation('Service Worker behavior changed', 'sw.js',
             'const CACHE_PREFIX=', '/* mutation proof */\nconst CACHE_PREFIX=')
    mutation('verification budget inflated', 'verification_budget.json',
             f'"max_total_loc": {budget["max_total_loc"]}', '"max_total_loc": 99999')
    for filename, limit in sorted(budget.get('document_byte_limits', {}).items()): document_bloat_mutation(filename, limit)

print(('FAIL' if failed else 'PASS') + f': verification architecture — {passed} checks ({time.time()-T0:.1f}s)' +
      (' incl. mutation proof' if MUTATE else ''))
raise SystemExit(1 if failed else 0)
