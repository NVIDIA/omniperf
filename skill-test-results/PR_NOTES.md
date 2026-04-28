# OmniPerf Agent Skills PR Notes

Date started: 2026-04-28
Purpose: Track mistakes, doc defects, unsafe instructions, missing prerequisites, and improvement ideas discovered while testing `.agents/skills/*`.

## Fixed in This PR

### `profiling`: gate privileged Nsight Systems commands

- Severity: `safety`
- Evidence: Phase 2 defect D1
- Problem: `sudo -E nsys profile` was presented as the default. On DGX, containers, and many setups, `nsys` should be tried without sudo first.
- Fix: Use non-sudo `nsys profile` in examples and add explicit guidance to use `sudo -E` only when CPU sampling is blocked and privileged profiling is approved.

### `profiling`: replace deprecated Isaac Lab `--headless`

- Severity: `clarity`
- Evidence: Phase 2 defect D2
- Problem: Isaac Lab Nsight example used deprecated `--headless`.
- Fix: Replace with `--viz none`.

### `profiling`: document GPU metrics/container permission failure

- Severity: `clarity`
- Evidence: Phase 2 defect D3
- Problem: `--gpu-metrics-devices=all` can fail with `ERR_NVGPUCTRPERM` in containers, but the profiling command did not mention it.
- Fix: Add nearby guidance to rerun without GPU metrics or fix host/container permissions; cross-reference `install-profilers`.

### `tracy-memory`: discover `liballocwrapper.so`

- Severity: `clarity`
- Evidence: Phase 2 defect D4
- Problem: LD_PRELOAD path used a `<version>` placeholder without a discovery command.
- Fix: Add `find ~/.cache/packman -name liballocwrapper.so` based discovery and fail fast when absent.

### `tracy-memory`: normalize Tracy binary paths

- Severity: `clarity`
- Evidence: Phase 2 defect D5
- Problem: `tracy-memory` referenced `./tracy/capture` and `./tracy/update`, while `install-profilers` installs `tracy-capture` to PATH.
- Fix: Resolve `tracy-capture`/`capture` and `tracy-update`/`update` from PATH.

### `install-isaaclab`: mention uv/pip venv path

- Severity: `nice-to-have`
- Evidence: Phase 2 defect D6
- Problem: Only conda was documented.
- Fix: Clarify conda is the common path and add a short uv/pip venv alternative for versions that support it.

## Remaining Follow-Ups / Environment Blockers

These are not doc defects fixed in this PR, but they block deeper local validation on horde-dgxc-14:

- `nsys` missing.
- `sqlite3` missing.
- `csvexport` missing.
- `tracy-capture` missing.
- Python module `nvtx` missing from default Python.
- No Isaac Sim `python.sh` found in common locations.
- No Isaac Lab `isaaclab.sh` found in common locations.
- CPU governor is `schedutil`; serious benchmark numbers should use `performance`.

## Future Improvement Ideas

- Add a lightweight automated validator under `.agents/skills/tests/` if the repo wants skill docs tested in CI.
- Consider a minimal profiler setup checklist: `nsys + sqlite3` first, Tracy tools second.

---

## Phase 4 Thorough Review Findings (2026-04-28)

Review of phase4-thorough results against the TEST_PLAN. Categorized as **real doc defects** (fixed) vs **environment-only blockers** (not fixable in docs).

### Real Documentation Defects — Fixed

#### D7: `nsys-analyze` — missing explicit CUDA-kernels-empty guidance

- Severity: `clarity`
- Evidence: Phase 4 check "CUDA kernels absent behavior documented" = `warning`
- Problem: The SQLite schema table mentioned CUDA kernel table is "empty for Kit/RTX apps — normal" in a single parenthetical, but provided no actionable guidance when a user finds it empty (e.g., should they add `-t cuda` to capture flags? Is this expected for their workload type?).
- Fix: Added a prominent callout note after the schema table explaining why the table is empty for Kit/RTX (Vulkan dispatch), when it should have data (PyTorch/Warp/PhysX GPU CUDA ops), and what to check (`-t cuda` in nsys flags).

