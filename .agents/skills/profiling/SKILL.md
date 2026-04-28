---
name: profiling
description: Capture performance traces using Tracy and Nsight Systems for Kit-based applications (Isaac Sim, Isaac Lab, Kit SDK). Covers Tracy capture sequence (port management, last-resort shutdown workaround), nsys profile commands, Kit args for each backend, CPU governor setup, and the COLD/WARM/TRACE methodology. Use when running profiling captures, setting up trace collection, or troubleshooting capture failures. NOT for adding profiling zones to code (use profiling-api skill) or analyzing captured traces (use nsys-analyze skill).
---

# Profiling Guide

This is the canonical reference for profiling Kit-based applications (Isaac Sim, Isaac Lab, Kit SDK).
Other skills reference this one for profiling details — keep this up to date.

## Benchmark Accuracy: COLD / WARM / TRACE

Profilers add overhead. Keep measurement and diagnosis as separate runs:

1. **COLD:** first run after a fresh install/cache state. Use this to expose startup and shader-cache effects, not as the steady-state performance number.
2. **WARM:** same workload with caches already populated and profiling disabled. This is the authoritative FPS/frametime benchmark run.
3. **TRACE:** Tracy or nsys enabled for attribution. Use this to explain bottlenecks, not as the headline performance number.

Only enable high-overhead Python function capture (`CARB_PROFILING_PYTHON=1`) in TRACE runs when Python call-level attribution is needed.

## Tracy Profiling

### Environment Setup
```bash
export TRACY_NO_SYS_TRACE=1
export TRACY_NO_CALLSTACK=1

# Optional, high overhead. Do not set during WARM benchmark measurement.
# export CARB_PROFILING_PYTHON=1
```

### Kit Args (common for all Kit-based products)
```
--/app/profilerBackend=tracy
--/app/profileFromStart=true
--/profiler/gpu/tracyInject/enabled=true
--/app/profilerMask=1
--/plugins/carb.profiler-tracy.plugin/fibersAsThreads=false
--/profiler/channels/carb.events/enabled=false
--/profiler/channels/carb.tasking/enabled=false
--/rtx/addTileGpuAnnotations=true
```

### Tracy Capture — Correct Procedure (IMPORTANT)

Tracy capture is error-prone. Follow this exact sequence to avoid port conflicts and data loss.

**Default Tracy port: 8086.** Kit/Isaac Sim auto-increments to 8087, 8088... if 8086 is already in use.

**Tracy capture binary:** Build from source at https://github.com/wolfpld/tracy or obtain pre-built binaries.

#### Step-by-step:
```bash
# 1. Kill any existing Tracy-related processes hogging the port
pkill -f '(^|/)(tracy-capture|capture)( |$)' || true
ss -tlnp | grep :8086  # verify port is free

TRACY_CAPTURE_BIN=$(command -v tracy-capture || command -v capture)
[ -n "$TRACY_CAPTURE_BIN" ] || { echo "Missing Tracy capture binary"; exit 1; }

# 2. Start the application FIRST (in background)
nohup ./python.sh <benchmark_script> <args> \
  --/app/profilerBackend=tracy --/app/profileFromStart=true \
  ... > /tmp/app.log 2>&1 &
APP_PID=$!

# 3. Poll until Tracy port is open (app needs time to initialize)
for i in $(seq 1 60); do
  ss -tlnp | grep -q :8086 && break
  sleep 2
done

# 4. Start capture AFTER port is confirmed open
"$TRACY_CAPTURE_BIN" -o trace_output.tracy -f -p 8086

# 5. Wait for app to finish — capture auto-disconnects and saves
# DO NOT kill capture manually! It saves data only on clean disconnect.
wait $APP_PID
```

#### Critical warnings:
- **NEVER start capture before the app.** The app might open on 8087 if 8086 is occupied.
- **NEVER kill capture with kill/SIGTERM.** It will NOT save the trace file.
- **Always check for zombie processes** on port 8086 before starting.
- **v6.0.0 shutdown hang:** v6.0.0 with Tracy may hang during shutdown. If the app doesn't exit within ~2 min after benchmark completes, kill the app process (not capture).

### Last Resort: Scoped `os._exit(0)` Close Patch

Do **not** patch installed Isaac Sim files by default. Normal shutdown is preferred because it runs cleanup code and keeps the install reproducible.

Use this workaround only when all of the following are true:
- The workload repeatedly hangs during Tracy shutdown.
- Expected benchmark and trace outputs already exist with non-zero size.
- The install is disposable or you can restore the original file immediately after capture.

Prefer first to let the app exit normally. If it hangs after results are complete, kill the **app process**, not the Tracy capture process. Patch only when repeated hangs prevent clean capture completion.

