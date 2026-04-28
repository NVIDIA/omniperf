#!/usr/bin/env python3
"""OmniPerf AgentSkill eval helpers.

This script keeps authored eval cases in the Agent Skills convention:
  .agents/skills/<skill>/evals/evals.json

It writes only lightweight markdown evidence under:
  .agents/skills/eval-results/
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / ".agents" / "skills"
INSTALLED = Path("/home/horde/.openclaw/workspace/skills")
RESULTS = SKILLS / "eval-results"

RISK_PATTERNS = [
    r"\bsudo\b",
    r"\bapt(-get)?\s+install\b",
    r"\brm\s+-rf\b",
    r"\bconda\s+env\s+remove\b",
    r"\bmkfs\b",
    r"\bdd\s+if=",
    r"\bchmod\s+-R\s+777\b",
    r"LD_PRELOAD",
    r"\bkillall\b",
]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def parse_frontmatter(text: str) -> tuple[dict[str, str], bool]:
    if not text.startswith("---"):
        return {}, False
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, False
    fm = {}
    for line in parts[1].splitlines():
        line = line.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        key, value = line.split(":", 1)
        fm[key.strip()] = value.strip().strip("'\"")
    return fm, True


def all_skill_dirs() -> list[Path]:
    return sorted(p.parent for p in SKILLS.glob("*/SKILL.md"))


def load_evals(skill_dir: Path) -> tuple[dict[str, Any] | None, list[str]]:
    path = skill_dir / "evals" / "evals.json"
    if not path.exists():
        return None, ["missing_evals_json"]
    issues = []
    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        return None, [f"invalid_evals_json:{exc}"]
    if data.get("skill_name") != skill_dir.name:
        issues.append(f"skill_name_mismatch:{data.get('skill_name')}!={skill_dir.name}")
    cases = data.get("evals")
    if not isinstance(cases, list) or not cases:
        issues.append("empty_evals")
    else:
        seen = set()
        for i, case in enumerate(cases):
            cid = case.get("id")
            if not cid:
                issues.append(f"eval_{i}_missing_id")
            elif cid in seen:
                issues.append(f"duplicate_eval_id:{cid}")
            seen.add(cid)
            for field in ["prompt", "expected_output"]:
                if not isinstance(case.get(field), str) or not case[field].strip():
                    issues.append(f"eval_{cid or i}_missing_{field}")
            assertions = case.get("assertions", [])
            if not isinstance(assertions, list) or not assertions:
                issues.append(f"eval_{cid or i}_missing_assertions")
    return data, issues


def static_validation() -> None:
    RESULTS.mkdir(parents=True, exist_ok=True)
    skills = []
    name_counts: dict[str | None, int] = {}
    for skill_dir in all_skill_dirs():
        skill_md = skill_dir / "SKILL.md"
        text = skill_md.read_text(errors="replace")
        fm, has_fm = parse_frontmatter(text)
        name = fm.get("name")
        desc = fm.get("description")
        dirname = skill_dir.name
        name_counts[name] = name_counts.get(name, 0) + 1
        risky = []
        for pattern in RISK_PATTERNS:
            for match in re.finditer(pattern, text, flags=re.I):
                start = max(0, text.rfind("\n", 0, match.start()) + 1)
                end = text.find("\n", match.end())
                if end < 0:
                    end = len(text)
                risky.append({
                    "pattern": pattern,
                    "line": text.count("\n", 0, match.start()) + 1,
                    "snippet": text[start:end][:240],
                })
        installed_md = INSTALLED / dirname / "SKILL.md"
        installed_status = "missing"
        if installed_md.exists():
            installed_status = "match" if sha256(skill_md) == sha256(installed_md) else "differs"
        _, eval_issues = load_evals(skill_dir)
        issues = []
        warnings = []
        if not has_fm:
            issues.append("missing_frontmatter")
        if not name:
            issues.append("missing_name")
        if not desc:
            issues.append("missing_description")
        if name and name != dirname:
            issues.append(f"name_directory_mismatch:{name}!={dirname}")
        if desc and len(desc) < 40:
            warnings.append("short_description")
        if installed_status != "match":
            issues.append(f"installed_copy_{installed_status}")
        issues.extend(eval_issues)
        if risky:
            warnings.append("contains_risky_or_privileged_commands_review_required")
        skills.append({
            "directory": dirname,
            "name": name,
            "description": desc,
            "has_frontmatter": has_fm,
            "installed_status": installed_status,
            "issues": issues,
            "warnings": warnings,
            "risky_matches": risky,
            "path": str(skill_md.relative_to(ROOT)),
            "evals_path": str((skill_dir / "evals" / "evals.json").relative_to(ROOT)),
        })
    for skill in skills:
        if skill["name"] and name_counts.get(skill["name"], 0) > 1:
            skill["issues"].append("duplicate_name")

    phase0 = {
"repo": str(ROOT),
        "skills": skills,
        "summary": {
            "skill_count": len(skills),
            "pass_count": sum(1 for s in skills if not s["issues"]),
            "fail_count": sum(1 for s in skills if s["issues"]),
            "warning_count": sum(1 for s in skills if s["warnings"]),
        },
    }
    lines = [
        "# Phase 0 — Static Skill Validation",
        "",
        "| Skill | Status | Installed copy | Evals | Issues | Warnings |",
        "|---|---|---|---|---|---|",
    ]
    for s in skills:
        status = "pass" if not s["issues"] else "fail"
        eval_status = "present" if "missing_evals_json" not in s["issues"] else "missing"
        lines.append(
            f"| `{s['directory']}` | {status} | {s['installed_status']} | {eval_status} | "
            f"{', '.join(s['issues']) or '-'} | {', '.join(s['warnings']) or '-'} |"
        )
    lines += ["", "## Risky / privileged command matches needing review", ""]
    for s in skills:
        if s["risky_matches"]:
            lines.append(f"### `{s['directory']}`")
            for r in s["risky_matches"][:20]:
                snippet = r["snippet"].replace("|", "\\|")
                lines.append(f"- line {r['line']}: `{snippet}`")
            if len(s["risky_matches"]) > 20:
                lines.append(f"- ... {len(s['risky_matches']) - 20} more")
            lines.append("")
    (RESULTS / "static-validation.md").write_text("\n".join(lines) + "\n")

    print(json.dumps({"phase0": phase0["summary"]}, indent=2))


def evals_summary() -> None:
    rows = []
    aggregate = {"skill_count": 0, "eval_count": 0, "assertion_count": 0}
    for skill_dir in all_skill_dirs():
        data, issues = load_evals(skill_dir)
        cases = data.get("evals", []) if data else []
        assertion_count = sum(len(c.get("assertions", [])) for c in cases if isinstance(c, dict))
        rows.append({
            "skill": skill_dir.name,
            "path": str((skill_dir / "evals" / "evals.json").relative_to(ROOT)),
            "eval_count": len(cases),
            "assertion_count": assertion_count,
            "issues": issues,
        })
        aggregate["skill_count"] += 1
        aggregate["eval_count"] += len(cases)
        aggregate["assertion_count"] += assertion_count
    RESULTS.mkdir(parents=True, exist_ok=True)
    lines = [
        "# AgentSkill Evals Summary",
        "",
        "Authored eval cases live beside each skill at `.agents/skills/<skill>/evals/evals.json`.",
        "Generated run results are intentionally kept to this small markdown summary.",
        "",
        "| Skill | Evals | Assertions | Issues |",
        "|---|---:|---:|---|",
    ]
    for row in rows:
        lines.append(f"| `{row['skill']}` | {row['eval_count']} | {row['assertion_count']} | {', '.join(row['issues']) or '-'} |")
    lines += ["", f"Total evals: `{aggregate['eval_count']}`", f"Total assertions: `{aggregate['assertion_count']}`", ""]
    (RESULTS / "evals-summary.md").write_text("\n".join(lines))
    print(json.dumps(aggregate, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description="OmniPerf AgentSkill eval helper")
    parser.add_argument("command", choices=["static-validation", "evals-summary"])
    args = parser.parse_args()
    if args.command == "static-validation":
        static_validation()
    elif args.command == "evals-summary":
        evals_summary()


if __name__ == "__main__":
    main()
