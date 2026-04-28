# OmniPerf Agent Skills Test Plan

Validate that OmniPerf AgentSkills are discoverable, safe to invoke, and useful in the Isaac Sim / Isaac Lab / Kit performance workflow.

This plan is centered on per-skill eval manifests. Keep authored cases in `.agents/skills/<skill>/evals/evals.json`; keep only tiny markdown summaries in `.agents/skills/eval-results/`. Do not commit runtime artifacts or host-specific logs.

## Scope

Skills under `.agents/skills/`:

- `install-profilers`
- `install-isaacsim`
- `install-isaaclab`
- `benchmark-isaacsim`
- `benchmark-isaaclab`
- `profiling`
- `nsys-analyze`
- `nvtx-python`
- `profiling-api`
- `tracy-memory`
- `diagnose-perf`
- `perf-tuning`

## Pass / Fail Criteria

A skill passes if it has:

1. Valid frontmatter with matching `name` and directory name.
2. A clear `description` with trigger conditions and boundaries.
3. Explicit prerequisites and copy-pastable commands.
4. Approval gates for privileged or destructive actions (`sudo`, installs, cleanup, system settings).
5. A clear recovery path when dependencies are missing.
6. Useful adjacent-skill redirects where the task belongs elsewhere.
7. At least one representative positive test and one negative/boundary test.
8. Artifact expectations: install/version output, benchmark KPI, trace file, SQL/table output, or explicit blocked status.

## Phase 0 — Static Validation

Run a static scan over every `SKILL.md`:

- Parse YAML frontmatter.
- Check unique names.
- Check directory/name match.
- Flag privileged or risky commands for review.
- Check descriptions include trigger boundaries and, where relevant, NOT-for clauses.
- Check command blocks for unresolved placeholders (`<...>`) without nearby discovery guidance.
- Verify local installed copies, if applicable, match the repo source under test.

Expected output:

- `.agents/skills/eval-results/static-validation.md`

## Phase 2 — Eval Cases / Prompt Selection Smoke Tests

Dry-run only. Do not install, use sudo, run benchmarks, or start heavy GPU workloads.

Anthropic Agent Skills convention: authored eval cases live beside each skill at `.agents/skills/<skill>/evals/evals.json`. Each case has `id`, `prompt`, `expected_output`, and `assertions`.

Representative prompts now captured in `evals/evals.json` files:

- `install-profilers`: “Check what profiler tools are installed and tell me the missing install steps. Do not install anything.”
- `install-isaacsim`: “Plan a pip-based Isaac Sim install for version 5.1 on Ubuntu. Do not install.”
- `install-isaaclab`: “Plan an Isaac Lab install linked to an existing Isaac Sim. Do not install.”
- `diagnose-perf`: “Given low FPS in Isaac Sim, perform a no-profiling triage plan.”
- `benchmark-isaacsim`: “Plan a tiny headless Isaac Sim benchmark smoke test.”
- `benchmark-isaaclab`: “Plan a tiny Isaac Lab env-step FPS smoke test.”
- `profiling`: “Plan a 10-second Nsight Systems capture for a Kit app.”
- `nsys-analyze`: “Given a `.nsys-rep`, list the analysis commands and expected tables.”
- `nvtx-python`: “Show a minimal Python NVTX function-range test.”
- `profiling-api`: “Show minimal C++ and Python profiling-zone examples for Kit.”
- `tracy-memory`: “Plan a Tracy memory capture and explain required `LD_PRELOAD` handling.”
- `perf-tuning`: “Given PresentFrame stalls and GPU saturation, recommend measurable fixes.”

Expected authored eval files and generated summaries:

- `.agents/skills/<skill>/evals/evals.json` for every skill
- `.agents/skills/eval-results/evals-summary.md`

## Phase 3 — Runtime / Tooling Checks

Runtime smoke checks are no longer authored as repository test files. Add or update per-skill cases in `.agents/skills/<skill>/evals/evals.json`; if an eval run produces artifacts, keep them in an external eval workspace or temporary directory rather than committing them under this repo.

## Phase 4 — Per-Skill Thorough Tests

Thorough cases now belong in each skill's `.agents/skills/<skill>/evals/evals.json` file. Keep positive, negative/boundary, safety, and artifact expectations as eval `prompt`, `expected_output`, and `assertions` entries. Do not commit generated traces, benchmark outputs, or ad-hoc phase reports.

## Reporting

Maintain:

- `.agents/skills/<skill>/evals/evals.json` — authored eval cases, Anthropic/Agent Skills convention
- `.agents/skills/eval-results/evals-summary.md` — generated eval inventory
- `.agents/skills/eval-results/static-validation.md` — lightweight static validation evidence

Do not commit ad-hoc runtime outputs, trace files, host snapshots, or bulky generated reports. If deeper runtime evidence is needed, keep it in an external eval workspace and summarize only the durable lesson in the PR.