```bash
# Find simulation_app.py — path varies between source and build layouts:
#   Source build: source/extensions/isaacsim.simulation_app/isaacsim/simulation_app/simulation_app.py
#   Build output: _build/linux-x86_64/release/exts/isaacsim.simulation_app/isaacsim/simulation_app/simulation_app.py
# NOTE: `find -path` may fail in some environments (dots in dir names). Use glob instead:
shopt -s globstar nullglob
SIM_APP=$(echo <package_path>/**/isaacsim/simulation_app/simulation_app.py | tr ' ' '\n' | grep -v __pycache__ | head -1)
# Or explicit known paths:
# SIM_APP=<package_path>/_build/linux-x86_64/release/exts/isaacsim.simulation_app/isaacsim/simulation_app/simulation_app.py
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
still running after 2+ minutes with no new output, it is probably hung. Kill the app process, not the Tracy capture process:

```bash
ls -la <result_path>/kpis_*.json <result_path>/*.tracy 2>/dev/null
# If files exist and size > 0:
kill <app_pid>
sleep 10
kill -9 <app_pid> 2>/dev/null || true
```

## Nsight Systems Profiling

### Install
```bash
# Linux: download from https://developer.nvidia.com/nsight-systems
sudo dpkg -i nsight-systems-*.deb

# Windows: install via CUDA Toolkit from https://developer.nvidia.com/cuda-downloads
```

### Kit Args for NVTX
```
--/app/profileFromStart=true
--/profiler/enabled=true
--/app/profilerBackend=nvtx
--/app/profilerMask=1
--/plugins/carb.profiler-tracy.plugin/fibersAsThreads=false
--/profiler/channels/carb.events/enabled=false
--/profiler/channels/carb.tasking/enabled=false
```

### Nsys Command
```bash
# Optional, high overhead. Use only when Python call-level attribution is needed.
# export CARB_PROFILING_PYTHON=1

sudo -E nsys profile \
  -t nvtx,cuda,osrt \
  --gpu-metrics-devices=all \
  --gpuctxsw=true \
  --cuda-memory-usage=true \
  --python-backtrace=cuda \
  <APPLICATION_COMMAND>
```

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
  --/profiler/gpu/tracyInject/enabled=true --/app/profilerMask=1 \
  --/plugins/carb.profiler-tracy.plugin/fibersAsThreads=false \
  --/profiler/channels/carb.events/enabled=false \
  --/profiler/channels/carb.tasking/enabled=false \
  --/rtx/addTileGpuAnnotations=true \
  --/exts/isaacsim.benchmark.services/metrics/metrics_output_folder=/tmp/results
```

**Isaac Lab with Nsight:**
```bash
sudo -E nsys profile -t nvtx,cuda,osrt --gpu-metrics-devices=all \
  --gpuctxsw=true --cuda-memory-usage=true --python-backtrace=cuda \
  ./isaaclab.sh -p scripts/benchmarks/benchmark_non_rl.py \
  --task=Isaac-Cartpole-RGB-Camera-Direct-v0 --num_frames 100 --viz none --enable_cameras --num_envs=512 \
  --kit_args "--/app/profileFromStart=true --/profiler/enabled=true --/app/profilerBackend=nvtx --/app/profilerMask=1"
```

### nsys SQLite Export (when nsys stats fails or custom queries needed)
```bash
nsys export --type=sqlite -o profile.sqlite profile.nsys-rep
```

**NVTX_EVENTS gotcha:** There is NO `name` column. Use `text` (inline) or join `textId` to `StringIds`:
```sql
sqlite3 profile.sqlite "
SELECT COALESCE(e.text, s.value) as zone_name,
       COUNT(*) as cnt,
       ROUND(AVG(e.end - e.start) / 1e6, 2) as avg_ms,
       ROUND(SUM(e.end - e.start) / 1e6, 2) as total_ms
FROM NVTX_EVENTS e
LEFT JOIN StringIds s ON e.textId = s.id
WHERE e.start > 25000000000
  AND e.end IS NOT NULL AND (e.end - e.start) > 0
GROUP BY zone_name ORDER BY total_ms DESC LIMIT 30;
"
```

**CUDA Kernels = 0 is normal** for Kit/Isaac Sim — RTX uses its own GPU pipeline, not CUDA API. NVTX zones are the only analysis source.

### Tracy CSV Export (alternative analysis path)
```bash
csvexport profile.tracy > zones.csv
# Columns: name, src_file, src_line, total_ns, total_perc, counts, mean_ns, min_ns, max_ns, std_ns
sort -t',' -k4 -rn zones.csv | head -50
```

---

# CPU Governor — Performance Mode

**MANDATORY before any benchmark.** See the `perf-tuning` skill for commands and details.

---
