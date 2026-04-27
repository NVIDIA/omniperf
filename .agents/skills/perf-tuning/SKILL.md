---
name: perf-tuning
description: Resolve common Kit/Isaac Sim/Isaac Lab performance issues using specific settings and configuration changes. Covers PresentFrame stalls, resolveSamplerFeedback, headless mode, multi-GPU tradeoffs, DLSS/DLSS-G, PhysX tuning, RTX presets (isaaclab_performance/balanced/quality), viewport gizmos, HydraEngine waitIdle, fsWatcher overhead, and CPU governor. Use when profiling data shows a specific bottleneck and you need the fix, when someone asks "why is it slow" and you have Tracy/nsys evidence, or when tuning RTX settings for GPU-bound workloads. NOT for: initial triage (use diagnose-perf), capturing profiles (use profiling), or analyzing traces (use nsys-analyze).
---

# Performance Tuning for Kit / Isaac Sim / Isaac Lab

Specific fixes for performance issues identified through profiling.
Prerequisite: you should already know *where* the bottleneck is (from `diagnose-perf`, `profiling`, or `nsys-analyze` skills).

## PresentFrame is Abnormally Slow

Two causes:

### GPU Backpressure
GPU work exceeds frame budget → CPU waits for swapchain buffer.

**Verify:** Enable GPU zones in Tracy and check if GPU frametime > CPU frametime.
```bash
--/profiler/gpu/tracyInject/enabled=true --/profiler/gpu=true --/rtx/addTileGpuAnnotations=true
```

