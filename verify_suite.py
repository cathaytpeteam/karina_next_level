#!/usr/bin/env python3
"""Find Pax — one-command release verification and machine-readable report.

  python3 verify_suite.py --fast
  python3 verify_suite.py --full

Runs the architecture mutation proof, edit gate, then the existing release gate. It always
writes verification_report.json. Exit codes: 0 PASS, 1 FAIL, 2 BLOCKED_ENVIRONMENT.
The report is generated control output and is intentionally excluded from release hashes.
"""
from pathlib import Path
from datetime import datetime, timezone
import hashlib, json, re, subprocess, sys, time

sys.dont_write_bytecode = True
R = Path(__file__).resolve().parent
REPORT = R / 'verification_report.json'
MODE = 'full' if '--full' in sys.argv else 'fast' if '--fast' in sys.argv else ''
VERBOSE = '-v' in sys.argv or '--verbose' in sys.argv
JOBS = sys.argv[sys.argv.index('--jobs') + 1] if '--jobs' in sys.argv and sys.argv.index('--jobs') + 1 < len(sys.argv) else ('1' if MODE == 'full' else '3')
if MODE not in ('fast', 'full'):
    print('Usage: python3 verify_suite.py --fast|--full [--jobs 1|2|3] [-v]')
    raise SystemExit(2)
if JOBS not in ('1', '2', '3'):
    print('ERROR: --jobs must be 1, 2 or 3')
    raise SystemExit(2)

budget = json.loads((R / 'verification_budget.json').read_text(encoding='utf-8'))
runtime = budget.get('runtime', {})
warn_seconds = runtime.get('performance_warn_seconds', {})
env_markers = tuple(runtime.get('environment_block_markers', ['ERR_BLOCKED_BY_ADMINISTRATOR']))

def run(name, args):
    started = time.perf_counter()
    p = subprocess.run(args, cwd=R, capture_output=True, text=True, encoding='utf-8', errors='replace')
    elapsed = round(time.perf_counter() - started, 3)
    out = (p.stdout or '') + (('\n' + p.stderr) if p.stderr else '')
    fails = [x.strip() for x in out.splitlines() if x.startswith('FAIL')]
    check_count = None
    for pattern in (r'—\s+(\d+) checks', r'\((\d+) passed\)', r'—\s+(\d+) checks passed'):
        m = re.search(pattern, out)
        if m:
            check_count = int(m.group(1)); break
    limit = warn_seconds.get(name)
    perf = 'WARN' if isinstance(limit, (int, float)) and elapsed > limit else 'PASS'
    item = {
        'name': name, 'status': 'PASS' if p.returncode == 0 else 'FAIL',
        'returncode': p.returncode, 'elapsed_seconds': elapsed,
        'checks': check_count, 'performance_status': perf,
        'performance_warn_seconds': limit, 'failures': fails[:20],
    }
    if VERBOSE:
        print(out.rstrip())
    else:
        suffix = f' — {check_count} checks' if check_count is not None else ''
        print(f"{item['status']:4} {name}: {elapsed:.1f}s{suffix}" + (' [PERF WARN]' if perf == 'WARN' else ''))
        if p.returncode:
            for line in fails[:5]: print('     ' + line)
    return item, out


def metric_layers(out):
    layers = {}
    for key, passed, failed, state in re.findall(r'^METRIC layer (\w+) (\d+) (\d+) (\w+)$', out, re.M):
        layers[key] = {'passed': int(passed), 'failed': int(failed), 'status': state}
    return layers


def deployed_hash_state():
    sums = {}
    for line in (R / 'SHA256SUMS.txt').read_text(encoding='utf-8').splitlines():
        if '  ' in line:
            h, name = line.split('  ', 1)
            if '#' not in name: sums[name] = h
    sw = (R / 'sw.js').read_text(encoding='utf-8')
    m = re.search(r'const ASSETS=\[(.*?)\];', sw, re.S)
    assets = {x[2:] for x in re.findall(r'"(\./[^"]*)"', m.group(1)) if x != './'} if m else set()
    assets.add('sw.js')
    missing, changed = [], []
    for name in sorted(assets):
        p = R / name
        if not p.is_file(): missing.append(name); continue
        got = hashlib.sha256(p.read_bytes()).hexdigest()
        if sums.get(name) != got: changed.append(name)
    return {
        'status': 'PASS' if not missing and not changed else 'UNVERIFIED',
        'deployed_files': len(assets), 'missing': missing, 'different_from_last_verified': changed,
    }


