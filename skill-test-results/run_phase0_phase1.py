#!/usr/bin/env python3
import json, os, re, shutil, subprocess, sys, time, hashlib
from pathlib import Path

ROOT = Path('/home/horde/.openclaw/workspace/omniperf')
SKILLS = ROOT / '.agents' / 'skills'
INSTALLED = Path('/home/horde/.openclaw/workspace/skills')
OUT = ROOT / 'skill-test-results'
OUT.mkdir(parents=True, exist_ok=True)

RISK_PATTERNS = [
    r'\bsudo\b', r'\bapt(-get)?\s+install\b', r'\brm\s+-rf\b', r'\bconda\s+env\s+remove\b',
    r'\bmkfs\b', r'\bdd\s+if=', r'\bchmod\s+-R\s+777\b', r'LD_PRELOAD', r'\bkillall\b',
]

def sha256(p):
    h=hashlib.sha256()
    h.update(p.read_bytes())
    return h.hexdigest()

def parse_frontmatter(text):
    if not text.startswith('---'):
        return {}, False
    parts=text.split('---',2)
    if len(parts)<3:
        return {}, False
    fm={}
    for line in parts[1].splitlines():
        line=line.strip()
        if not line or line.startswith('#') or ':' not in line:
            continue
        k,v=line.split(':',1)
        fm[k.strip()] = v.strip().strip('"\'')
    return fm, True

def run(cmd, timeout=20):
    try:
        cp=subprocess.run(cmd, shell=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout)
        return {'cmd':cmd,'returncode':cp.returncode,'stdout':cp.stdout.strip(),'stderr':cp.stderr.strip()}
    except subprocess.TimeoutExpired as e:
        return {'cmd':cmd,'returncode':None,'stdout':(e.stdout or '').strip() if isinstance(e.stdout,str) else '', 'stderr':'TIMEOUT'}
    except Exception as e:
        return {'cmd':cmd,'returncode':None,'stdout':'','stderr':repr(e)}

skills=[]
name_counts={}
for skill_md in sorted(SKILLS.glob('*/SKILL.md')):
    text=skill_md.read_text(errors='replace')
    fm, has_fm=parse_frontmatter(text)
    name=fm.get('name')
    desc=fm.get('description')
    dirname=skill_md.parent.name
    name_counts[name]=name_counts.get(name,0)+1
    risky=[]
    for pat in RISK_PATTERNS:
        for m in re.finditer(pat, text, flags=re.I):
            start=max(0, text.rfind('\n',0,m.start())+1)
            end=text.find('\n',m.end())
            if end<0: end=len(text)
            risky.append({'pattern':pat,'line':text.count('\n',0,m.start())+1,'snippet':text[start:end][:240]})
    installed_md=INSTALLED/dirname/'SKILL.md'
    installed_status='missing'
    if installed_md.exists():
        installed_status = 'match' if sha256(skill_md)==sha256(installed_md) else 'differs'
    issues=[]
    warnings=[]
    if not has_fm: issues.append('missing_frontmatter')
    if not name: issues.append('missing_name')
    if not desc: issues.append('missing_description')
    if name and name != dirname: issues.append(f'name_directory_mismatch:{name}!={dirname}')
    if desc and len(desc) < 40: warnings.append('short_description')
    if installed_status != 'match': issues.append(f'installed_copy_{installed_status}')
    if risky: warnings.append('contains_risky_or_privileged_commands_review_required')
    skills.append({
        'directory':dirname,
        'name':name,
        'description':desc,
        'has_frontmatter':has_fm,
        'installed_status':installed_status,
        'issues':issues,
        'warnings':warnings,
        'risky_matches':risky,
        'path':str(skill_md.relative_to(ROOT)),
    })
for s in skills:
    if s['name'] and name_counts.get(s['name'],0)>1:
        s['issues'].append('duplicate_name')

phase0={'timestamp':time.time(),'repo':str(ROOT),'skills':skills,'summary':{
    'skill_count':len(skills),
    'pass_count':sum(1 for s in skills if not s['issues']),
    'fail_count':sum(1 for s in skills if s['issues']),
    'warning_count':sum(1 for s in skills if s['warnings']),
}}
(OUT/'phase0-static-validation.json').write_text(json.dumps(phase0, indent=2))

# markdown summary
lines=['# Phase 0 — Static Skill Validation','','| Skill | Status | Installed copy | Issues | Warnings |','|---|---|---|---|---|']
for s in skills:
    status='pass' if not s['issues'] else 'fail'
    lines.append(f"| `{s['directory']}` | {status} | {s['installed_status']} | {', '.join(s['issues']) or '-'} | {', '.join(s['warnings']) or '-'} |")
lines += ['','## Risky / privileged command matches needing review','']
for s in skills:
    if s['risky_matches']:
        lines.append(f"### `{s['directory']}`")
        for r in s['risky_matches'][:20]:
            snippet = r['snippet'].replace('|', '\\|')
            lines.append(f"- line {r['line']}: `{snippet}`")
        if len(s['risky_matches'])>20:
            lines.append(f"- ... {len(s['risky_matches'])-20} more")
        lines.append('')
(OUT/'phase0-static-validation.md').write_text('\n'.join(lines)+'\n')

# Phase 1 host snapshot
checks={}
commands={
    'uname':'uname -a',
    'os_release':'cat /etc/os-release 2>/dev/null || true',
    'disk_workspace':'df -h /home/horde/.openclaw/workspace',
    'git':'git --version',
    'python3':'python3 --version',
    'python':'python --version 2>/dev/null || true',
    'pip':'python3 -m pip --version 2>/dev/null || true',
    'conda':'conda --version 2>/dev/null || true',
    'uv':'uv --version 2>/dev/null || true',
    'nvidia_smi':'nvidia-smi 2>/dev/null || true',
    'nvidia_smi_query':'nvidia-smi --query-gpu=name,driver_version,memory.total,memory.used,temperature.gpu,pstate,clocks.sm,clocks.mem --format=csv,noheader 2>/dev/null || true',
    'nsys':'nsys --version 2>/dev/null || true',
    'sqlite3':'sqlite3 --version 2>/dev/null || true',
    'csvexport':'csvexport --help 2>/dev/null | head -40 || true',
    'tracy_capture':'which tracy-capture 2>/dev/null || true; tracy-capture --help 2>/dev/null | head -20 || true',
    'common_isaac_paths':'find /home/horde /opt /data -maxdepth 4 \( -name python.sh -o -name isaaclab.sh \) 2>/dev/null | head -100',
}
for k,c in commands.items():
    checks[k]=run(c, timeout=30)
phase1={'timestamp':time.time(),'checks':checks}
(OUT/'phase1-host-prereqs.json').write_text(json.dumps(phase1, indent=2))

lines=['# Phase 1 — Host Prerequisite Snapshot','']
for k,res in checks.items():
    out=res['stdout'] or res['stderr'] or ''
    preview='\n'.join(out.splitlines()[:20])
    lines.append(f'## {k}')
    lines.append('')
    lines.append(f'- return code: `{res["returncode"]}`')
    lines.append('')
    lines.append('```text')
    lines.append(preview[:4000])
    lines.append('```')
    lines.append('')
(OUT/'phase1-host-prereqs.md').write_text('\n'.join(lines)+'\n')

print(json.dumps({'phase0':phase0['summary'], 'phase1_checks':len(checks)}, indent=2))
