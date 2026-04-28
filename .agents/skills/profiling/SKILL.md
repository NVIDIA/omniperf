---
name: profiling
description: Capture performance traces using CPU ChromeTrace, Tracy, and Nsight Systems/NVTX for Kit-based applications (Isaac Sim, Isaac Lab, Kit SDK). Covers COLD/WARM/TRACY measurement separation, canonical Tracy capture sequence, last-resort force-kill handling, nsys profile commands, Kit profiler args, and lightweight export handoff to nsys-analyze. Use when running profiling captures, setting up trace collection, or troubleshooting capture failures. NOT for adding profiling zones (use profiling-api), deep trace analysis (use nsys-analyze), memory allocation profiling (use tracy-memory), or applying performance fixes (use perf-tuning).
---

# Profiling Guide

This is the agent-facing profiling workflow for Kit-based applications (Isaac Sim, Isaac Lab, Kit SDK).
`dev/docs/profiling-guide.md` is the source of truth; keep this skill aligned with that guide.

## Benchmark Accuracy: COLD / WARM / TRACY

Profilers add overhead. Keep measurement and diagnosis as separate runs:

1. **COLD:** first run after a fresh install/cache state. Use this to expose startup and shader-cache effects, not as the steady-state performance number.
2. **WARM:** same workload with caches already populated and profiling disabled. This is the authoritative FPS/frametime benchmark run.
3. **TRACY:** same cache state as WARM, Tracy backend enabled, `CARB_PROFILING_PYTHON=1` set, and `.tracy` captured via a separate capture process. Use this for analysis only, not headline numbers.

Never report benchmark performance from a profiled run. Nsight Systems captures are also analysis-only and have their own overhead.

## CPU ChromeTrace Backend

Use the CPU backend for short, shareable, offline captures or targeted runtime intervals.

### Kit Args
```bash
--/app/profilerBackend=cpu
--/app/profileFromStart=true
--/profiler/enabled=true
--/plugins/carb.profiler-cpu.plugin/saveProfile=1
--/plugins/carb.profiler-cpu.plugin/compressProfile=1
--/plugins/carb.profiler-cpu.plugin/filePath=mytrace.gz
```

### Runtime On/Off
```python
import carb.profiler

profiler = carb.profiler.acquire_profiler_interface()
profiler.set_capture_mask(1)  # start targeted capture
# ... section to profile ...
profiler.set_capture_mask(0)  # stop targeted capture
```

### Convert Chrome Trace JSON to Tracy
```bash
# From the Tracy binary directory
./import-chrome input_trace.json output.tracy
```

## Tracy Profiling

### Environment Setup
```bash
export TRACY_NO_SYS_TRACE=1
export TRACY_NO_CALLSTACK=1

# TRACY analysis phase only. Do not set during COLD/WARM benchmark measurement.
export CARB_PROFILING_PYTHON=1
```

### Kit Args (common for all Kit-based products)
```
--/app/profilerBackend=tracy
--/app/profileFromStart=true
--/profiler/enabled=true
--/profiler/gpu=true
--/profiler/gpu/tracyInject/enabled=true
--/app/profilerMask=1
--/plugins/carb.profiler-tracy.plugin/fibersAsThreads=false
--/profiler/channels/carb.events/enabled=false
--/profiler/channels/carb.tasking/enabled=false
--/profiler/gpu/tracyInject/msBetweenClockCalibration=0
--/rtx/addTileGpuAnnotations=true
--/plugins/carb.profiler-tracy.plugin/instantEventsAsMessages=true
```

### Tracy Capture — Correct Procedure (IMPORTANT)

Tracy capture is error-prone. Follow this exact sequence to avoid port conflicts and data loss.

**Tracy port:** default is `8086`; Isaac Sim 6.0+ commonly uses `8087` to avoid OV Hub. Kit auto-increments to `8087`, `8088`, etc. on conflict. Set `TRACY_PORT` when you know the port.

**Tracy capture binary:** use the bundled `omni.kit.profiler.tracy` capture binary when available, or build Tracy 0.11.1 from source and resolve `capture` / `capture-release` / `tracy-capture` from PATH. See `install-profilers`; do not hard-code stale Tracy build paths.