started_all = time.perf_counter()
arch, arch_out = run('architecture_mutation', [sys.executable, '-B', 'verify_architecture.py', '--mutate'])
changed, changed_out = run('verify_changed_all', [sys.executable, '-B', 'verify_changed.py', '--all'])
release_cmd = [sys.executable, '-B', 'verify_release.py', '--' + MODE, '--jobs', JOBS, '--timing', '--metrics']
release, release_out = run('release_' + MODE, release_cmd)

layers = metric_layers(release_out)
static_m = re.search(r'^METRIC static (\d+) (PASS|FAIL)$', release_out, re.M)
static = {'status': static_m.group(2), 'checks': int(static_m.group(1))} if static_m else {'status': 'UNKNOWN', 'checks': None}
env_hits = sorted({marker for marker in env_markers if marker and marker in release_out})

# Only classify a failed release as environment-blocked for an explicitly known browser-policy marker.
release_status = release['status']
if release_status == 'FAIL' and env_hits:
    product_fail = [x for x in release['failures'] if not any(y in x for y in (
        'privacy at run time', '安全檢查失敗', 'fast browser checks', 'full browser checks', 'browser checks', 'check — fix the FAIL lines above'))]
    if not product_fail:
        release_status = 'BLOCKED_ENVIRONMENT'
release['status'] = release_status
release['environment_blockers'] = env_hits
release['layers'] = layers
release['static'] = static

deploy = deployed_hash_state()
performance_warnings = [x['name'] for x in (arch, changed, release) if x['performance_status'] == 'WARN']
if arch['status'] != 'PASS' or changed['status'] != 'PASS' or release_status == 'FAIL':
    overall = 'FAIL'
elif release_status == 'BLOCKED_ENVIRONMENT':
    overall = 'BLOCKED_ENVIRONMENT'
else:
    overall = 'PASS'
if overall == 'PASS' and deploy['status'] != 'PASS':
    overall = 'FAIL'

report = {
    'schema': 1,
    'generated_at_utc': datetime.now(timezone.utc).isoformat(timespec='seconds'),
    'mode': MODE,
    'overall_status': overall,
    'elapsed_seconds': round(time.perf_counter() - started_all, 3),
    'suites': [arch, changed, release],
    'anti_bloat': {'status': arch['status'], 'budget_file': 'verification_budget.json'},
    'deploy_hash': deploy,
    'performance': {'status': 'WARN' if performance_warnings else 'PASS', 'warnings': performance_warnings},
    'support_matrix': runtime.get('support_matrix', {}),
    'environment_required': runtime.get('environment_required', []),
}
REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

print('\nRELEASE VERIFICATION')
print(f"Static        {static['checks'] if static['checks'] is not None else '-'}  {static['status']}")
print(f"Architecture {arch['checks'] if arch['checks'] is not None else '-'}  {arch['status']}  {arch['elapsed_seconds']:.1f}s")
print(f"Changed      {changed['checks'] if changed['checks'] is not None else '-'}  {changed['status']}  {changed['elapsed_seconds']:.1f}s")
for key in ('safety', 'send', 'clear', 'input', 'flow', 'open', 'look'):
    if key in layers:
        x = layers[key]; print(f"Browser {key:<6} {x['passed']}/{x['failed']}  {x['status']}")
print(f"Release gate          {release['elapsed_seconds']:.1f}s")
print(f"Anti-bloat          {arch['status']}")
print(f"Performance         {'WARN' if performance_warnings else 'PASS'}")
print(f"Deploy hash         {deploy['status']} ({deploy['deployed_files']} files)")
print(f"Total time            {report['elapsed_seconds']:.1f}s")
print(f"RESULT: {overall}")
print('Report: verification_report.json')
raise SystemExit(0 if overall == 'PASS' else 2 if overall == 'BLOCKED_ENVIRONMENT' else 1)