#### D8: `nvtx-python` — hardcoded developer path + sitecustomize overwrite risk

- Severity: `safety` / `clarity`
- Evidence: Phase 4 check "sitecustomize overwrite/backup guidance" = `warning`
- Problem: (a) `NVTX_SKILL_DIR` was hardcoded to `/Users/abaillet/src/omniperf/...` (developer's macOS path — wrong on any other machine). (b) No warning against copying `sitecustomize.py` into `site-packages/` where it would overwrite existing hooks (coverage.py, virtualenv, etc.).
- Fix: Replaced hardcoded path with a discoverable `$(cd ...)` pattern plus a placeholder comment. Added explicit warning not to copy into `site-packages/`. Removed hardcoded paths from Usage examples too.

#### D9: `profiling-api` — manual begin/end exception safety

- Severity: `correctness`
- Evidence: Phase 4 check "manual begin/end safety" = `warning`
- Problem: Python `carb.profiler.begin()`/`.end()` example had no `try/finally`. If `do_work()` throws, `end()` is never called, corrupting the profiler zone stack for that thread. C++ manual begin/end had a "prefer RAII" note but no exception-safety warning.
- Fix: Wrapped Python manual begin/end example in `try/finally` with explanatory text. Added exception-safety guidance to C++ manual begin/end note.

#### D10: `benchmark-isaacsim` — no discovery/gating before benchmarks

- Severity: `clarity`
- Evidence: Phase 4 check "Isaac Sim install available for --help/run" = `blocked_missing_prereq`
- Problem: The skill assumed `python.sh` or a pip-installed Isaac Sim existed with no way to discover or verify before attempting to run benchmarks.
- Fix: Added "Discover Existing Isaac Sim Installation" section with `find` and `python3 -c "import isaacsim"` commands, and a gate: "Do not proceed with benchmarks until one of these checks succeeds."

#### D11: `benchmark-isaaclab` — no discovery/gating before benchmarks

- Severity: `clarity`
- Evidence: Phase 4 check "Isaac Lab install available for --help/run" = `blocked_missing_prereq`
- Problem: Same as D10, but for Isaac Lab. No `isaaclab.sh` discovery.
- Fix: Added "Discover Existing Isaac Lab Installation" section with `find` command and gate.

#### D12: `install-isaacsim` — no check-before-install discovery

- Severity: `nice-to-have`
- Evidence: Phase 4 checks on Isaac Sim path discovery
- Problem: The skill went straight to install methods without checking if Isaac Sim was already installed.
- Fix: Added "Check for Existing Installation" section with source-build, pip, and Docker discovery commands.

#### D13: `install-isaaclab` — no check-before-install discovery

- Severity: `nice-to-have`
- Evidence: Phase 4 checks on Isaac Lab path discovery
- Problem: The skill went straight to mode selection without checking for an existing Isaac Lab.
- Fix: Added discovery commands at the top of "Choose Install Mode" section.

### Environment-Only Blockers (not doc defects)

These are purely about the test host (`horde-dgxc-14`) lacking installed software. The skills correctly document install steps for these tools; the test just couldn't validate artifact-producing paths.

- `nsys`, `sqlite3`, `csvexport`, `tracy-capture` not on PATH → blocks `profiling`, `nsys-analyze`, `tracy-memory` artifact tests
- Python `nvtx` module not installed → blocks `nvtx-python` artifact test
- No Isaac Sim / Isaac Lab installed → blocks all benchmark and profiling artifact tests
- `conda`, `uv`, `docker` not available → blocks `install-isaaclab` env-creation and `install-isaacsim` Docker path
- CPU governor is `schedutil` → warning only; correctly documented in `perf-tuning` as needing approval to change
- `perf_event_paranoid=4` → blocks CPU sampling in nsys; correctly documented in `profiling` as needing sudo or sysctl change with approval

## 2026-04-28 follow-up: missing-tool installation attempts

User asked to keep trying because skills should provide install paths for missing tools. I treated the documented setup sections as the playbook and installed/validated the missing pieces where possible.

### Installed / validated locally

- `nsys`: installed `nsight-systems-2025.6.3` from the configured CUDA apt repo; `/usr/local/bin/nsys` works.
- `sqlite3`: installed from apt; SQLite export/query smoke tests pass.
- Tracy CLI tools: built Tracy `v0.11.1` from source using the actual CMake targets for this version:
  - `/usr/local/bin/csvexport`
  - `/usr/local/bin/capture`
  - `/usr/local/bin/capture-release` symlink
  - `/usr/local/bin/tracy-capture` symlink
  - `/usr/local/bin/update`
  - `/usr/local/bin/tracy-update` symlink
- Python `nvtx`: installed in user Python; import passes and nsys NVTX smoke produced SQLite with expected `tiny_*` NVTX ranges.
- `uv`: installed in user Python; `/home/horde/.local/bin/uv` works.
- Docker CLI/daemon: installed `docker.io`; `sudo dockerd` was started manually because this environment is not booted with systemd. `docker --version` passes and `sudo docker ps` works.
- `conda`: installed local Miniconda at `/home/horde/miniconda3` and symlinked `/usr/local/bin/conda` without running `conda init`.
- Isaac Sim: installed pip Isaac Sim `4.5.0.0` with `[all,extscache]` into `/home/horde/venvs/isaacsim45`; import and `SimulationApp` import pass with `OMNI_KIT_ACCEPT_EULA=YES`.
- Isaac Lab: cloned `isaac-sim/IsaacLab` to `/home/horde/.openclaw/workspace/IsaacLab`, linked `_isaac_sim` to the Isaac Sim venv, ran `./isaaclab.sh -i none`, and verified `import isaaclab` through `./isaaclab.sh -p`.
- Phase 3 rerun: profiler/NVTX/nsys/analyze smoke tests pass; CPU sampling remains disabled due to host `perf_event_paranoid=4`.
- Phase 4 rerun: `install-profilers`, `profiling`, `nsys-analyze`, Isaac path discovery, Isaac Lab path discovery, conda, uv, Docker, NVTX, and Tracy binary checks now pass where the harness checks them.

### Remaining blockers / environment-only warnings

- Phase 4 harness now verifies Isaac Sim through the discovered isolated venv (`/home/horde/venvs/isaacsim45/python.sh`) instead of treating system Python as authoritative. System `python3` still cannot import `isaacsim`, which is expected after an isolated install.
- `liballocwrapper.so` is still not present under `~/.cache/packman` or the pip Isaac Sim install. The pip package has Tracy profiler extension binaries but not the Packman `liballocwrapper.so` expected by the memory profiling path. This remains a real prerequisite for Tracy memory captures.
- `profiling-api` still lacks a real Kit SDK build/run artifact in this host validation pass; static docs pass.
- Heavy Isaac Sim/Isaac Lab benchmarks remain approval-gated; only imports/smokes were run.
- CPU governor remains `schedutil`; serious benchmark numbers should switch to `performance` first.
- `perf_event_paranoid=4`; nsys can capture NVTX/OSRT enough for smoke tests, but CPU IP/backtrace sampling is disabled unless the sysctl is lowered.

### Documentation defects found/confirmed

- Tracy 0.11.1 source build instructions in `install-profilers` used stale `make -C capture/build/unix release` / `capture-release` paths. For this checkout, valid targets are CMake targets: `tracy-csvexport`, `tracy-capture`, and `tracy-update`; binaries are named `tracy-*` in the build dirs. The skill should document the CMake path or both variants.
- Isaac Sim pip install docs correctly need full `[all,extscache]`; bare `pip install isaacsim` installed only the metapackage and failed `SimulationApp` import.
- The install skills should emphasize activating the target venv (and `OMNI_KIT_ACCEPT_EULA=YES`) before import verification; system Python checks are misleading after isolated installs.

