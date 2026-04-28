# Phase 0 — Static Skill Validation

| Skill | Status | Installed copy | Evals | Issues | Warnings |
|---|---|---|---|---|---|
| `benchmark-isaaclab` | pass | match | present | - | - |
| `benchmark-isaacsim` | pass | match | present | - | - |
| `diagnose-perf` | pass | match | present | - | contains_risky_or_privileged_commands_review_required |
| `install-isaaclab` | pass | match | present | - | contains_risky_or_privileged_commands_review_required |
| `install-isaacsim` | pass | match | present | - | contains_risky_or_privileged_commands_review_required |
| `install-profilers` | pass | match | present | - | contains_risky_or_privileged_commands_review_required |
| `nsys-analyze` | pass | match | present | - | - |
| `nvtx-python` | pass | match | present | - | - |
| `perf-tuning` | pass | match | present | - | contains_risky_or_privileged_commands_review_required |
| `profiling` | pass | match | present | - | contains_risky_or_privileged_commands_review_required |
| `profiling-api` | pass | match | present | - | - |
| `tracy-memory` | pass | match | present | - | contains_risky_or_privileged_commands_review_required |

## Risky / privileged command matches needing review

### `diagnose-perf`
- line 47: `sudo cpupower frequency-set -g performance`

### `install-isaaclab`
- line 170: `conda env remove -n env_isaaclab`

### `install-isaacsim`
- line 30: `**Safety gates:** `sudo apt-get`, Docker service/group changes, and cleanup commands such as `rm -rf` mutate the host. Check/discover first, then ask/obtain approval before running those examples. Prefer creating a new venv over deleting an`
- line 66: `sudo add-apt-repository -y ppa:deadsnakes/ppa`
- line 67: `sudo apt-get update`
- line 68: `sudo apt-get install -y python3.12 python3.12-venv python3.12-dev   # adjust version to match the table`
- line 158: `sudo apt-get update && sudo apt-get install -y docker.io`
- line 158: `sudo apt-get update && sudo apt-get install -y docker.io`
- line 159: `sudo systemctl start docker && sudo systemctl enable docker`
- line 159: `sudo systemctl start docker && sudo systemctl enable docker`
- line 160: `sudo usermod -aG docker $USER`
- line 165: `# If docker ps still fails, use `sudo docker ...` for the current command`
- line 182: `sudo apt-get install -y libglu1-mesa-dev libegl1-mesa-dev libgles2-mesa-dev patchelf`
- line 230: `sudo usermod -aG docker $USER`
- line 232: `# If still fails in this shell: use `sudo docker ps` to verify Docker works,`
- line 239: `sudo apt-get install -y xvfb`
- line 68: `sudo apt-get install -y python3.12 python3.12-venv python3.12-dev   # adjust version to match the table`
- line 158: `sudo apt-get update && sudo apt-get install -y docker.io`
- line 182: `sudo apt-get install -y libglu1-mesa-dev libegl1-mesa-dev libgles2-mesa-dev patchelf`
- line 239: `sudo apt-get install -y xvfb`
- line 30: `**Safety gates:** `sudo apt-get`, Docker service/group changes, and cleanup commands such as `rm -rf` mutate the host. Check/discover first, then ask/obtain approval before running those examples. Prefer creating a new venv over deleting an`
- line 110: `- To completely reset, only after explicit approval: `deactivate && rm -rf ~/venvs/isaacsim ~/.cache/ov ~/.local/share/ov`.`

### `install-profilers`
- line 22: `**Approval gates:** Commands that install packages, write `/usr/local/bin`, change `/proc/sys/kernel/perf_event_paranoid`, or create system symlinks are host mutations. Check first, then ask/obtain approval before running the `sudo` example`
- line 38: `sudo dpkg -i nsight-systems.deb`
- line 46: `sudo ./NsightSystems-linux-public-*.run --accept`
- line 58: `sudo apt-get update`
- line 60: `sudo apt-get install -y "$NSYS_PKG"`
- line 71: `sudo ln -sf "$NSYS_BIN" /usr/local/bin/nsys`
- line 80: `sudo dpkg -i cuda-keyring_1.1-1_all.deb`
- line 81: `sudo apt-get update`
- line 86: `sudo apt-get install -y "$NSYS_PKG"`
- line 95: `sudo apt-get install -y nsight-systems-cli`
- line 107: `sudo sh -c 'echo 2 > /proc/sys/kernel/perf_event_paranoid'`
- line 110: `sudo sh -c 'echo kernel.perf_event_paranoid=2 > /etc/sysctl.d/99-nsys.conf'`
- line 128: `sudo apt-get install -y sqlite3`
- line 175: `sudo apt-get install -y build-essential cmake git libcapstone-dev`
- line 184: `sudo cp csvexport/build/tracy-csvexport /usr/local/bin/csvexport`
- line 190: `sudo cp capture/build/tracy-capture /usr/local/bin/capture`
- line 191: `sudo ln -sf /usr/local/bin/capture /usr/local/bin/capture-release  # compatibility alias`
- line 192: `sudo ln -sf /usr/local/bin/capture /usr/local/bin/tracy-capture    # optional compatibility alias`
- line 197: `sudo cp update/build/tracy-update /usr/local/bin/update`
- line 198: `sudo ln -sf /usr/local/bin/update /usr/local/bin/tracy-update  # optional compatibility alias`
- ... 7 more

