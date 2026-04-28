# OmniPerf Agent Skills Test Plan

Validate that OmniPerf AgentSkills are discoverable, safe to invoke, and useful in the Isaac Sim / Isaac Lab / Kit performance workflow.

This plan is layered: static/doc checks first, then dry-run prompt tests, then non-invasive host checks, then real artifact-producing tests only when prerequisites exist or the user explicitly approves installs/privileged commands.

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

- `skill-test-results/phase0-static-validation.md`
- `skill-test-results/phase0-static-validation.json`

## Phase 1 — Host Prerequisite Snapshot

Use non-mutating checks only:

- OS/kernel.
- NVIDIA driver/GPU via `nvidia-smi`.
- Python, pip, conda, uv.
- `nsys`, `sqlite3`, `csvexport`, `tracy-capture`, Tracy `update`.
- Existing Isaac Sim / Isaac Lab paths.
- Disk space.
- CPU governor.
- CUDA/PyTorch availability if a Python env exists.

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

1. `install-profilers`: version checks for `nsys`, `sqlite3`, `csvexport`, `tracy-capture`, Tracy `update`.
2. `diagnose-perf`: run read-only system snapshot commands.
3. `nvtx-python`: import/run a tiny Python NVTX script if `nvtx` is installed; otherwise mark blocked.
4. `profiling` / `nsys-analyze`: if `nsys` exists, capture/export a tiny Python workload; otherwise mark blocked.
5. `profiling-api`: static doc check for C++ and Python examples.
6. `tracy-memory`: check for Tracy capture tools and `liballocwrapper.so` candidates.

Expected output:

- `skill-test-results/phase3-tooling-smoke/phase3-tooling-smoke.md`
- `skill-test-results/phase3-tooling-smoke/phase3-tooling-smoke.json`

## Phase 4 — Per-Skill Thorough Tests

Each skill gets a dedicated checklist with positive, negative, safety, and artifact checks. Store results under `skill-test-results/phase4-thorough/<skill>.md` and a summary table at `skill-test-results/phase4-thorough/SUMMARY.md`.

### `install-profilers`

Safe tests:

- Run the quick-check commands for `nsys`, `sqlite3`, `csvexport`, `tracy-capture`, and Tracy `update`.
- Check whether CUDA apt repo exists without installing anything.
- Check whether `/opt/nvidia/nsight-systems` exists.
- Check whether PATH contains duplicate/conflicting Tracy binaries.
- Validate the skill says to install only missing pieces.

Artifact tests when tools exist:

- `nsys --version` returns a version.
- `sqlite3 --version` returns a version.
- `csvexport --help` works.
- `tracy-capture --help` or equivalent works.

Blocked tests needing approval:

- `apt-get install`, `.run` installers, `sudo ln -sf`, sysctl/perf changes.

### `install-isaacsim`

Safe tests:

- Validate Python version matrix against current host Python versions.
- Search common locations for Isaac Sim installs: `/home`, `/opt`, `/data`, workspace.
- Check for pip-installed `isaacsim` in active Python without installing.
- Validate pip/source/Docker paths are mutually clear.
- Check Docker availability without starting containers.
- Confirm commands gate `sudo`, Docker group changes, and cleanup.

Artifact tests when install exists:

- Locate `python.sh` or env Python.
- Run import check: `import isaacsim` or version-specific equivalent.
- Run `./python.sh -c 'print("OK")'` if present.

Blocked tests needing approval:

- New Isaac Sim install, Docker install, package installs, cache cleanup.

### `install-isaaclab`

Safe tests:

- Search for `isaaclab.sh`.
- Check conda/uv availability.
- Validate full Isaac Sim-backed vs kit-less/Newton mode selection.
- Check `_isaac_sim` symlink if Isaac Lab is found.
- Verify activation commands are shell-safe and avoid mutating shell startup files.

Artifact tests when install exists:

- Run `./isaaclab.sh -p -c "import isaaclab; print('OK')"`.
- Run `./isaaclab.sh --help` or benchmark script `--help`.

Blocked tests needing approval:

- Cloning/building Isaac Lab, creating/removing conda/uv envs, dependency installs.

### `benchmark-isaacsim`

Safe tests:

- Inspect benchmark scripts listed in the skill if Isaac Sim source/install exists.
- Run `--help` for benchmark scripts if `python.sh` exists.
- Validate tiny benchmark command uses minimal frames/assets and headless-safe args.
- Confirm KPI/output path is explicit.

Artifact tests when install exists:

- Run one tiny camera or scene-loading benchmark with minimal frames.
- Capture command, stdout/stderr, exit code, KPI JSON/log paths.

Blocked tests needing approval:

- Heavy benchmark sweeps, long runs, Nucleus asset pulls that require credentials.

### `benchmark-isaaclab`

Safe tests:

- Inspect `scripts/benchmarks/` if Isaac Lab exists.
- Run `benchmark_non_rl.py --help` if possible.
- Validate `--viz none` / headless guidance.
- Validate tiny `--num_frames` / `--num_envs` smoke command.

Artifact tests when install exists:

- Run `benchmark_non_rl.py` with tiny frame/env counts.
- Capture throughput/KPI/log output.

