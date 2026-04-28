---
name: diagnose-perf
description: First-responder performance triage for Isaac Sim and Isaac Lab. Identifies bottleneck category (GPU-bound, CPU-bound, VRAM, loading) using nvidia-smi and system tools without profiling. Use when a user reports slow FPS, stuttering, high latency, or wants a quick health check before profiling. NOT for applying specific fixes (use perf-tuning), capturing traces (use profiling), or analyzing traces (use nsys-analyze).
---

# Performance Diagnosis Guide

Quick triage to identify the most likely performance bottleneck in an Isaac Sim or Isaac Lab workload.
This skill does NOT require profiling tools — it uses only nvidia-smi, standard Linux utilities, and Kit config inspection.

For deeper analysis after triage, use the **profiling** and **nsys-analyze** skills.

## Phase 1 — System Snapshot (no Isaac process needed)

Run these commands and check for red flags. Keep this skill read-only: collect facts and classify the bottleneck. Mutating fixes such as persistence mode, CPU governor changes, or package installs belong in `perf-tuning`/install skills and require approval.

### GPU Info
```bash
nvidia-smi -q | grep -E "Product Name|FB Memory Usage|GPU Current Temp|Performance State|Clocks Throttle|Driver Version|CUDA Version|PCIe Generation"
```

Key fields to check:

| Field | Red Flag | Action |
|-------|----------|--------|
| Performance State | P2 or higher (P3, P8…) | GPU in power-saving mode — run a workload to wake it; persistence-mode changes are host mutations and need approval |
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

| SM Util | Mem Util | VRAM | CPU | Diagnosis | Handoff |
|---------|----------|------|-----|-----------|------------|
| >80% | Low | OK | Low | **GPU compute-bound** (rendering or physics) | Profile with nsys to separate RTX vs PhysX zones |
| Low | >80% | High | Low | **VRAM bandwidth-bound** | Use `perf-tuning` for texture/material/Fabric options |
| Low | Low | >95% | Low | **VRAM capacity-bound** (near OOM) | Use `perf-tuning` for scene/render-resolution options |
| Low | Low | OK | >80% | **CPU-bound** | Use `perf-tuning` for Python/USD/Fabric options |
| High | Low | OK | High | **Balanced load** (good!) | Already well-utilized — micro-optimize with profiler |
| Low | Low | OK | Low | **Idle/waiting** | Check if rate-limited, sleeping, or blocked on I/O |
| Spiky | Any | Growing | Any | **Loading-bound** | Use `profiling`/`nsys-analyze` if the loading source is unclear |

### Physics vs Rendering (if GPU compute-bound)
Without profiling, check these heuristics:
- **Physics-heavy scene** (>100 rigid bodies, soft bodies, fluids): likely PhysX-bound
- **Camera/lidar-heavy scene** (multiple render products): likely render-bound
- **Both**: profile to separate — use `profiling` skill with NVTX markers

## Phase 4 — Triage Handoff

Do not apply fixes from this skill. Use the bottleneck classification above to choose the next skill:

1. **Need likely fixes now:** use `perf-tuning` with the red flags and bottleneck category.
2. **Need exact hotspot attribution:** use `profiling` to capture traces, then `nsys-analyze`.
3. **Need a benchmark comparison:** use `benchmark-isaacsim` or `benchmark-isaaclab` for WARM results.

Common handoff topics for `perf-tuning`: headless/viewport work, Fabric, debug visualization, CPU governor, RTX quality, PhysX settings, collision geometry, and waitIdle/async rendering.

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

For the full performance settings reference (physics, rendering, app loop), see the `perf-tuning` skill.

Settings can be applied via:
- `.kit` files in `apps/` directory
- CLI: `--/setting/path=value`
- Python: `carb.settings.get_settings().set("/setting/path", value)`

## When to Escalate to Full Profiling

This triage identifies the *category* of bottleneck. For *specific* hotspots, use:
- **profiling** skill → capture nsys/Tracy traces
- **nsys-analyze** skill → analyze traces to find exact functions/zones causing slowdowns

Escalate when:
- Triage shows GPU compute-bound but you need to know if it's physics or rendering
- FPS is inexplicably low despite healthy system metrics
- The user needs frame-by-frame timing breakdown
- Comparing performance between two versions or configurations
