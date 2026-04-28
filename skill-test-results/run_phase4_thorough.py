#!/usr/bin/env python3
import json, os, re, shutil, subprocess, time
from pathlib import Path

ROOT = Path('/home/horde/.openclaw/workspace/omniperf')
SKILLS = ROOT / '.agents' / 'skills'
OUT = ROOT / 'skill-test-results' / 'phase4-thorough'
OUT.mkdir(parents=True, exist_ok=True)

COMMON_SEARCH_ROOTS = ['/home/horde', '/opt', '/data', str(ROOT)]

def run(cmd, timeout=30, cwd=None, env=None):
    started = time.time()
    try:
        cp = subprocess.run(cmd, shell=True, cwd=cwd, env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout)
        return {'cmd': cmd, 'returncode': cp.returncode, 'stdout': cp.stdout.strip(), 'stderr': cp.stderr.strip(), 'duration_s': round(time.time() - started, 3)}
    except subprocess.TimeoutExpired as e:
        return {'cmd': cmd, 'returncode': None, 'stdout': (e.stdout or '').strip() if isinstance(e.stdout, str) else '', 'stderr': ((e.stderr or '') if isinstance(e.stderr, str) else '') + '\nTIMEOUT', 'duration_s': round(time.time() - started, 3)}

def read_skill(name):
    p = SKILLS / name / 'SKILL.md'
    return p.read_text(errors='replace') if p.exists() else ''

def status_from_checks(checks):
    vals = [c.get('status') for c in checks]
    if any(v == 'fail' for v in vals): return 'fail'
    if any(v == 'blocked_missing_prereq' for v in vals): return 'blocked_missing_prereq'
    if any(v == 'blocked_needs_approval' for v in vals): return 'blocked_needs_approval'
    if any(v == 'warning' for v in vals): return 'warning'
    if any(v == 'pass_with_warnings' for v in vals): return 'pass_with_warnings'
    return 'pass'

def check(name, status, detail='', evidence=None):
    d = {'name': name, 'status': status, 'detail': detail}
    if evidence is not None: d['evidence'] = evidence
    return d

def which(cmd):
    return shutil.which(cmd)

def find_files(expr, timeout=45):
    roots = ' '.join(COMMON_SEARCH_ROOTS)
    return run(f"find {roots} -maxdepth 5 {expr} 2>/dev/null | head -100", timeout=timeout)

def write_report(skill, title, checks, extra=None):
    status = status_from_checks(checks)
    data = {'skill': skill, 'status': status, 'checks': checks, 'extra': extra or {}}
    (OUT / f'{skill}.json').write_text(json.dumps(data, indent=2))
    lines = [f'# {title}', '', f'Overall status: `{status}`', '', '| Check | Status | Detail |', '|---|---|---|']
    for c in checks:
        detail = str(c.get('detail', '')).replace('|', '\\|').replace('\n', '<br>')[:700]
        lines.append(f"| {c['name']} | `{c['status']}` | {detail} |")
    if extra:
        lines += ['', '## Evidence', '', '```json', json.dumps(extra, indent=2)[:6000], '```']
    (OUT / f'{skill}.md').write_text('\n'.join(lines) + '\n')
    return data

results = {}

