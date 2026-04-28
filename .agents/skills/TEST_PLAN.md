# OmniPerf Agent Skills Test Plan

Validate that OmniPerf AgentSkills are discoverable, safe to invoke, and useful in the Isaac Sim / Isaac Lab / Kit performance workflow.

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

## Phase 0 — Static Validation

Run a static scan over every `SKILL.md`:

- Parse YAML frontmatter.
- Check unique names.
- Check directory/name match.
- Flag privileged or risky commands for review.
- Verify local installed copies, if applicable, match the repo source under test.

Expected output:

- `skill-test-results/phase0-static-validation.md`
- `skill-test-results/phase0-static-validation.json`

## Phase 1 — Host Prerequisite Snapshot

Use non-mutating checks only:

- OS/kernel.
- NVIDIA driver/GPU via `nvidia-smi`.
- Python, pip, conda, uv.
- `nsys`, `sqlite3`, `csvexport`, `tracy-capture`.
- Existing Isaac Sim / Isaac Lab paths.
- Disk space.

Expected output:

- `skill-test-results/phase1-host-prereqs.md`
- `skill-test-results/phase1-host-prereqs.json`

## Phase 2 — Prompt / Selection Smoke Tests

Dry-run only. Do not install, use sudo, run benchmarks, or start heavy GPU workloads.

Representative prompts:

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

Expected output:

- `skill-test-results/phase2-prompt-smoke/SUMMARY.md`
- one report per skill under `skill-test-results/phase2-prompt-smoke/`

## Phase 3 — Tooling Smoke Tests

Run only non-invasive checks unless prerequisites are already available:

1. `install-profilers`: version checks for `nsys`, `sqlite3`, `csvexport`, `tracy-capture`.
2. `diagnose-perf`: run read-only system snapshot commands.
3. `nvtx-python`: import/run a tiny Python NVTX script if `nvtx` is installed; otherwise mark blocked.
4. `profiling` / `nsys-analyze`: if `nsys` exists, capture/export a tiny Python workload; otherwise mark blocked.
5. `profiling-api`: static doc check for C++ and Python examples.
6. `tracy-memory`: check for Tracy capture tools and `liballocwrapper.so` candidates.

Expected output:

- `skill-test-results/phase3-tooling-smoke/phase3-tooling-smoke.md`
- `skill-test-results/phase3-tooling-smoke/phase3-tooling-smoke.json`

## Phase 4 — Isaac Sim Smoke Benchmark

Run only if Isaac Sim is already installed or after explicit approval to install it.

- Locate `python.sh` or Isaac Sim Python environment.
- Verify import.
- Run one tiny headless benchmark.
- Capture exact command, stdout/stderr, and KPI outputs.

## Phase 5 — Isaac Lab Smoke Benchmark

Run only if Isaac Lab is already installed or after explicit approval to install it.

- Locate `isaaclab.sh`.
- Verify import.
- Run `benchmark_non_rl.py` with tiny frame/env counts.
- Capture exact command and KPI outputs.

## Phase 6 — Real Profiling Capture

Run only after benchmark smoke tests pass.

- Capture a short Nsight Systems trace around a known smoke command.
- Export to SQLite.
- Run `nsys-analyze` queries.
- Capture Tracy only if Tracy tools are available.

## Phase 7 — Analysis + Tuning Review

Use collected artifacts to validate:

- `diagnose-perf` bottleneck category.
- `nsys-analyze` top zones/kernels/waits.
- `perf-tuning` evidence-backed fixes.
- `tracy-memory` only if memory behavior is relevant.

## Status Values

- `pass`
- `fail`
- `warning`
- `blocked_missing_prereq`
- `blocked_needs_approval`
- `not_applicable`

## Reporting

Maintain:

- `skill-test-results/SUMMARY.md`
- `skill-test-results/PR_NOTES.md`

Use `PR_NOTES.md` as the running backlog for doc fixes and follow-up PRs.