**Fix:** Reduce GPU workload — see [RTX Tuning](#rtx-tuning-when-gpu-bound) below.

### VNC / Remote Desktop
Virtual framebuffer causes driver present timing issues.

**Fix:** Use a physical monitor or run in headless mode.

## resolveSamplerFeedback is Abnormally Slow

Texture Streaming bug causes per-frame thread waits proportional to RenderProduct count.

**Fix:** Disable Texture Streaming:
```bash
--/rtx-transient/resourcemanager/enableTextureStreaming=false
```

**Impact:** ~6.72 ms saved per frame (measured). VRAM usage may increase — verify headroom.

## Headless Mode (3–4 ms GPU savings)

For simulation-only workloads (RL training, SDG, automated benchmarks):

```python
# Isaac Sim via SimulationApp
simulation_app = SimulationApp({"headless": True, "disable_viewport_updates": True})
```

```bash
# Kit args
--no-window --/app/window/hideUi=True
```

Also disable viewport updates in Python:
```python
from omni.kit.viewport.utility import get_active_viewport
get_active_viewport().updates_enabled = False
```

## Multi-Camera Render Count Verification

Always check Tracy GPU zones to verify only intended cameras are rendering:
- Count `extrt/rtx/rtaTexturesMC_*` (camera textures) and `t_viewport_ViewportTexture_*` (viewport textures)
- Verify resolution in zone names matches intent (e.g., `rtaTexturesMC_3_RP_1920x1080`)
- In headless mode, check that unnecessary viewport textures aren't rendering in background

## PhysX Tuning

### Expose Full PhysX Detail
Default `profilerMask=1` hides internal PhysX zones. To diagnose PhysX bottlenecks, remove the mask arg (defaults to ALL).

### Key Settings

| Setting | Effect |
|---------|--------|
| `--/physics/suppressReadback=true` | Suppress GPU→CPU readback |
| `--/physics/updateToUsd=false` | Skip physics→USD writeback (only if not reading state from USD) |
| `--/physics/disableContactProcessing=true` | Skip contact event callbacks (if no subscriber needs them) |

### Async Physics (USD Schema)

```python
from pxr import UsdPhysics, PhysxSchema

stage = omni.usd.get_context().get_stage()
for prim in stage.Traverse():
    if prim.IsA(UsdPhysics.Scene):
        api = PhysxSchema.PhysxSceneAPI.Apply(prim)
        api.CreateUpdateTypeAttr().Set(PhysxSchema.Tokens.asynchronous)
```

Applicable when previous-frame physics results are acceptable (RL training, SDG).

### Solver Type
PGS (type 0) = faster, less accurate. TGS (type 1) = more accurate, slightly slower.
```bash
--/physics/physxScene/solverType=0  # PGS for speed
```

## Extension Change Detection (fsWatcher)

~0.1 ms/frame overhead for hot-reload file monitoring. Disable for benchmarks:
```bash
--/app/extensions/fsWatcherEnabled=false
```

## Viewport Gizmo Overhead

Gizmos (manipulators, grid, selection outlines) cause significant CPU overhead in scenes with many objects.

```bash
--/persistent/app/viewport/displayOptions=0
--/persistent/app/viewport/gizmo/enabled=false
```

## DLSS-G (Frame Generation) — Know What You're Measuring

DLSS-G inserts AI sub-frames between real frames:
- **Viewport HUD FPS** includes sub-frames → inflated by 2–4x
- **Tracy/benchmark frametime FPS** = actual rendering FPS

| GPU Gen | Sub-frame Multiplier |
|---------|---------------------|
| Ada (RTX 40) | 2x |
| Blackwell (RTX 50) | 3–4x |

**Rule:** DLSS-G is for viewport display only. Disable for simulation/benchmarks:
```bash
--/rtx-transient/dlssg/enabled=false  # default is off, but verify
```

## HydraEngine waitIdle

When `/app/hydraEngine/waitIdle=true` (default), main thread blocks every frame until GPU finishes.

```bash
--/app/hydraEngine/waitIdle=false  # allow CPU-GPU pipelining
```

Safe for rendering-only workloads. Keep `true` if reading GPU results same-frame (physics readback, synchronous sensors).

## Multi-GPU — Not Always Faster

Multi-GPU adds CPU overhead (job distribution, per-GPU setup, data gathering). Only effective when GPU is the clear bottleneck.

| Scenario | Recommendation |
|----------|---------------|
| High-res (4K) × many cameras (4–8) | Multi-GPU effective |
| Low-res (1080p) × few cameras (1–2) | Single GPU faster |
| CPU-bottlenecked | Adding GPUs = pointless |

**Always verify GPU-bound with Tracy/nsys before adding GPUs.**

## CPU Governor

```bash
# Check
cat /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor | sort | uniq -c
# Fix
echo performance | sudo tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor
```

Real impact: `powersave` → `performance` saved ~4 ms/frame in measured cases.

## RTX Tuning When GPU-Bound

### Recommended Approach
Start from an IsaacLab preset, then selectively re-enable features you need.

### IsaacLab Presets (ChessRTX path-traced, RTX PRO 6000 Blackwell)

| Preset | FPS | Δ vs default |
|--------|-----|-------------|
| (default) | 51.85 | — |
| `isaaclab_quality` | 70.25 | +35.5% |
| `isaaclab_balanced` | 87.81 | +69.4% |
| `isaaclab_performance` | 111.90 | +115.8% |

### DLSS execMode — Single Biggest Lever

| execMode | Mode | FPS | Δ vs default |
|----------|------|-----|-------------|
| 0 | Performance | 106.24 | +104.9% |
| 1 | Balanced | 87.08 | +68.0% |
| 2 | Quality | 71.42 | +37.7% |

```bash
--/rtx/post/dlss/execMode=0  # always specify 0/1/2 — mode 3 (Auto) broken in headless
```

~91% of `isaaclab_performance`'s gain comes from this single setting.

### Full Preset Parameter Table

For detailed per-parameter comparison across all three presets, see `references/rtx-presets.md`.

### Tuning Checklist

1. Confirm GPU-bound with Tracy/nsys
2. Verify DLSS-G off for simulation (`--/rtx-transient/dlssg/enabled=false`)
3. Set `--/rtx/post/dlss/execMode=0` (biggest single lever)
4. Apply `isaaclab_performance` preset for maximum speed
5. Selectively re-enable visual features as needed
6. Scene-dependent — numbers will vary