### `perf-tuning`
- line 11: `**Approval gates:** Benchmark/app CLI flags are fine to test in a new run. Host-level changes (`sudo`, CPU governor, sysctl, persistence mode, package installs) require approval and may be unavailable in containers. If a container cannot ch`
- line 185: `echo performance \| sudo tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor`

### `profiling`
- line 217: `sudo dpkg -i nsight-systems-*.deb`
- line 236: `Try without `sudo` first. Use `sudo -E` only when `perf_event_paranoid` blocks CPU sampling or system-wide OS runtime data, and only after confirming it is acceptable for the machine. In containers, `sudo` may not exist and GPU metrics may `
- line 236: `Try without `sudo` first. Use `sudo -E` only when `perf_event_paranoid` blocks CPU sampling or system-wide OS runtime data, and only after confirming it is acceptable for the machine. In containers, `sudo` may not exist and GPU metrics may `
- line 236: `Try without `sudo` first. Use `sudo -E` only when `perf_event_paranoid` blocks CPU sampling or system-wide OS runtime data, and only after confirming it is acceptable for the machine. In containers, `sudo` may not exist and GPU metrics may `
- line 354: `# Raise the soft file-descriptor limit without sudo when the shell allows it.`
- line 376: `# the same command with `sudo -E nsys profile ...`; do not use sudo by default.`
- line 376: `# the same command with `sudo -E nsys profile ...`; do not use sudo by default.`
- line 390: `For host-only CPU sampling/GPU metrics, add `--sample=system-wide --gpu-metrics-devices=all --gpuctxsw=true` only when the host allows it. Use `sudo -E` only if the non-sudo command fails because CPU sampling is blocked and you have approva`
- line 390: `For host-only CPU sampling/GPU metrics, add `--sample=system-wide --gpu-metrics-devices=all --gpuctxsw=true` only when the host allows it. Use `sudo -E` only if the non-sudo command fails because CPU sampling is blocked and you have approva`

### `tracy-memory`
- line 3: `description: Profile CPU and GPU memory allocations using Tracy in Kit-based applications after Tracy capture tooling is installed. Covers LD_PRELOAD setup for liballocwrapper.so, Kit memory-channel flags, capture binary isolation (unset LD`
- line 3: `description: Profile CPU and GPU memory allocations using Tracy in Kit-based applications after Tracy capture tooling is installed. Covers LD_PRELOAD setup for liballocwrapper.so, Kit memory-channel flags, capture binary isolation (unset LD`
- line 13: `The `omni.cpumemorytracking` extension uses LD_PRELOAD to intercept malloc/free. Without it, Kit logs `Failed to load library: 'liballocwrapper.so'` and **zero memory events are captured**. Pip Isaac Sim installs may not ship this Packman/s`
- line 23: `export LD_PRELOAD="$ALLOC_WRAPPER"`
- line 52: `## Step 3: Unset LD_PRELOAD Before Capture Binary`
- line 57: `# After launching Kit with LD_PRELOAD in background`
- line 58: `unset LD_PRELOAD`
- line 76: `# Broken: 18 MB → 18 MB (zero memory data — LD_PRELOAD failed)`
- line 87: `If you see `Failed to load library: 'liballocwrapper.so'` → LD_PRELOAD path is wrong. Stop and fix before re-running.`
- line 96: `If Memory tab is empty: recheck LD_PRELOAD path and `cpu.memory` channel setting.`
- line 110: `- Missing `LD_PRELOAD=liballocwrapper.so` → extension starts but hooks never install`
- line 113: `- LD_PRELOAD bleeding into capture binary → corrupt capture`

