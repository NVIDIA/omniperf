# OmniPerf Agent Skills Test Summary

Status: completed through Phase 4 on 2026-04-28 UTC

Test plan: `.agents/skills/TEST_PLAN.md`

## Phase Status

| Phase | Status | Notes |
|---|---|---|
| Phase 0 — Static Skill Validation | pass_with_warnings | 12/12 skills valid; repo copies now match installed local skill copies. Privileged examples are flagged for review where expected. |
| Phase 1 — Host Prerequisite Snapshot | pass | Ubuntu 22.04, NVIDIA L40, driver 570.158.01, ~162G free. |
| Phase 2 — Prompt / Selection Smoke Tests | pass_with_warnings | 10 pass, 2 warnings, 0 fail before fixes. Warnings were converted into doc patches. |
| Phase 3 — Tooling Smoke Tests | pass_with_warnings | `nsys`, `sqlite3`, Tracy `csvexport`/`capture`, and Python `nvtx` now work. CPU IP/backtrace sampling still blocked by `perf_event_paranoid=4`. |
| Phase 4 — Per-Skill Thorough Tests | pass_with_expected_blocks | Install/profiling/nsys/nvtx/profiling-api/diagnose checks pass. Isaac Lab tiny benchmark passes; Isaac Sim standalone scripts and Tracy allocator wrapper are still unavailable. Real tuning before/after evidence remains approval-gated. |
| Phase 5 — Isaac Sim Smoke Benchmark | blocked_missing_prereq | Pip Isaac Sim import works via `/home/horde/venvs/isaacsim45/python.sh`, but this pip install does not include `standalone_examples/benchmarks` scripts. |
| Phase 6 — Isaac Lab Smoke Benchmark | pass_with_warnings | Tiny Cartpole non-RL benchmark passes with 16 envs / 10 frames. Long RL/convergence runs remain approval-gated. |
| Phase 7 — Real Profiling Capture | partial | Tiny Python Nsight traces and nsys-analyze SQLite export pass. Full Kit/benchmark traces need an approved workload. |
| Phase 8 — Analysis + Tuning Review | partial | SQLite/NVTX analysis smoke passes. Real tuning review needs before/after benchmark evidence. |

## Artifacts

- Plan: `.agents/skills/TEST_PLAN.md`
- PR notes / improvement backlog: `skill-test-results/PR_NOTES.md`
- Phase 0 summary: `skill-test-results/phase0-static-validation.md`
- Phase 1 summary: `skill-test-results/phase1-host-prereqs.md`
- Phase 2 summary: `skill-test-results/phase2-prompt-smoke/SUMMARY.md`
- Phase 3 summary: `skill-test-results/phase3-tooling-smoke/phase3-tooling-smoke.md`
- Phase 4 summary: `skill-test-results/phase4-thorough/SUMMARY.md`

## Host Facts

- OS: Ubuntu 22.04.5 LTS
- Kernel: 5.15.0-113-generic
- GPU: NVIDIA L40, 49140 MiB
- Driver: 570.158.01
- CUDA reported by driver: 12.8
- CPU: dual-socket Intel Xeon Platinum 8362, 64 physical cores / 128 threads
- RAM: ~1 TiB
- Workspace disk: ~162G available
- CPU governor: `schedutil` — benchmark numbers should be marked exploratory until set to `performance`.
- `perf_event_paranoid=4` — Nsight Systems CPU IP/backtrace sampling is disabled unless lowered with approval.

## Tooling Installed / Validated

- `nsys`: `/usr/local/bin/nsys`, Nsight Systems 2025.6.3
- `sqlite3`: installed and usable for Nsight SQLite exports
- Tracy CLI tools: `csvexport`, `capture`, `capture-release`, `tracy-capture`, `update`, `tracy-update`
- Python `nvtx`: import passes; tiny NVTX capture/export produced expected SQLite ranges
- `uv`, `conda`, Docker CLI/daemon: available
- Isaac Sim: pip Isaac Sim 4.5.0 venv at `/home/horde/venvs/isaacsim45`; `SimulationApp` import passes with EULA env
- Isaac Lab: `/home/horde/.openclaw/workspace/IsaacLab`; `./isaaclab.sh -p -c "import isaaclab"` passes

## Findings Fixed in This PR

- `profiling`: Nsight Systems examples now try non-sudo first, gate `sudo -E`, include container-safe `--sample=none` mode, and mention container/GPU metrics permission failures.
- `tracy-memory`: LD_PRELOAD path now uses a discovery command; capture/update binaries are PATH-resolved instead of hard-coded `./tracy/...` paths; missing `liballocwrapper.so` is treated as a hard prerequisite, not a capture to fake.
- `install-isaaclab`: added a short uv/pip virtual environment alternative and clarified conda is the common path, not the only path.
- `nsys-analyze`: added explicit guidance for empty CUDA kernel tables in Kit/RTX traces.
- `nvtx-python`: removed hardcoded developer paths and warned not to overwrite `sitecustomize.py` in `site-packages`.
- `profiling-api`: made manual begin/end examples exception-safe.
- `benchmark-isaacsim` / `benchmark-isaaclab`: added install discovery gates before benchmarks; Isaac Sim now checks for source-tree benchmark scripts; Isaac Lab handles version-dependent `--headless` vs `--viz none`.
- `install-isaacsim` / `install-isaaclab`: added check-before-install and target-env verification guidance, including pip runtime vs source benchmark-script distinction; destructive cleanup/env removal is explicitly approval-gated.
- `install-profilers`: fixed Tracy 0.11.x CMake target names and robust Nsight Systems symlink discovery; privileged installs/sysctl changes are explicitly approval-gated.
- `diagnose-perf` / `perf-tuning`: triage stays read-only; host-level governor/sysctl/persistence changes are opt-in and container limitations should be recorded instead of forced.

## Remaining Blocks / Warnings

- Isaac Sim pip install lacks the source-tree `standalone_examples/benchmarks` scripts; use a source checkout or a package that includes benchmark scripts for Phase 5.
- Tracy memory capture still lacks `liballocwrapper.so` under `~/.cache/packman` / pip Isaac Sim; memory profiling remains blocked until a Packman/source Kit install provides it.
- Heavy Isaac Sim benchmark runs remain blocked until a source checkout or package with `standalone_examples/benchmarks` is available.
- Heavy Isaac Lab RL/convergence runs remain approval-gated.
- CPU governor remains `schedutil`; serious benchmark numbers should switch to `performance` first.