Blocked tests needing approval:

- Long RL training/convergence tests, large env counts.

### `profiling`

Safe tests:

- Check `nsys` availability.
- Check `perf_event_paranoid` read-only.
- Validate non-sudo default and `sudo -E` gating.
- Validate GPU metrics fallback guidance.
- Validate Tracy port/capture sequencing instructions.

Artifact tests when tools exist:

- Run `nsys profile` around a tiny Python script.
- Export `.nsys-rep` to SQLite if exporter exists.
- If Tracy tools and Kit app exist, run a short Tracy capture.

Blocked tests needing approval:

- `sudo nsys`, sysctl changes, long profiling captures.

### `nsys-analyze`

Safe tests:

- If a SQLite export exists, list tables and validate expected schema fallbacks.
- Validate SQL handles `NVTX_EVENTS.text` vs `textId/StringIds`.
- Validate behavior when CUDA kernel tables are absent.
- Validate comparison workflow with synthetic or existing SQLite if available.

Artifact tests when trace exists:

- Produce top NVTX zone table.
- Produce phase summary.
- Produce warning if only RTX/NVTX data exists and CUDA kernel table is empty.

Blocked tests needing prereq:

- Requires `.nsys-rep`/SQLite or `nsys` to create one.

### `nvtx-python`

Safe tests:

- Check import of Python `nvtx` in active Python/env.
- Create a temporary isolated test dir with a tiny NVTX-decorated function.
- Validate `sitecustomize.py` instructions avoid overwriting existing files without backup.
- Validate include/exclude filters are documented.

Artifact tests when `nvtx` + `nsys` exist:

- Capture tiny NVTX Python workload.
- Verify NVTX range appears in exported SQLite.

Blocked tests needing approval:

- Installing `nvtx` into global/default env.

### `profiling-api`

Safe tests:

- Static-check C++ examples include required headers and mask/channel use.
- Static-check Python examples import/use Carbonite profiler APIs correctly.
- Validate begin/end examples use `try/finally` or scoped patterns.
- Validate metrics/plot/event annotations mention profiler masks/channels.

Artifact tests when Kit SDK/source exists:

- Compile or run minimal extension/sample using profiling zones.
- Capture trace and verify custom zones appear.

Blocked tests needing prereq:

- Requires Kit SDK or a buildable Kit extension context.

### `tracy-memory`

Safe tests:

- Discover `liballocwrapper.so` without exporting it globally.
- Check Tracy capture/update binaries.
- Validate instructions unset `LD_PRELOAD` before capture binary.
- Validate strip-test command and failure interpretation.

Artifact tests when Kit + Tracy tools exist:

- Run short Kit/Isaac workload with memory channels enabled.
- Capture `.tracy`.
- Run strip test and compare file sizes.

Blocked tests needing approval/prereq:

- Real memory capture requires Kit app + Tracy tools; LD_PRELOAD applies only to launched workload.

### `diagnose-perf`

Safe tests:

- Run read-only GPU/CPU/memory/thermal/governor snapshot.
- Classify idle GPU correctly as not a workload bottleneck.
- Validate red-flag logic for P-state, throttling, VRAM pressure, CPU governor.
- If no Isaac process is running, verify it says workload-specific conclusions are unavailable.

Artifact tests when workload exists:

- Sample `nvidia-smi dmon`/process utilization briefly.
- Produce bottleneck hypothesis with confidence level.

Blocked tests needing approval:

- CPU governor changes or persistence-mode changes.

### `perf-tuning`

Safe tests:

- Feed synthetic evidence cases and check recommendations:
  - PresentFrame + GPU saturation.
  - Hydra waitIdle / CPU bottleneck.
  - resolveSamplerFeedback slow path.
  - fsWatcher overhead.
  - CPU governor not performance.
- Validate every fix has a measurement/rollback plan.
- Validate it does not recommend tuning without evidence.

Artifact tests when workload exists:

- Apply one low-risk runtime flag only with approval.
- Re-measure before/after KPI.

Blocked tests needing approval:

- System settings, persistent config changes, benchmark reruns at scale.

## Phase 5 — Isaac Sim Smoke Benchmark

Run only if Isaac Sim is already installed or after explicit approval to install it.

- Locate `python.sh` or Isaac Sim Python environment.
- Verify import.
- Run one tiny headless benchmark.
- Capture exact command, stdout/stderr, and KPI outputs.

## Phase 6 — Isaac Lab Smoke Benchmark

Run only if Isaac Lab is already installed or after explicit approval to install it.

- Locate `isaaclab.sh`.
- Verify import.
- Run `benchmark_non_rl.py` with tiny frame/env counts.
- Capture exact command and KPI outputs.

## Phase 7 — Real Profiling Capture

Run only after benchmark smoke tests pass.

- Capture a short Nsight Systems trace around a known smoke command.
- Export to SQLite.
- Run `nsys-analyze` queries.
- Capture Tracy only if Tracy tools are available.

## Phase 8 — Analysis + Tuning Review

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
- `skill-test-results/phase4-thorough/SUMMARY.md`

Use `PR_NOTES.md` as the running backlog for doc fixes and follow-up PRs.