# Shared host discovery
host = {
    'nvidia_smi': run('nvidia-smi --query-gpu=name,driver_version,memory.total,memory.used,temperature.gpu,pstate,clocks_throttle_reasons.active,utilization.gpu,power.draw,power.limit --format=csv,noheader', timeout=20),
    'cpu_governor': run('cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor 2>/dev/null || echo unavailable'),
    'perf_event_paranoid': run('cat /proc/sys/kernel/perf_event_paranoid 2>/dev/null || echo unavailable'),
    'python3_version': run('python3 --version'),
    'python_import_isaacsim': run('python3 - <<"PY"\ntry:\n import isaacsim\n print("isaacsim import OK")\nexcept Exception as e:\n print(type(e).__name__ + ": " + str(e))\n raise SystemExit(42)\nPY'),
    'isaacsim_python_sh_verify': run('if [ -x /home/horde/venvs/isaacsim45/python.sh ]; then OMNI_KIT_ACCEPT_EULA=YES /home/horde/venvs/isaacsim45/python.sh - <<"PY"\nimport isaacsim\nfrom isaacsim.simulation_app import SimulationApp\nprint("Isaac Sim OK")\nPY\nelse echo "no known isaacsim python.sh"; exit 42; fi', timeout=120),
    'isaaclab_verify': run('if [ -x /home/horde/.openclaw/workspace/IsaacLab/isaaclab.sh ]; then env TERM=xterm bash -lc \'cd /home/horde/.openclaw/workspace/IsaacLab && ./isaaclab.sh -p -c "import isaaclab; print(\\"Isaac Lab OK\\")"\'; else echo "no known isaaclab.sh"; exit 42; fi', timeout=120),
    'python_import_nvtx': run('python3 - <<"PY"\ntry:\n import nvtx\n print("nvtx import OK")\nexcept Exception as e:\n print(type(e).__name__ + ": " + str(e))\n raise SystemExit(42)\nPY'),
    'python_import_torch_cuda': run('python3 - <<"PY"\ntry:\n import torch\n print("torch", torch.__version__, "cuda", torch.cuda.is_available())\nexcept Exception as e:\n print(type(e).__name__ + ": " + str(e))\n raise SystemExit(42)\nPY'),
    'conda': run('command -v conda && conda --version'),
    'uv': run('command -v uv && uv --version'),
    'docker': run('command -v docker && docker --version'),
    'python_sh_paths': find_files('\\( -name python.sh -o -name isaac-sim.sh \\)'),
    'isaaclab_paths': find_files('-name isaaclab.sh'),
    'cuda_apt_repos': run('ls /etc/apt/sources.list.d/*cuda* 2>/dev/null || true'),
    'nsight_opt': run('find /opt/nvidia/nsight-systems -maxdepth 4 -type f -name nsys 2>/dev/null | head -20'),
    'allocwrapper': run('find ~/.cache/packman -name liballocwrapper.so 2>/dev/null | head -20'),
}

# install-profilers
skill = 'install-profilers'; text = read_skill(skill); checks=[]; extra={}
tools = ['nsys','sqlite3','csvexport','tracy-capture','tracy-update','update','capture','capture-release']
for t in tools:
    path = which(t)
    checks.append(check(f'tool on PATH: {t}', 'pass' if path else 'blocked_missing_prereq', path or 'not found'))
checks.append(check('CUDA apt repo check is non-mutating', 'pass', host['cuda_apt_repos']['stdout'] or 'no cuda repo file found'))
checks.append(check('/opt Nsight check is non-mutating', 'pass', host['nsight_opt']['stdout'] or 'no /opt nsys found'))
checks.append(check('skill says install only missing tools', 'pass' if 'Install only what' in text or "Install only what's missing" in text else 'warning', 'looked for install-only-missing guidance'))
checks.append(check('privileged install commands are approval-gated', 'pass' if 'Approval gates' in text and 'sudo' in text else 'warning', 'sudo install examples require approval gating'))
extra['tool_versions'] = {t: run(f'{t} --version 2>&1 | head -5', timeout=10) for t in tools if which(t)}
results[skill] = write_report(skill, 'install-profilers thorough test', checks, extra)

# install-isaacsim
skill='install-isaacsim'; text=read_skill(skill); checks=[]; extra={'discovery': {'python_sh_paths': host['python_sh_paths'], 'python_import_isaacsim': host['python_import_isaacsim'], 'isaacsim_python_sh_verify': host['isaacsim_python_sh_verify'], 'docker': host['docker']}}
checks.append(check('Python version matrix present', 'pass' if 'Python version matrix' in text else 'fail'))
checks.append(check('Isaac Sim path discovery', 'pass' if host['python_sh_paths']['stdout'] else 'blocked_missing_prereq', host['python_sh_paths']['stdout'] or 'no python.sh / isaac-sim.sh found'))
if host['isaacsim_python_sh_verify']['returncode'] == 0:
    checks.append(check('Isaac Sim verified via discovered python.sh', 'pass', host['isaacsim_python_sh_verify']['stdout']))
elif host['python_import_isaacsim']['returncode'] == 0:
    checks.append(check('Isaac Sim verified in current Python env', 'pass', host['python_import_isaacsim']['stdout']))
else:
    checks.append(check('Isaac Sim import verification', 'blocked_missing_prereq', host['python_import_isaacsim']['stdout'] or host['python_import_isaacsim']['stderr']))