#### Step-by-step:
```bash
# 1. Kill any existing Tracy-related processes hogging the port
pkill -9 -f "capture" 2>/dev/null || true
export TRACY_PORT="${TRACY_PORT:-8086}"  # use 8087 for Isaac Sim 6.0+ when needed
ss -tlnp | grep ":$TRACY_PORT" || true  # verify the intended port is free

BENCH_SCRIPT="standalone_examples/benchmarks/benchmark_camera.py"
RESULT_DIR="/tmp/isaacsim-profile-results"

TRACY_CAPTURE_BIN="${TRACY_CAPTURE_BIN:-}"
if [ -z "$TRACY_CAPTURE_BIN" ]; then
  TRACY_CAPTURE_BIN=$(command -v capture || command -v capture-release || command -v tracy-capture)
fi
[ -n "$TRACY_CAPTURE_BIN" ] || { echo "Missing Tracy capture binary"; exit 1; }

# 2. Start the application FIRST (in background)
nohup ./python.sh "$BENCH_SCRIPT" \
  --num-cameras 1 --num-frames 600 \
  --/app/profilerBackend=tracy --/app/profileFromStart=true \
  --/profiler/enabled=true --/profiler/gpu=true \
  --/profiler/gpu/tracyInject/enabled=true --/app/profilerMask=1 \
  --/plugins/carb.profiler-tracy.plugin/fibersAsThreads=false \
  --/profiler/channels/carb.events/enabled=false \
  --/profiler/channels/carb.tasking/enabled=false \
  --/profiler/gpu/tracyInject/msBetweenClockCalibration=0 \
  --/rtx/addTileGpuAnnotations=true \
  --/plugins/carb.profiler-tracy.plugin/instantEventsAsMessages=true \
  --/exts/isaacsim.benchmark.services/metrics/metrics_output_folder="$RESULT_DIR" \
  > /tmp/app.log 2>&1 &
APP_PID=$!

# 3. Poll until Tracy port is open (app needs time to initialize)
for i in $(seq 1 60); do
  ss -tlnp | grep -q ":$TRACY_PORT" && break
  sleep 2
done

# 4. Start capture AFTER port is confirmed open
"$TRACY_CAPTURE_BIN" -o trace_output.tracy -f -p "$TRACY_PORT" &
CAPTURE_PID=$!

# 5. Wait for benchmark result files, not graceful Isaac Sim shutdown
until ls "$RESULT_DIR"/kpis_*.json >/dev/null 2>&1; do sleep 5; done

# 6. Isaac Sim can hang during Tracy shutdown. Force-kill after outputs exist.
kill -9 "$APP_PID" "$CAPTURE_PID" 2>/dev/null || true
```

#### Critical warnings:
- **Prefer app first, then capture.** Starting capture before the app can work, but app-first plus port verification is the most reliable sequence.
- **NEVER kill capture with kill/SIGTERM.** It will NOT save the trace file.
- **Always check for zombie processes** on the intended Tracy port before starting.
- **Do not wait for Isaac Sim graceful shutdown** after benchmark outputs exist; Tracy shutdown can hang. Use `kill -9` as the guide-prescribed last resort.

### Last Resort: Scoped `os._exit(0)` Close Patch

Do **not** patch installed Isaac Sim files by default. Normal shutdown is preferred because it runs cleanup code and keeps the install reproducible.

Use this workaround only when all of the following are true:
- The workload repeatedly hangs during Tracy shutdown.
- Expected benchmark and trace outputs already exist with non-zero size.
- The install is disposable or you can restore the original file immediately after capture.

Prefer first to use the force-kill sequence above after results are complete. Patch only when repeated hangs prevent usable capture completion.

