#!/usr/bin/env python3
import json, os, subprocess, time, textwrap
from pathlib import Path

ROOT = Path('/home/horde/.openclaw/workspace/omniperf')
OUT = ROOT / 'skill-test-results' / 'phase3-tooling-smoke'
OUT.mkdir(parents=True, exist_ok=True)

def run(cmd, timeout=60, cwd=None, env=None):
    started=time.time()
    try:
        cp=subprocess.run(cmd, shell=True, cwd=cwd, env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout)
        return {'cmd':cmd,'returncode':cp.returncode,'stdout':cp.stdout,'stderr':cp.stderr,'duration_s':round(time.time()-started,3)}
    except subprocess.TimeoutExpired as e:
        return {'cmd':cmd,'returncode':None,'stdout':e.stdout or '','stderr':(e.stderr or '')+'\nTIMEOUT','duration_s':round(time.time()-started,3)}

results = {'timestamp': time.time(), 'tests': {}}

# install-profilers: exact quick check, but no install
prof_checks = {
    'nsys_path': 'command -v nsys',
    'nsys_version': 'nsys --version',
    'sqlite3_path': 'command -v sqlite3',
    'sqlite3_version': 'sqlite3 --version',
    'csvexport_path': 'command -v csvexport',
    'csvexport_help': 'csvexport --help | head -40',
    'tracy_capture_path': 'command -v tracy-capture || command -v capture || command -v capture-release',
    'tracy_capture_help': '(tracy-capture --help || capture --help || capture-release --help) 2>&1 | head -40',
    'tracy_update_path': 'command -v tracy-update || command -v update',
    'tracy_update_help': '(tracy-update --help || update --help) 2>&1 | head -40',
}
results['tests']['install-profilers'] = {k: run(v, timeout=20) for k,v in prof_checks.items()}

# diagnose-perf: non-invasive snapshot subset
results['tests']['diagnose-perf'] = {
    'gpu_query': run('nvidia-smi --query-gpu=name,driver_version,memory.total,memory.used,temperature.gpu,pstate,clocks_throttle_reasons.active,utilization.gpu,power.draw,power.limit --format=csv,noheader', timeout=20),
    'cpu_model': run("lscpu | grep -E 'Model name|Socket|Core|Thread|NUMA'", timeout=20),
    'cpu_governor': run("cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor 2>/dev/null || echo unavailable", timeout=20),
    'memory': run('free -h', timeout=20),
}

# nvtx-python: create tiny script; only run if nvtx installed
nvtx_dir = OUT / 'nvtx-python'
nvtx_dir.mkdir(exist_ok=True)
script = nvtx_dir / 'tiny_nvtx_test.py'
script.write_text(textwrap.dedent('''
    import time
    try:
        import nvtx
    except Exception as e:
        print(f"NVTX_IMPORT_FAILED: {e!r}")
        raise SystemExit(42)

    @nvtx.annotate("tiny_work", color="blue")
    def tiny_work():
        total = 0
        for i in range(10000):
            total += i*i
        time.sleep(0.01)
        return total

    print("RESULT", tiny_work())
''').strip()+'\n')
results['tests']['nvtx-python'] = {
    'import_and_run': run(f'python3 {script}', timeout=20),
}