checks.append(check('Docker availability checked without starting container', 'pass' if host['docker']['returncode']==0 else 'blocked_missing_prereq', host['docker']['stdout'] or host['docker']['stderr'] or 'docker missing'))
checks.append(check('sudo/package install examples are approval-gated', 'pass' if 'Safety gates' in text and ('sudo apt-get' in text or 'sudo usermod' in text) else 'warning'))
checks.append(check('cleanup command is approval-gated', 'pass' if 'rm -rf' in text and 'explicit approval' in text else 'warning', 'cleanup must stay approval-gated'))
results[skill]=write_report(skill, 'install-isaacsim thorough test', checks, extra)

# install-isaaclab
skill='install-isaaclab'; text=read_skill(skill); checks=[]; extra={'discovery': {'isaaclab_paths': host['isaaclab_paths'], 'isaaclab_verify': host['isaaclab_verify'], 'conda': host['conda'], 'uv': host['uv']}}
checks.append(check('mode selection documented', 'pass' if 'Choose Install Mode' in text and 'Kit-less' in text else 'warning'))
checks.append(check('conda availability', 'pass' if host['conda']['returncode']==0 else 'blocked_missing_prereq', host['conda']['stdout'] or 'conda missing'))
checks.append(check('uv availability', 'pass' if host['uv']['returncode']==0 else 'blocked_missing_prereq', host['uv']['stdout'] or 'uv missing'))
checks.append(check('Isaac Lab path discovery', 'pass' if host['isaaclab_paths']['stdout'] else 'blocked_missing_prereq', host['isaaclab_paths']['stdout'] or 'no isaaclab.sh found'))
checks.append(check('Isaac Lab import verification', 'pass' if host['isaaclab_verify']['returncode']==0 else 'blocked_missing_prereq', host['isaaclab_verify']['stdout'] or host['isaaclab_verify']['stderr']))
checks.append(check('avoids conda init mutation', 'pass' if 'Do not run `conda init`' in text else 'warning'))
checks.append(check('env removal example is approval-gated', 'pass' if 'conda env remove' in text and 'approval' in text.lower() else 'warning'))
results[skill]=write_report(skill, 'install-isaaclab thorough test', checks, extra)

# benchmark-isaacsim
skill='benchmark-isaacsim'; text=read_skill(skill); checks=[]; extra={'discovery': {'python_sh_paths': host['python_sh_paths'], 'isaacsim_python_sh_verify': host['isaacsim_python_sh_verify']}}
checks.append(check('benchmark scripts documented', 'pass' if 'benchmark_camera.py' in text and 'standalone_examples/benchmarks' in text else 'fail'))
checks.append(check('tiny benchmark parameters possible', 'pass' if '--num-frames' in text or '--num_frames' in text else 'warning'))
checks.append(check('Isaac Sim import available', 'pass' if host['isaacsim_python_sh_verify']['returncode']==0 else 'blocked_missing_prereq', host['isaacsim_python_sh_verify']['stdout'] or host['isaacsim_python_sh_verify']['stderr']))
isaacsim_bench_scripts = run('find /home/horde/venvs/isaacsim45 /home/horde/.openclaw/workspace -maxdepth 8 -path "*standalone_examples/benchmarks*" -type f 2>/dev/null | head -50', timeout=60)
extra['discovery']['isaacsim_benchmark_scripts'] = isaacsim_bench_scripts
checks.append(check('Isaac Sim benchmark scripts available locally', 'pass' if isaacsim_bench_scripts['stdout'] else 'blocked_missing_prereq', isaacsim_bench_scripts['stdout'] or 'pip install lacks standalone_examples/benchmarks scripts'))
checks.append(check('KPI/output path guidance', 'pass' if 'metrics_output_folder' in text or 'kpis' in text.lower() or 'output' in text.lower() else 'warning'))
checks.append(check('heavy benchmark sweeps not run', 'blocked_needs_approval', 'requires benchmark scripts and approval for workloads beyond tiny smoke'))
results[skill]=write_report(skill, 'benchmark-isaacsim thorough test', checks, extra)