```bash
# Find simulation_app.py — path varies between source and build layouts:
#   Source build: source/extensions/isaacsim.simulation_app/isaacsim/simulation_app/simulation_app.py
#   Build output: _build/linux-x86_64/release/exts/isaacsim.simulation_app/isaacsim/simulation_app/simulation_app.py
# NOTE: `find -path` may fail in some environments (dots in dir names). Use glob instead:
shopt -s globstar nullglob
PACKAGE_PATH="/path/to/IsaacSim-or-pip-package"
SIM_APP=$(echo "$PACKAGE_PATH"/**/isaacsim/simulation_app/simulation_app.py | tr ' ' '\n' | grep -v __pycache__ | head -1)
# Or explicit known paths:
# SIM_APP="$PACKAGE_PATH"/_build/linux-x86_64/release/exts/isaacsim.simulation_app/isaacsim/simulation_app/simulation_app.py
echo "Found: $SIM_APP"

# Idempotent patch with a restore point.
cp -n "$SIM_APP" "$SIM_APP.bak.codex-tracy-close"
python3 - "$SIM_APP" <<'PY'
from pathlib import Path
import re, sys

path = Path(sys.argv[1])
text = path.read_text()
marker = "CODEX_TRACY_CLOSE_BYPASS"
if marker in text:
    print(f"Already patched: {path}")
    raise SystemExit(0)

patched, count = re.subn(
    r"(^\s*def close\(self[^)]*\):\n)",
    r"\1        # CODEX_TRACY_CLOSE_BYPASS: last-resort workaround for Tracy shutdown hangs.\n        import os; os._exit(0)\n",
    text,
    count=1,
    flags=re.MULTILINE,
)
if count != 1:
    raise SystemExit(f"Could not find close() in {path}")
path.write_text(patched)
print(f"Patched: {path}")
PY

# Verify the patch applied
grep -n 'CODEX_TRACY_CLOSE_BYPASS' "$SIM_APP"

# Restore after the capture
cp "$SIM_APP.bak.codex-tracy-close" "$SIM_APP"
```

### Last Resort: Force-kill Hung Benchmarks When Results Exist

If ALL expected output files exist with non-zero size, and the process is
still running after 2+ minutes with no new output, it is probably hung. Follow the guide sequence and force-kill the app and capture processes:

```bash
RESULT_DIR="/tmp/isaacsim-profile-results"
APP_PID=12345
CAPTURE_PID=12346

ls -la "$RESULT_DIR"/kpis_*.json "$RESULT_DIR"/*.tracy 2>/dev/null
# If files exist and size > 0:
kill -9 "$APP_PID" "$CAPTURE_PID" 2>/dev/null || true
```

## Nsight Systems Profiling

### Install
```bash
# Linux: download from https://developer.nvidia.com/nsight-systems
sudo dpkg -i nsight-systems-*.deb

# Windows: download the latest standalone .msi from https://developer.nvidia.com/nsight-systems
```

### Kit Args for NVTX
```
--/app/profileFromStart=true
--/profiler/enabled=true
--/app/profilerBackend=nvtx
--/profiler/gpu=true
--/app/profilerMask=1
--/plugins/carb.profiler-tracy.plugin/fibersAsThreads=false
--/profiler/channels/carb.events/enabled=false
--/profiler/channels/carb.tasking/enabled=false
```

### Nsys Command

Try without `sudo` first. Use `sudo -E` only when `perf_event_paranoid` blocks CPU sampling or system-wide OS runtime data, and only after confirming it is acceptable for the machine. In containers, `sudo` may not exist and GPU metrics may require extra host privileges.

#### Container-safe mode: NVTX/Vulkan/CUDA only, no CPU sampling

Use this mode when running inside a container where you cannot change `perf_event_paranoid`, cannot switch CPU governor, or do not have host-level perf privileges. Do not burn time fighting CPU sampling in that environment: capture NVTX zones, Vulkan activity, CUDA/Warp/PyTorch activity if present, and OS runtime where available. Treat the run as trace-structure evidence, not a final CPU bottleneck study.

If the host lacks Isaac Sim `standalone_examples/benchmarks` scripts (common with pip-only installs), substitute a verified Isaac Lab benchmark command or another local Kit workload; do not assume `benchmark_camera.py` exists just because `SimulationApp` imports.

