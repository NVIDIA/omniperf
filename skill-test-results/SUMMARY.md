# OmniPerf Agent Skills Test Summary

Status: eval manifests migrated on 2026-04-28 UTC

Test plan: `.agents/skills/TEST_PLAN.md`
Eval cases: `.agents/skills/<skill>/evals/evals.json`

## Phase Status

- Legacy committed Phase 2/3/4 reports and harness scripts have been removed; authored evals now live beside skills.

| Phase | Status | Notes |
|---|---|---|
| Phase 0 — Static Skill Validation | pass_with_warnings | 12/12 skills valid; repo copies now match installed local skill copies. Privileged examples are flagged for review where expected. |
| Phase 1 — Host Prerequisite Snapshot | pass | Ubuntu 22.04, NVIDIA L40, driver 570.158.01, ~162G free. |
| Phase 2 — Eval Manifests | pass | Authored prompts now live in per-skill `evals/evals.json` files. |
| Phase 3 — Runtime / Tooling Checks | removed | Legacy committed smoke reports and harness scripts were removed; run new checks from external eval workspaces if needed. |
| Phase 4 — Per-Skill Thorough Tests | moved_to_evals | Thorough cases now belong in each skill's `evals/evals.json`; generated artifacts should not be committed. |
| Phase 5 — Isaac Sim Smoke Benchmark | blocked_missing_prereq | Pip Isaac Sim import works via `/home/horde/venvs/isaacsim45/python.sh`, but this pip install does not include `standalone_examples/benchmarks` scripts. |
| Phase 6 — Isaac Lab Smoke Benchmark | pass_with_warnings | Tiny Cartpole non-RL benchmark passes with 16 envs / 10 frames. Long RL/convergence runs remain approval-gated. |
| Phase 7 — Real Profiling Capture | partial | Tiny Python Nsight traces and nsys-analyze SQLite export pass. Full Kit/benchmark traces need an approved workload. |
| Phase 8 — Analysis + Tuning Review | partial | SQLite/NVTX analysis smoke passes. Real tuning review needs before/after benchmark evidence. |

## Artifacts

- Plan: `.agents/skills/TEST_PLAN.md`
- PR notes / improvement backlog: `skill-test-results/PR_NOTES.md`
- Phase 0 summary: `skill-test-results/phase0-static-validation.md`
- Phase 1 summary: `skill-test-results/phase1-host-prereqs.md`
- Eval inventory: `skill-test-results/evals-summary.md`

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

- Skill eval prompts were moved to the Anthropic/Agent Skills convention: each skill now owns `.agents/skills/<skill>/evals/evals.json`; only stable helper scripts and summary reports remain in the repo.

- `profiling`: Nsight Systems examples now try non-sudo first, gate `sudo -E`, include container-safe `--sample=none` mode, and mention container/GPU metrics permission failures.
- `tracy-memory`: LD_PRELOAD path now uses a discovery command; capture/update binaries are PATH-resolved instead of hard-coded `./tracy/...` paths; missing `liballocwrapper.so` is treated as a hard prerequisite, not a capture to fake.
- `install-isaaclab`: added a short uv/pip virtual environment alternative and clarified conda is the common path, not the only path.
- `nsys-analyze`: added explicit guidance for empty CUDA kernel tables in Kit/RTX traces.
- `nvtx-python`: removed hardcoded developer paths and warned not to overwrite `sitecustomize.py` in `site-packages`.
- `profiling-api`: made manual begin/end examples exception-safe.
- `benchmark-isaacsim` / `benchmark-isaaclab`: added install discovery gates before benchmarks; Isaac Sim now checks for source-tree benchmark scripts; Isaac Lab handles version-dependent `--headless` vs `--viz none`.
- `install-isaacsim` / `install-isaaclab`: added check-before-install and target-env verification guidance, including pip runtime vs source benchmark-script distinction; destructive cleanup/env removal is explicitly approval-gated.
- `install-profilers`: fixed Tracy 0.11.x CMake target names and robust Nsight Systems symlink discovery; privileged installs/sysctl changes are explicitly approval-gated; standalone Nsight URL is no longer hard-coded to a stale version.
- `diagnose-perf` / `perf-tuning`: triage stays read-only; host-level governor/sysctl/persistence changes are opt-in and container limitations should be recorded instead of forced.
- `profiling` / `nvtx-python`: removed stale Tracy build-path guidance, avoided Isaac Sim `--headless` ambiguity in Nsight examples, removed default `sudo prlimit`, and made NVTX helper setup copy-paste-safe.

## Remaining Blocks / Warnings

- Isaac Sim pip install lacks the source-tree `standalone_examples/benchmarks` scripts; use a source checkout or a package that includes benchmark scripts for Phase 5.
- Tracy memory capture still lacks `liballocwrapper.so` under `~/.cache/packman` / pip Isaac Sim; memory profiling remains blocked until a Packman/source Kit install provides it.
- Heavy Isaac Sim benchmark runs remain blocked until a source checkout or package with `standalone_examples/benchmarks` is available.
- Heavy Isaac Lab RL/convergence runs remain approval-gated.
- CPU governor remains `schedutil`; serious benchmark numbers should switch to `performance` first.