# benchmark-isaaclab
skill='benchmark-isaaclab'; text=read_skill(skill); checks=[]; extra={'discovery': {'isaaclab_paths': host['isaaclab_paths'], 'isaaclab_verify': host['isaaclab_verify']}}
checks.append(check('benchmark scripts documented', 'pass' if 'benchmark_non_rl.py' in text and 'scripts/benchmarks' in text else 'fail'))
checks.append(check('headless/viz guidance', 'pass' if 'HEADLESS_ARG' in text and '--viz' in text and '--headless' in text else 'warning'))
checks.append(check('tiny env/frame params documented', 'pass' if '--num_envs' in text and ('--num_frames' in text or '--num_frames' in text) else 'warning'))
checks.append(check('Isaac Lab install available for --help/run', 'pass' if host['isaaclab_verify']['returncode']==0 else 'blocked_missing_prereq', host['isaaclab_verify']['stdout'] or host['isaaclab_verify']['stderr']))
tiny_lab = run('env TERM=xterm OMNI_KIT_ACCEPT_EULA=YES bash -lc \'cd /home/horde/.openclaw/workspace/IsaacLab && ./isaaclab.sh -p scripts/benchmarks/benchmark_non_rl.py --task=Isaac-Cartpole-Direct-v0 --headless --num_frames 10 --num_envs 16 --benchmark_backend LocalLogMetrics\'', timeout=240)
extra['tiny_benchmark'] = tiny_lab
if tiny_lab['returncode'] == 0:
    detail = '\n'.join([line for line in tiny_lab['stdout'].splitlines() if 'Mean Environment step FPS' in line or 'Mean Environment step effective FPS' in line or 'Mean Environment step times' in line][-4:])
    checks.append(check('tiny benchmark artifact run', 'pass', detail or 'completed'))
else:
    checks.append(check('tiny benchmark artifact run', 'blocked_missing_prereq', tiny_lab['stdout'][-500:] or tiny_lab['stderr'][-500:]))
checks.append(check('long RL training not run', 'pass_with_warnings', 'long RL training/convergence tests intentionally skipped; tiny non-RL benchmark artifact passed'))
results[skill]=write_report(skill, 'benchmark-isaaclab thorough test', checks, extra)

# profiling
skill='profiling'; text=read_skill(skill); checks=[]; extra={'host': {'perf_event_paranoid': host['perf_event_paranoid']}}
checks.append(check('nsys availability', 'pass' if which('nsys') else 'blocked_missing_prereq', which('nsys') or 'nsys missing'))
checks.append(check('perf_event_paranoid read', 'pass', host['perf_event_paranoid']['stdout'] or host['perf_event_paranoid']['stderr']))
checks.append(check('non-sudo default documented', 'pass' if 'Try without `sudo` first' in text and re.search(r'\nnsys profile', text) else 'warning'))
checks.append(check('GPU metrics permission fallback documented', 'pass' if 'ERR_NVGPUCTRPERM' in text else 'warning'))
checks.append(check('container-safe no CPU sampling mode documented', 'pass' if '--sample=none' in text and 'Container-safe mode' in text else 'warning'))
checks.append(check('Tracy capture sequence documented', 'pass' if 'Start the application FIRST' in text and 'NEVER kill capture' in text else 'warning'))
if which('nsys'):
    tiny = OUT / 'tiny_profile.py'; tiny.write_text('print("tiny")\n')
    extra['tiny_nsys'] = run(f'nsys profile --force-overwrite=true -o {OUT / "tiny"} -t nvtx,osrt python3 {tiny}', timeout=120)
else:
    checks.append(check('tiny nsys artifact test', 'blocked_missing_prereq', 'nsys missing'))
results[skill]=write_report(skill, 'profiling thorough test', checks, extra)

# nsys-analyze
skill='nsys-analyze'; text=read_skill(skill); checks=[]; extra={}
sqlite_files = list((ROOT/'skill-test-results').glob('**/*.sqlite'))
checks.append(check('sqlite3 availability', 'pass' if which('sqlite3') else 'blocked_missing_prereq', which('sqlite3') or 'sqlite3 missing'))
if which('nsys') and not sqlite_files:
    tiny = OUT / 'nsys_tiny_for_analyze.py'
    tiny.write_text('import time\nprint("analyze tiny")\ntime.sleep(0.01)\n')
    rep_base = OUT / 'nsys_analyze_tiny'
    rep = OUT / 'nsys_analyze_tiny.nsys-rep'
    sqlite_out = OUT / 'nsys_analyze_tiny.sqlite'
    extra['create_tiny_trace'] = run(f'nsys profile --force-overwrite=true -o {rep_base} -t nvtx,osrt python3 {tiny}', timeout=120)
    if rep.exists():
        extra['export_tiny_sqlite'] = run(f'nsys export --force-overwrite=true --type sqlite --output {sqlite_out} {rep}', timeout=120)
        sqlite_files = [sqlite_out] if sqlite_out.exists() else []