```bash
export CARB_PROFILING_PYTHON=1
NSYS_OUTPUT="kit_profile_container"

nsys profile \
  --force-overwrite=true \
  --output="$NSYS_OUTPUT" \
  --sample=none \
  --trace=nvtx,vulkan,cuda,osrt \
  --gpuctxsw=false \
  ./python.sh standalone_examples/benchmarks/benchmark_camera.py \
  --num-cameras 1 --num-frames 100 \
  --no-window --/app/window/hideUi=True \
  --/app/profileFromStart=true --/profiler/enabled=true \
  --/app/profilerBackend=nvtx --/app/profilerMask=1 \
  --/plugins/carb.profiler-tracy.plugin/fibersAsThreads=false \
  --/profiler/channels/carb.events/enabled=false \
  --/profiler/channels/carb.tasking/enabled=false
```

Notes:
- Omit `--gpu-metrics-devices=all` by default in containers; it often fails with `ERR_NVGPUCTRPERM` unless host GPU counter permissions are configured.
- Omit `--sample=system-wide`; it requires host perf permissions and fails when `perf_event_paranoid` is high/read-only.
- If `osrt` is also blocked/noisy in your container, reduce to `--trace=nvtx,vulkan,cuda`.
- Record in the report that CPU sampling and governor control were unavailable, so CPU-side conclusions are lower confidence.

#### Full host mode: CPU sampling and GPU metrics enabled

Use this only on hosts where CPU sampling and GPU metrics are allowed. If the host lacks Isaac Sim `standalone_examples/benchmarks` scripts, substitute a verified local Kit/Isaac Lab workload.

```bash
export CARB_PROFILING_PYTHON=1
NSYS_OUTPUT="kit_profile"

nsys profile \
  --force-overwrite=true \
  --output="$NSYS_OUTPUT" \
  --sample=system-wide \
  --trace=cuda,nvtx,vulkan,osrt \
  --gpu-metrics-devices=all \
  --gpuctxsw=true \
  --cuda-memory-usage=true \
  --cuda-graph-trace=graph:host-and-device \
  ./python.sh standalone_examples/benchmarks/benchmark_camera.py \
  --num-cameras 1 --num-frames 100 \
  --no-window --/app/window/hideUi=True \
  --/app/profileFromStart=true --/profiler/enabled=true \
  --/app/profilerBackend=nvtx --/app/profilerMask=1 \
  --/plugins/carb.profiler-tracy.plugin/fibersAsThreads=false \
  --/profiler/channels/carb.events/enabled=false \
  --/profiler/channels/carb.tasking/enabled=false
```

If `--gpu-metrics-devices=all` fails with `ERR_NVGPUCTRPERM` or permission errors, rerun without GPU metrics or fix the container/host permissions first. See `install-profilers` for setup notes.

### Windows nsys Differences
- `-t osrt` is NOT supported on Windows (use `-t wddm`)
- `nsys profile` CANNOT profile `.bat` files — must target `.exe` directly
- `nsys stats` may fail with UnicodeDecodeError — export to SQLite instead
- Must `cd` to the directory containing the target exe

## Analyzing Profiles

For NVTX zone interpretation and phase detection config, see the `nsys-analyze` skill.

### Product-Specific Profiling Examples

**Isaac Sim with Tracy:**
```bash
./python.sh standalone_examples/benchmarks/benchmark_camera.py \
  --num-cameras 1 --resolution 1920 1080 --num-gpus 1 --num-frames 600 \
  --/app/profilerBackend=tracy --/app/profileFromStart=true \
  --/profiler/enabled=true --/profiler/gpu=true \
  --/profiler/gpu/tracyInject/enabled=true --/app/profilerMask=1 \
  --/plugins/carb.profiler-tracy.plugin/fibersAsThreads=false \
  --/profiler/channels/carb.events/enabled=false \
  --/profiler/channels/carb.tasking/enabled=false \
  --/profiler/gpu/tracyInject/msBetweenClockCalibration=0 \
  --/rtx/addTileGpuAnnotations=true \
  --/plugins/carb.profiler-tracy.plugin/instantEventsAsMessages=true \
  --/exts/isaacsim.benchmark.services/metrics/metrics_output_folder=/tmp/results
```

