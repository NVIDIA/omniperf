---
name: diagnose-perf
description: First-responder performance triage for Isaac Sim and Isaac Lab. Use when a user reports slow FPS, stuttering, high latency, or wants a quick health check before profiling.
---

# Performance Diagnosis Guide

Quick triage to identify the most likely performance bottleneck in an Isaac Sim or Isaac Lab workload.
This skill does NOT require profiling tools — it uses only nvidia-smi, standard Linux utilities, and Kit config inspection.

For deeper analysis after triage, use the **profiling** and **nsys-analyze** skills.

## Phase 1 — System Snapshot (no Isaac process needed)

Run these commands and check for red flags:

### GPU Info
```bash
nvidia-smi -q | grep -E "Product Name|FB Memory Usage|GPU Current Temp|Performance State|Clocks Throttle|Driver Version|CUDA Version|PCIe Generation"
```

Key fields to check:

| Field | Red Flag | Action |
|-------|----------|--------|
| Performance State | P2 or higher (P3, P8…) | GPU in power-saving mode — run a workload to wake it, or set `nvidia-smi -pm 1` |
| Clocks Throttle Reasons | Any "Active" | Thermal or power throttling — check cooling, power limits |
| FB Memory Usage | >90% used at idle | Other processes hogging VRAM — check with `nvidia-smi` process list |
| PCIe Generation | Gen2 or Gen1 | Bandwidth bottleneck for large scenes — check BIOS/motherboard |
| GPU Current Temp | >85°C | Thermal throttling likely — improve airflow |

### CPU Info
```bash
# Governor (performance = best for benchmarks)
cat /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor | sort -u

# Core count
nproc

# Current frequency
lscpu | grep "MHz"
```

**Red flag:** Governor is `powersave` or `schedutil` — for benchmarks, `performance` is recommended:
```bash
# Requires root; may be read-only in containers
sudo cpupower frequency-set -g performance
```

### Memory
```bash
free -h
```
**Red flag:** Swap usage > 0 during Isaac runs means system RAM is insufficient.

## Phase 2 — Runtime Capture (Isaac process running)

Start the Isaac workload, then capture GPU metrics while it runs:

### GPU Monitoring
```bash
# Run for 30 seconds alongside the workload
nvidia-smi dmon -s pucm -d 1 -c 30 > /tmp/gpu_monitor.csv
```

Columns: `pwr` (watts), `gtemp` (°C), `sm` (SM utilization %), `mem` (memory utilization %), `fb` (VRAM MB used)

### Process-Level Check
```bash
# Find Isaac process
ISAAC_PID=$(pgrep -f "isaac-sim\|kit\|python.*isaacsim" | head -1)

# CPU and memory usage
top -bn1 -p $ISAAC_PID | tail -1

# Thread count (high = possible thread contention)
ls /proc/$ISAAC_PID/task 2>/dev/null | wc -l
```

### Quick Frame Timing (if benchmark outputs JSON)
If the user ran a benchmark skill, check the output JSON for FPS:
```bash
cat /tmp/benchmark_output/*.json | python3 -c "
import json, sys
data = json.load(sys.stdin)
for phase in data:
    for m in phase.get('measurements', []):
        metric = m.get('name') or m.get('metric', '')
        value = m.get('data', m.get('value'))
        if isinstance(metric, str) and ('fps' in metric.lower() or 'time' in metric.lower()) and value is not None:
            print(f\"{phase['phase_name']}: {metric} = {value:.2f}\")
"
```

## Phase 3 — Bottleneck Classification

Use the GPU monitoring data to classify the bottleneck:

### Reading the nvidia-smi dmon Output
```bash
# Average SM and memory utilization from capture
awk 'NR>2 && $1!="#" {sm+=$5; mem+=$6; n++} END {printf "Avg SM: %.0f%%  Avg MEM: %.0f%%\n", sm/n, mem/n}' /tmp/gpu_monitor.csv
```

### Decision Tree

| SM Util | Mem Util | VRAM | CPU | Diagnosis | Next Steps |
|---------|----------|------|-----|-----------|------------|
| >80% | Low | OK | Low | **GPU compute-bound** (rendering or physics) | Profile with nsys to separate RTX vs PhysX zones |
| Low | >80% | High | Low | **VRAM bandwidth-bound** | Reduce texture resolution, simplify materials, check Fabric |
| Low | Low | >95% | Low | **VRAM capacity-bound** (near OOM) | Reduce scene complexity, lower render resolution |
| Low | Low | OK | >80% | **CPU-bound** | Check Python GIL, reduce USD stage queries, enable Fabric |
| High | Low | OK | High | **Balanced load** (good!) | Already well-utilized — micro-optimize with profiler |
| Low | Low | OK | Low | **Idle/waiting** | Check if rate-limited, sleeping, or blocked on I/O |
| Spiky | Any | Growing | Any | **Loading-bound** | Scene loading dominates — see Phase 4 Quick Wins |

### Physics vs Rendering (if GPU compute-bound)
Without profiling, check these heuristics:
- **Physics-heavy scene** (>100 rigid bodies, soft bodies, fluids): likely PhysX-bound
- **Camera/lidar-heavy scene** (multiple render products): likely render-bound
- **Both**: profile to separate — use `profiling` skill with NVTX markers