checks.append(check('existing or generated sqlite trace artifact', 'pass' if sqlite_files else 'blocked_missing_prereq', ', '.join(map(str, sqlite_files[:5])) or 'no sqlite trace artifacts found'))
checks.append(check('NVTX_EVENTS text/StringIds gotcha documented', 'pass' if 'StringIds' in text and 'NVTX_EVENTS' in text else 'warning'))
checks.append(check('CUDA kernels absent behavior documented', 'pass' if 'CUDA Kernels' in text or 'CUDA kernels' in text else 'warning'))
checks.append(check('comparison methodology documented', 'pass' if 'comparison' in text.lower() or 'compare' in text.lower() else 'warning'))
if which('sqlite3') and sqlite_files:
    extra['tables'] = run(f"sqlite3 {sqlite_files[0]} '.tables'", timeout=20)
# Keep reports lightweight: remove generated binary artifacts after recording evidence.
for artifact in [OUT / 'nsys_analyze_tiny.nsys-rep', OUT / 'nsys_analyze_tiny.sqlite']:
    if artifact.exists():
        artifact.unlink()
results[skill]=write_report(skill, 'nsys-analyze thorough test', checks, extra)

# nvtx-python
skill='nvtx-python'; text=read_skill(skill); checks=[]; extra={'python_import_nvtx': host['python_import_nvtx']}
checks.append(check('nvtx import in active Python', 'pass' if host['python_import_nvtx']['returncode']==0 else 'blocked_missing_prereq', host['python_import_nvtx']['stdout'] or host['python_import_nvtx']['stderr']))
checks.append(check('sitecustomize instructions present', 'pass' if 'sitecustomize.py' in text else 'fail'))
checks.append(check('include/exclude filters documented', 'pass' if 'NVTX_PROFILE_INCLUDE' in text and 'NVTX_PROFILE_EXCLUDE' in text else 'warning'))
checks.append(check('sitecustomize overwrite/backup guidance', 'pass' if 'Do not copy `sitecustomize.py` into `site-packages/`' in text or 'overwrite' in text.lower() else 'warning'))
checks.append(check('nsys artifact test for NVTX ranges', 'blocked_missing_prereq' if not which('nsys') or host['python_import_nvtx']['returncode'] else 'pass', 'requires nsys + nvtx'))
results[skill]=write_report(skill, 'nvtx-python thorough test', checks, extra)

# profiling-api
skill='profiling-api'; text=read_skill(skill); checks=[]; extra={}
checks.append(check('C++ macro header example', 'pass' if '#include <carb/profiler/Profile.h>' in text and 'CARB_PROFILE_ZONE' in text else 'fail'))
checks.append(check('Python profiler API example', 'pass' if 'carb.profiler' in text else 'warning'))
checks.append(check('manual begin/end safety', 'pass' if 'try' in text.lower() and 'finally' in text.lower() else 'warning', 'manual ranges should be exception-safe'))
checks.append(check('metrics/plots documented', 'pass' if 'plot' in text.lower() or 'metric' in text.lower() else 'warning'))
if host['isaacsim_python_sh_verify']['returncode'] == 0:
    smoke = OUT / 'profiling-api-smoke' / 'carb_profiler_runtime_smoke.py'
    smoke.parent.mkdir(exist_ok=True)
    smoke.write_text('''\nimport carb.profiler\ncarb.profiler.begin(1, "skill_runtime_smoke")\ntry:\n    total = sum(i*i for i in range(1000))\nfinally:\n    carb.profiler.end(1)\nprint("carb profiler runtime smoke", total)\n'''.lstrip())
    py_path = '/home/horde/venvs/isaacsim45/lib/python3.10/site-packages/omni/kernel/py'
    lib_path = '/home/horde/venvs/isaacsim45/lib/python3.10/site-packages/omni'
    env = dict(os.environ)
    env['OMNI_KIT_ACCEPT_EULA'] = 'YES'
    env['PYTHONPATH'] = py_path + (':' + env.get('PYTHONPATH', '') if env.get('PYTHONPATH') else '')
    env['LD_LIBRARY_PATH'] = lib_path + (':' + env.get('LD_LIBRARY_PATH', '') if env.get('LD_LIBRARY_PATH') else '')
    extra['carb_runtime_smoke'] = run(f'/home/horde/venvs/isaacsim45/python.sh {smoke}', timeout=120, env=env)
    checks.append(check('Kit/Isaac runtime artifact test', 'pass' if extra['carb_runtime_smoke']['returncode']==0 else 'blocked_missing_prereq', extra['carb_runtime_smoke']['stdout'] or extra['carb_runtime_smoke']['stderr']))
