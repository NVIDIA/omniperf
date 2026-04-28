# Phase 0 — Static Skill Validation

| Skill | Status | Installed copy | Issues | Warnings |
|---|---|---|---|---|
| `benchmark-isaaclab` | pass | match | - | - |
| `benchmark-isaacsim` | pass | match | - | - |
| `diagnose-perf` | pass | match | - | contains_risky_or_privileged_commands_review_required |
| `install-isaaclab` | pass | match | - | contains_risky_or_privileged_commands_review_required |
| `install-isaacsim` | pass | match | - | contains_risky_or_privileged_commands_review_required |
| `install-profilers` | pass | match | - | contains_risky_or_privileged_commands_review_required |
| `nsys-analyze` | pass | match | - | - |
| `nvtx-python` | pass | match | - | - |
| `perf-tuning` | pass | match | - | contains_risky_or_privileged_commands_review_required |
| `profiling` | pass | match | - | contains_risky_or_privileged_commands_review_required |
| `profiling-api` | pass | match | - | - |
| `tracy-memory` | pass | match | - | contains_risky_or_privileged_commands_review_required |

## Risky / privileged command matches needing review

### `diagnose-perf`
- line 47: `sudo cpupower frequency-set -g performance`

### `install-isaaclab`
- line 164: `conda env remove -n env_isaaclab`

### `install-isaacsim`
- line 64: `sudo add-apt-repository -y ppa:deadsnakes/ppa`
- line 65: `sudo apt-get update`
- line 66: `sudo apt-get install -y python3.12 python3.12-venv python3.12-dev   # adjust version to match the table`
- line 154: `sudo apt-get update && sudo apt-get install -y docker.io`
- line 154: `sudo apt-get update && sudo apt-get install -y docker.io`
- line 155: `sudo systemctl start docker && sudo systemctl enable docker`
- line 155: `sudo systemctl start docker && sudo systemctl enable docker`
- line 156: `sudo usermod -aG docker $USER`
- line 161: `# If docker ps still fails, use `sudo docker ...` for the current command`
- line 178: `sudo apt-get install -y libglu1-mesa-dev libegl1-mesa-dev libgles2-mesa-dev patchelf`
- line 226: `sudo usermod -aG docker $USER`
- line 228: `# If still fails in this shell: use `sudo docker ps` to verify Docker works,`
- line 235: `sudo apt-get install -y xvfb`
- line 66: `sudo apt-get install -y python3.12 python3.12-venv python3.12-dev   # adjust version to match the table`
- line 154: `sudo apt-get update && sudo apt-get install -y docker.io`
- line 178: `sudo apt-get install -y libglu1-mesa-dev libegl1-mesa-dev libgles2-mesa-dev patchelf`
- line 235: `sudo apt-get install -y xvfb`
- line 108: `- To completely reset: `deactivate && rm -rf ~/venvs/isaacsim ~/.cache/ov ~/.local/share/ov`.`

### `install-profilers`
- line 35: `sudo dpkg -i nsight-systems-*.deb`
- line 43: `sudo ./NsightSystems-linux-public-*.run --accept`
- line 55: `sudo apt-get update`
- line 57: `sudo apt-get install -y "$NSYS_PKG"`
- line 68: `sudo ln -sf "$NSYS_BIN" /usr/local/bin/nsys`
- line 77: `sudo dpkg -i cuda-keyring_1.1-1_all.deb`
- line 78: `sudo apt-get update`
- line 83: `sudo apt-get install -y "$NSYS_PKG"`
- line 92: `sudo apt-get install -y nsight-systems-cli`
- line 103: `sudo sh -c 'echo 2 > /proc/sys/kernel/perf_event_paranoid'`
- line 105: `sudo sh -c 'echo kernel.perf_event_paranoid=2 > /etc/sysctl.d/99-nsys.conf'`
- line 123: `sudo apt-get install -y sqlite3`
- line 170: `sudo apt-get install -y build-essential cmake git libcapstone-dev`
- line 179: `sudo cp csvexport/build/tracy-csvexport /usr/local/bin/csvexport`
- line 185: `sudo cp capture/build/tracy-capture /usr/local/bin/capture`
- line 186: `sudo ln -sf /usr/local/bin/capture /usr/local/bin/capture-release  # compatibility alias`
- line 187: `sudo ln -sf /usr/local/bin/capture /usr/local/bin/tracy-capture    # optional compatibility alias`
- line 192: `sudo cp update/build/tracy-update /usr/local/bin/update`
- line 193: `sudo ln -sf /usr/local/bin/update /usr/local/bin/tracy-update  # optional compatibility alias`
- line 214: `sudo apt-get install -y tracy-csvexport tracy-capture`
- ... 6 more

### `perf-tuning`
- line 180: `echo performance \| sudo tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor`

### `profiling`
- line 217: `sudo dpkg -i nsight-systems-*.deb`
- line 236: `Try without `sudo` first. Use `sudo -E` only when `perf_event_paranoid` blocks CPU sampling or system-wide OS runtime data, and only after confirming it is acceptable for the machine. In containers, `sudo` may not exist and GPU metrics may `
- line 236: `Try without `sudo` first. Use `sudo -E` only when `perf_event_paranoid` blocks CPU sampling or system-wide OS runtime data, and only after confirming it is acceptable for the machine. In containers, `sudo` may not exist and GPU metrics may `
- line 236: `Try without `sudo` first. Use `sudo -E` only when `perf_event_paranoid` blocks CPU sampling or system-wide OS runtime data, and only after confirming it is acceptable for the machine. In containers, `sudo` may not exist and GPU metrics may `
- line 294: `sudo prlimit --nofile=65536:65536 /bin/bash -c \`
- line 330: `Use `sudo -E` only if the non-sudo command fails because CPU sampling is blocked and you have approval to run privileged profiling.`
- line 330: `Use `sudo -E` only if the non-sudo command fails because CPU sampling is blocked and you have approval to run privileged profiling.`

### `tracy-memory`
- line 3: `description: Profile CPU and GPU memory allocations using Tracy in Kit-based applications after Tracy capture tooling is installed. Covers LD_PRELOAD setup for liballocwrapper.so, Kit memory-channel flags, capture binary isolation (unset LD`
- line 3: `description: Profile CPU and GPU memory allocations using Tracy in Kit-based applications after Tracy capture tooling is installed. Covers LD_PRELOAD setup for liballocwrapper.so, Kit memory-channel flags, capture binary isolation (unset LD`
- line 13: `The `omni.cpumemorytracking` extension uses LD_PRELOAD to intercept malloc/free. Without it, Kit logs `Failed to load library: 'liballocwrapper.so'` and **zero memory events are captured**.`
- line 20: `export LD_PRELOAD="$ALLOC_WRAPPER"`
- line 49: `## Step 3: Unset LD_PRELOAD Before Capture Binary`
- line 54: `# After launching Kit with LD_PRELOAD in background`
- line 55: `unset LD_PRELOAD`
- line 73: `# Broken: 18 MB → 18 MB (zero memory data — LD_PRELOAD failed)`
- line 84: `If you see `Failed to load library: 'liballocwrapper.so'` → LD_PRELOAD path is wrong. Stop and fix before re-running.`
- line 93: `If Memory tab is empty: recheck LD_PRELOAD path and `cpu.memory` channel setting.`
- line 107: `- Missing `LD_PRELOAD=liballocwrapper.so` → extension starts but hooks never install`
- line 110: `- LD_PRELOAD bleeding into capture binary → corrupt capture`