**Isaac Sim with Nsight (container-safe default):**
```bash
export CARB_PROFILING_PYTHON=1

nsys profile \
  --force-overwrite=true \
  --output=isaacsim_profile \
  --sample=none \
  --trace=nvtx,vulkan,cuda,osrt \
  --gpuctxsw=false \
  ./python.sh standalone_examples/benchmarks/benchmark_camera.py \
  --num-cameras 1 --num-frames 100 \
  --no-window --/app/window/hideUi=True \
  --/app/profileFromStart=true --/profiler/enabled=true \
  --/app/profilerBackend=nvtx --/app/profilerMask=1 \
  --/plugins/carb.profiler-tracy.plugin/fibersAsThreads=false \
  --/profiler/channels/carb.events/enabled=false \
  --/profiler/channels/carb.tasking/enabled=false
```

**Isaac Sim with Nsight (full host-only mode):**
```bash
export CARB_PROFILING_PYTHON=1
export DISPLAY=:0
export OMNI_PASS='<YOUR_API_KEY>'
export OMNI_USER='$omni-api-token'

# Raise the soft file-descriptor limit without sudo when the shell allows it.
ulimit -n 65536 2>/dev/null || echo "Could not raise nofile soft limit; continuing"

nsys profile \
  --force-overwrite=true \
  --output=isaacsim_profile \
  --sample=system-wide \
  --trace=cuda,nvtx,vulkan,osrt \
  --gpu-metrics-devices=all \
  --gpuctxsw=true \
  --cuda-memory-usage=true \
  --cuda-graph-trace=graph:host-and-device \
  ./python.sh standalone_examples/benchmarks/benchmark_camera.py \
  --num-cameras 1 --num-frames 100 \
  --no-window --/app/window/hideUi=True \
  --/app/profileFromStart=true --/profiler/enabled=true \
  --/app/profilerBackend=nvtx --/app/profilerMask=1 \
  --/plugins/carb.profiler-tracy.plugin/fibersAsThreads=false \
  --/profiler/channels/carb.events/enabled=false \
  --/profiler/channels/carb.tasking/enabled=false

# If CPU sampling is still blocked and privileged profiling is approved, rerun
# the same command with `sudo -E nsys profile ...`; do not use sudo by default.
```

**Isaac Lab with Nsight (container-safe default):**
```bash
OMNI_KIT_ALLOW_ROOT=1 DISPLAY=:0 \
  TRACY_NO_SYS_TRACE=1 TRACY_NO_CALLSTACK=1 CARB_PROFILING_PYTHON=1 \
  nsys profile --force-overwrite=true --output=isaaclab_profile \
  --sample=none --trace=nvtx,vulkan,cuda,osrt --gpuctxsw=false \
  ./isaaclab.sh -p scripts/benchmarks/benchmark_non_rl.py \
  --task=Isaac-Cartpole-Direct-v0 --viz none --num_frames 100 \
  --kit_args "--/app/profileFromStart=true --/profiler/enabled=true --/app/profilerBackend=nvtx --/app/profilerMask=1 --/plugins/carb.profiler-tracy.plugin/fibersAsThreads=false --/profiler/channels/carb.events/enabled=false --/profiler/channels/carb.tasking/enabled=false"
```

For host-only CPU sampling/GPU metrics, add `--sample=system-wide --gpu-metrics-devices=all --gpuctxsw=true` only when the host allows it. Use `sudo -E` only if the non-sudo command fails because CPU sampling is blocked and you have approval to run privileged profiling.

### Export Handoff

Export traces here, then use `nsys-analyze` for SQL queries, Tracy Statistics/Range Limit comparison, zone ranking, phase detection, and interpretation.
Tracy `capture` already applies LZ4 compression. For sharing very large `.tracy` files, optionally recompress with `update -z 1`.

### nsys SQLite Export (when nsys stats fails or custom queries needed)
```bash
nsys export --type=sqlite -o profile.sqlite profile.nsys-rep
csvexport profile.tracy > zones.csv

TRACY_UPDATE_BIN=$(command -v update || command -v tracy-update || true)
[ -n "$TRACY_UPDATE_BIN" ] && "$TRACY_UPDATE_BIN" -z 1 profile.tracy profile.recompressed.tracy
```

---

# CPU Governor — Performance Mode

**MANDATORY before any benchmark.** See the `perf-tuning` skill for commands and details.

---