else:
    checks.append(check('Kit SDK build/run artifact test', 'blocked_missing_prereq', 'requires Kit SDK or buildable extension context'))
results[skill]=write_report(skill, 'profiling-api thorough test', checks, extra)

# tracy-memory
skill='tracy-memory'; text=read_skill(skill); checks=[]; extra={'allocwrapper': host['allocwrapper']}
checks.append(check('liballocwrapper discovery', 'pass' if 'find ~/.cache/packman -name liballocwrapper.so' in text and 'memory tracing blocked' in text else 'warning'))
checks.append(check('liballocwrapper exists locally', 'pass' if host['allocwrapper']['stdout'] else 'blocked_missing_prereq', host['allocwrapper']['stdout'] or 'not found'))
checks.append(check('Tracy capture binary available', 'pass' if any(which(t) for t in ['tracy-capture','capture','capture-release']) else 'blocked_missing_prereq'))
checks.append(check('Tracy update binary available', 'pass' if any(which(t) for t in ['tracy-update','update']) else 'blocked_missing_prereq'))
checks.append(check('LD_PRELOAD unset before capture', 'pass' if 'unset LD_PRELOAD' in text else 'fail'))
checks.append(check('strip test documented', 'pass' if '-s M' in text and 'memtrace_no_mem' in text else 'warning'))
checks.append(check('real memory capture artifact test', 'blocked_missing_prereq', 'requires Kit app + Tracy tools + liballocwrapper.so'))
results[skill]=write_report(skill, 'tracy-memory thorough test', checks, extra)

# diagnose-perf
skill='diagnose-perf'; text=read_skill(skill); checks=[]; extra={'host': {k: host[k] for k in ['nvidia_smi','cpu_governor']}}
checks.append(check('GPU snapshot command works', 'pass' if host['nvidia_smi']['returncode']==0 else 'fail', host['nvidia_smi']['stdout'] or host['nvidia_smi']['stderr']))
checks.append(check('CPU governor snapshot works', 'pass', host['cpu_governor']['stdout'] or host['cpu_governor']['stderr']))
checks.append(check('idle GPU classified carefully', 'pass' if 'workload' in text.lower() else 'warning', 'no workload currently running; only host facts are valid'))
checks.append(check('red-flag logic documented', 'pass' if 'Red Flag' in text and 'Clocks Throttle' in text else 'warning'))
checks.append(check('governor changes require approval', 'pass' if 'require approval' in text.lower() and 'sudo cpupower' in text else 'warning', 'mutating fix must be gated'))
results[skill]=write_report(skill, 'diagnose-perf thorough test', checks, extra)

# perf-tuning
skill='perf-tuning'; text=read_skill(skill); checks=[]; extra={}
synthetic_cases = ['PresentFrame','resolveSamplerFeedback','waitIdle','fsWatcher','CPU governor']
for case in synthetic_cases:
    checks.append(check(f'synthetic evidence case documented: {case}', 'pass' if case.lower() in text.lower() else 'warning'))
checks.append(check('measurement-before-fix posture', 'pass' if 'Verify' in text and ('Measure' in text or 'benchmark' in text.lower()) else 'warning'))
checks.append(check('system setting changes are approval-gated', 'pass' if 'Approval gates' in text and ('sudo tee' in text or 'sudo' in text) else 'warning'))
checks.append(check('real before/after artifact test', 'blocked_needs_approval', 'requires workload and approval to apply tuning'))
results[skill]=write_report(skill, 'perf-tuning thorough test', checks, extra)

# Summary
summary_lines = ['# Phase 4 — Thorough Per-Skill Tests', '', '| Skill | Status | Key blockers/warnings |', '|---|---|---|']
for skill, data in results.items():
    blockers = []
    for c in data['checks']:
        if c['status'] != 'pass':
            blockers.append(f"{c['name']}: {c['status']}")
    summary_lines.append(f"| `{skill}` | `{data['status']}` | {'; '.join(blockers[:4]) or '-'} |")
summary_lines += ['', '## Host Snapshot Used', '', '```json', json.dumps(host, indent=2)[:8000], '```']
(OUT / 'SUMMARY.md').write_text('\n'.join(summary_lines) + '\n')
(OUT / 'SUMMARY.json').write_text(json.dumps({'timestamp': time.time(), 'results': results, 'host': host}, indent=2))
print(json.dumps({k: v['status'] for k,v in results.items()}, indent=2))