## Phase 4 — Quick Wins Checklist

These are the most common performance improvements, in order of impact:

### 1. Headless Mode (biggest win for non-visual workloads)
```bash
# Isaac Sim v5.x
./isaac-sim.sh --headless

# Isaac Sim v6.x
./isaac-sim.sh --enable isaacsim.core.experimental.headless

# Isaac Lab (Python script)
python train.py --headless
# Note: --headless flag is deprecated in Isaac Sim v6; use --enable ext instead
```
**Impact:** 2-10x FPS improvement by skipping viewport rendering.

### 2. Fabric (USD acceleration)
```
--/physics/fabricEnabled=true
```
Or in Python:
```python
sim_cfg = SimulationCfg(use_fabric=True)
```
**Impact:** Significant for scenes with many USD prims. Fabric bypasses the USD stage for physics data.

### 3. Disable Physics Debug Visualization
```
--/physics/debugDraw=false
--/physics/visualizationDisplayJoints=false
```
These are sometimes left on accidentally and cost GPU time.

### 4. Rate Limiting / Fixed Timestep
```
--/app/runLoops/main/rateLimitEnabled=true
--/app/runLoops/main/rateLimitFrequency=60
```
If FPS is uncapped and GPU is at 100%, the app may be doing unnecessary work.

### 5. Async Rendering
```
--/app/asyncRendering=true
--/app/asyncRenderingLowLatency=false
```
Allows physics and rendering to overlap. Small FPS gain, but may add one frame of latency.

### 6. PhysX Solver Tuning
```
--/physics/physxScene/solverType=1          # TGS (more accurate, slightly slower)
--/physics/physxScene/solverType=0          # PGS (faster, less accurate)
--/physics/physxScene/gpuMaxRigidContactCount=524288
--/physics/physxScene/gpuMaxRigidPatchCount=81920
```
If you see PhysX warnings about "exceeding max contacts", increase these buffers.
If physics fidelity isn't critical, try PGS solver (type 0).

### 7. Convex Hull / Collision Geometry
Check Kit logs for warnings like:
```bash
grep -i "convex\|collision\|trianglemesh\|falling back to CPU" /tmp/isaac_logs/*.log 2>/dev/null
```
**Red flag:** "Falling back to CPU PhysX" means a collision mesh couldn't run on GPU — simplify the collision geometry or use convex decomposition.

### 8. Rendering Quality Tradeoffs
```
--/rtx/post/aa/op=0                                    # Disable anti-aliasing
--/rtx/ecoMode/enabled=true                            # Lower-quality but faster rendering
--/rtx/directLighting/sampledLighting/enabled=false     # Simpler lighting
```

## Triage Report Template

After running Phases 1-3, summarize findings in this format:

```
## Performance Triage Report

### System
- GPU: [model] ([VRAM] GB) — Driver [version], CUDA [version]
- CPU: [model] × [cores] — Governor: [governor]
- RAM: [total] ([used] used, [swap] swap)
- PCIe: Gen[N]

### Red Flags
- [ ] GPU throttling: [yes/no, reason]
- [ ] CPU governor: [performance/powersave/schedutil]
- [ ] VRAM pressure: [usage %]
- [ ] Swap in use: [yes/no]

### Runtime Metrics (30s average)
- GPU SM utilization: [N]%
- GPU memory utilization: [N]%
- VRAM used: [N] MB / [total] MB
- CPU usage: [N]%

### Bottleneck Classification
**[GPU compute / VRAM bandwidth / VRAM capacity / CPU / Loading / Idle]**

### Recommended Actions
1. [Most impactful fix]
2. [Second fix]
3. [If deeper analysis needed: "Profile with nsys — see profiling skill"]
```

## Kit Settings Reference

### Where to Find Settings
- `.kit` files in `apps/` directory of Isaac Sim installation
- Runtime overrides via command line: `--/setting/path=value`
- Python API: `carb.settings.get_settings().set("/setting/path", value)`

### Key Performance Settings
```
# Physics
/physics/fabricEnabled                    # true = Fabric acceleration
/physics/physxScene/solverType            # 0=PGS, 1=TGS
/physics/physxScene/gpuMaxRigidContactCount
/physics/physxScene/gpuMaxRigidPatchCount
/physics/physxScene/broadPhaseType        # 0=SAP, 1=MBP, 2=ABP, 3=GPU
/physics/debugDraw                        # false for production

# Rendering
/app/asyncRendering                       # true = overlap physics+render
/app/asyncRenderingLowLatency             # false = more overlap
/rtx/ecoMode/enabled                      # true = lower quality, faster
/rtx/post/aa/op                           # 0 = no AA

# App loop
/app/runLoops/main/rateLimitEnabled       # true = cap FPS
/app/runLoops/main/rateLimitFrequency     # target FPS cap
```

## When to Escalate to Full Profiling

This triage identifies the *category* of bottleneck. For *specific* hotspots, use:
- **profiling** skill → capture nsys/Tracy traces
- **nsys-analyze** skill → analyze traces to find exact functions/zones causing slowdowns

Escalate when:
- Triage shows GPU compute-bound but you need to know if it's physics or rendering
- FPS is inexplicably low despite healthy system metrics
- The user needs frame-by-frame timing breakdown
- Comparing performance between two versions or configurations
