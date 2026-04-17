---
name: profiling
description: Profile and capture performance data using Tracy and Nsight Systems. Use when the user asks to profile, capture traces, or measure performance overhead.
---

# Profiling Guide

This is the canonical reference for profiling Kit-based applications (Isaac Sim, Isaac Lab, Kit SDK).
Other skills reference this one for profiling details — keep this up to date.

## Tracy Profiling

### Environment Setup
```bash
export CARB_PROFILING_PYTHON=1
export TRACY_NO_SYS_TRACE=1
export TRACY_NO_CALLSTACK=1
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

### MANDATORY: Apply `os._exit(0)` close patch (prevents shutdown hang)

Isaac Sim's `simulation_app.py` `close()` method hangs during shutdown, especially with Tracy.
Patch BEFORE running any benchmark:

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

# Insert os._exit(0) as first line of the close() method body.
# The docstring varies across versions so we match the method signature instead.
sed -i '/def close(self[^)]*)/a\        import os; os._exit(0)' "$SIM_APP"

# Verify the patch applied
grep -n 'os._exit(0)' "$SIM_APP"
```

> **Why not sed on the docstring?** The docstring text differs between v5 (`"""Close the running
> Omniverse Toolkit application."""` — multi-line) and v6, and the old single-line pattern
> `"""Close the running Omniverse Toolkit."""` silently fails on both. Matching the `def close`
> signature is robust across versions.

Must be applied to EVERY fresh install.

### MANDATORY: Force-kill hung benchmarks when results exist

If ALL expected output files exist with non-zero size, and the process is
still running after 2+ minutes with no new output, it is HUNG. Force-kill it:

```bash
ls -la <result_path>/kpis_*.json <result_path>/*.tracy 2>/dev/null
# If files exist and size > 0:
kill -9 <pid>
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
export CARB_PROFILING_PYTHON=1

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
  --task=Isaac-Cartpole-RGB-Camera-Direct-v0 --num_frames 100 --headless --enable_cameras --num_envs=512 \
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

## MANDATORY: Set Before ANY Benchmark

```bash
# Check
cat /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor | sort | uniq -c

# Set
echo performance | sudo tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor

# Verify
cat /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor | sort | uniq -c
```

- Not persistent across reboots
- Requires sudo
- Dynamic governors (`ondemand`, `schedutil`) cause inconsistent benchmark results

---