# profiling/nsys-analyze: if nsys exists, profile tiny Python workload without CUDA dependency.
nsys_exists = results['tests']['install-profilers']['nsys_path']['returncode'] == 0
sqlite_exists = results['tests']['install-profilers']['sqlite3_path']['returncode'] == 0
if nsys_exists:
    prof_dir = OUT / 'nsys-tiny'
    prof_dir.mkdir(exist_ok=True)
    tiny = prof_dir / 'tiny_profile.py'
    tiny.write_text('import time\nfor i in range(5):\n    sum(j*j for j in range(200000))\n    time.sleep(0.02)\nprint("tiny profile done")\n')
    rep_base = prof_dir / 'tiny_python'
    # Use CPU/NVTX/OSRT only to avoid requiring CUDA workload.
    results['tests']['profiling'] = {
        'nsys_profile_tiny_python': run(f'nsys profile --force-overwrite=true -o {rep_base} -t nvtx,osrt python3 {tiny}', timeout=120)
    }
    rep = prof_dir / 'tiny_python.nsys-rep'
    if rep.exists():
        results['tests']['profiling']['artifact'] = {'path': str(rep), 'size_bytes': rep.stat().st_size, 'committed': False}
        sqlite_out = prof_dir / 'tiny_python.sqlite'
        results['tests']['nsys-analyze'] = {
            'export_sqlite': run(f'nsys export --force-overwrite=true --type sqlite --output {sqlite_out} {rep}', timeout=120)
        }
        if sqlite_out.exists():
            results['tests']['nsys-analyze']['artifact'] = {'path': str(sqlite_out), 'size_bytes': sqlite_out.stat().st_size, 'committed': False}
            if sqlite_exists:
                results['tests']['nsys-analyze']['sqlite_tables'] = run(f"sqlite3 {sqlite_out} '.tables'", timeout=20)
            else:
                results['tests']['nsys-analyze']['sqlite_tables'] = {'status':'blocked_missing_prereq','reason':'sqlite3 not installed'}
        # Keep reports lightweight: do not leave binary trace artifacts in the PR tree.
        for artifact in (rep, sqlite_out):
            if artifact.exists():
                artifact.unlink()
    else:
        results['tests']['nsys-analyze'] = {'status':'blocked_no_nsys_rep'}
else:
    results['tests']['profiling'] = {'status':'blocked_missing_prereq','reason':'nsys not installed or not on PATH'}
    results['tests']['nsys-analyze'] = {'status':'blocked_missing_prereq','reason':'nsys not installed or not on PATH'}

# profiling-api: static/minimal example compiles are not appropriate without Kit SDK; validate doc has Python/C++ examples.
skill = ROOT / '.agents' / 'skills' / 'profiling-api' / 'SKILL.md'
text = skill.read_text(errors='replace') if skill.exists() else ''
results['tests']['profiling-api'] = {
    'static_doc_check': {
        'has_cpp_macro': 'CARB_PROFILE_ZONE' in text,
        'has_python_api': 'carb.profiler' in text or '@profile' in text,
        'status': 'pass' if 'CARB_PROFILE_ZONE' in text and ('carb.profiler' in text or '@profile' in text) else 'warning'
    }
}

# tracy-memory: non-invasive check for likely allocwrapper paths and capture binary availability.
alloc_paths = list(Path('/home/horde').glob('.cache/packman/chk/allocmemwrapper/*/liballocwrapper.so'))[:20]
results['tests']['tracy-memory'] = {
    'allocwrapper_candidates': [str(p) for p in alloc_paths],
    'tracy_capture_available': results['tests']['install-profilers']['tracy_capture_path']['returncode'] == 0,
    'status': 'pass' if alloc_paths and results['tests']['install-profilers']['tracy_capture_path']['returncode'] == 0 else 'blocked_missing_prereq'
}

(OUT / 'phase3-tooling-smoke.json').write_text(json.dumps(results, indent=2))

# Markdown summary
lines = ['# Phase 3 — Tooling Smoke Tests', '']

# Summaries
ip = results['tests']['install-profilers']
lines += ['## install-profilers', '', '| Tool | Status | Detail |', '|---|---|---|']
for tool, pathkey, verkey in [('nsys','nsys_path','nsys_version'),('sqlite3','sqlite3_path','sqlite3_version'),('csvexport','csvexport_path','csvexport_help'),('tracy-capture','tracy_capture_path','tracy_capture_help'),('tracy-update','tracy_update_path','tracy_update_help')]:
    pathres=ip[pathkey]
    verres=ip[verkey]
    st='pass' if pathres['returncode']==0 else 'blocked_missing_prereq'
    detail=(pathres['stdout'] or verres['stdout'] or verres['stderr']).strip().splitlines()[:2]
    lines.append(f"| `{tool}` | {st} | `{'; '.join(detail)[:180]}` |")
lines.append('')

for name in ['diagnose-perf','nvtx-python','profiling','nsys-analyze','profiling-api','tracy-memory']:
    lines.append(f'## {name}')
    data=results['tests'].get(name,{})
    lines.append('')
    lines.append('```json')
    lines.append(json.dumps(data, indent=2)[:4000])
    lines.append('```')
    lines.append('')

(OUT / 'phase3-tooling-smoke.md').write_text('\n'.join(lines)+'\n')
print(json.dumps({'wrote': str(OUT), 'nsys_exists': nsys_exists, 'sqlite_exists': sqlite_exists}, indent=2))
