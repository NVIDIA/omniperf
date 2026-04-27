---
name: profiling-api
description: Add profiling zones, metrics, and annotations to Kit-based C++ and Python code. Covers Carbonite macros (CARB_PROFILE_ZONE, CARB_PROFILE_FUNCTION, GPU zones), Python profiler API (decorators, begin/end), profiler masks, channels, Tracy plot data, event annotations, and automatic Python function capture (CARB_PROFILING_PYTHON). Use when a developer asks how to add profiling spans to their code, needs to understand mask/channel configuration, wants to record custom metrics as Tracy plots, or needs to annotate traces with event markers. NOT for capturing traces (use profiling skill) or analyzing them (use nsys-analyze skill).
---

# Profiling API — Instrumenting Kit-Based Code

How to add profiling zones, metrics, and annotations to C++ and Python code in the Carbonite/Kit ecosystem.
For *capturing* traces, see the `profiling` skill. For *analyzing* them, see `nsys-analyze`.

## C++ Profiling Macros

Source: `carb/profiler/Profile.h`

### Scope-Based Zone (most common)

```cpp
#include <carb/profiler/Profile.h>
constexpr const uint64_t kProfilerMask = 1;

void myFunction() {
    CARB_PROFILE_ZONE(kProfilerMask, "My C++ function");
    doHeavyWork();  // zone closes automatically at scope exit (RAII)
}
```

Parameters: `(maskOrChannel, zoneName, ...variadic_args)`
- No variadic args → `ProfileZoneStatic` (pre-registered, faster)
- With variadic args → `ProfileZoneDynamic` (printf formatting)

### Auto Function Name

```cpp
void myFunction() {
    CARB_PROFILE_FUNCTION(kProfilerMask);
    // zone name = function's pretty-printed name
}
```

### Manual Begin/End

```cpp
auto zoneId = CARB_PROFILE_BEGIN(kProfilerMask, "Manual zone");
// ... work ...
CARB_PROFILE_END(kProfilerMask, zoneId);
```

Prefer RAII style (`CARB_PROFILE_ZONE`) over manual begin/end.

### GPU Zones

Kit's RTX renderer uses query-based GPU zone capture:

```cpp
auto gpuCtx = CARB_PROFILE_CREATE_GPU_CONTEXT("Vulkan GPU", cpuTs, gpuTs, gpuPeriod, "vulkan");
CARB_PROFILE_GPU_QUERY_BEGIN(kProfilerMask, gpuCtx, queryId, "RTX Render Pass");
// ... submit GPU commands ...
CARB_PROFILE_GPU_QUERY_END(kProfilerMask, gpuCtx, queryId);
CARB_PROFILE_GPU_SET_QUERY_VALUE(kProfilerMask, gpuCtx, queryId, gpuTimestamp);
```

Enable GPU zones in Tracy:
```bash
--/profiler/gpu/tracyInject/enabled=true
--/rtx/addTileGpuAnnotations=true
```

## Python Profiling API

### Decorator (simplest)

```python
import carb.profiler

@carb.profiler.profile
def my_function():
    do_something()
```

### Manual begin/end

```python
carb.profiler.begin(1, "My Python operation")
# ... work ...
carb.profiler.end(1)
```

### Full IProfiler Interface

```python
profiler = carb.profiler.acquire_profiler_interface()

profiler.begin(mask, name)                      # zone start
profiler.end(mask)                              # zone end
profiler.set_capture_mask(mask) -> int          # returns previous mask
profiler.get_capture_mask() -> int
profiler.value_float(mask, value, name)         # Tracy Plot (float)
profiler.value_int(mask, value, name)           # Tracy Plot (int)
profiler.value_uint(mask, value, name)          # Tracy Plot (uint)
profiler.instant(mask, type, name)              # instant event
profiler.flow(mask, type, id, name)             # cross-thread flow
profiler.frame(mask, name)                      # frame marker
profiler.set_python_profiling_enabled(bool)     # toggle auto-profiling
```

Types:
```python
carb.profiler.InstantType.THREAD    # thread timeline
carb.profiler.InstantType.PROCESS   # process-wide timeline
carb.profiler.FlowType.BEGIN / END  # flow start/end
```

## Profiler Mask

64-bit bitmask controlling which zones are captured: `(zone_mask & capture_mask) != 0`

```cpp
constexpr uint64_t kCaptureMaskNone    = 0;              // nothing
constexpr uint64_t kCaptureMaskAll     = (uint64_t)-1;   // everything (default when no mask arg)
constexpr uint64_t kCaptureMaskDefault = uint64_t(1);    // bit 0
```

**Workflow:** Start with `--/app/profilerMask=1` (major spans only, minimal overhead). If more detail needed, remove the arg (defaults to ALL). Always start coarse, then zoom in.

## Profiler Channels

Higher-level abstraction over masks, toggled at runtime via settings:

### Declaring a Channel (C++)

```cpp
CARB_PROFILE_DECLARE_CHANNEL("myext.rendering", 1, true, g_myRenderingChannel);
CARB_PROFILE_ZONE(g_myRenderingChannel, "My rendering work");
```

### Runtime Toggle

```bash
--/profiler/channels/<name>/enabled=true|false
```

Commonly disabled during benchmarks (too noisy):
```bash
--/profiler/channels/carb.events/enabled=false
--/profiler/channels/carb.tasking/enabled=false
```

Memory channels:
```bash
--/profiler/channels/cpu.memory/enabled=true
--/profiler/channels/cpu.virtualmemory/enabled=true
--/profiler/channels/graphics.memory/enabled=true
```

## Tracy Plot Data (Numeric Metrics)

Record time-series values displayed as graphs in Tracy's Plot view.

### C++

```cpp
float gpuFrameTimeMs = 8.5f;
CARB_PROFILE_VALUE(gpuFrameTimeMs, 1, "GPU Frame Time (ms)");

int32_t triangleCount = 1500000;
CARB_PROFILE_VALUE(triangleCount, 1, "Triangle Count");
```

### Python

```python
profiler.value_float(1, 8.5, "GPU Frame Time (ms)")
profiler.value_int(1, 1500000, "Triangle Count")
profiler.value_uint(1, 4096, "GPU Memory (MB)")
```

## Event Annotations

### Instant Events

```cpp
// C++
CARB_PROFILE_EVENT(1, carb::profiler::InstantType::Thread, "Scene loading started");
CARB_PROFILE_EVENT(1, carb::profiler::InstantType::Process, "Phase transition: WARM -> BENCHMARK");
```

```python
# Python
profiler.instant(1, carb.profiler.InstantType.THREAD, "Scene loading started")
profiler.instant(1, carb.profiler.InstantType.PROCESS, "Phase transition")
```

Display as Tracy messages (recommended):
```bash
--/plugins/carb.profiler-tracy.plugin/instantEventsAsMessages=true
```

### command_macro.core Annotations

The `omni.kit.command_macro.core` extension auto-inserts `[command_macro][Measurement] Start/End - <tag>` events around benchmark measurements.

## Automatic Python Function Capture

Capture all Python function calls without per-function instrumentation:

```bash
export CARB_PROFILING_PYTHON=1
```

Or programmatically:
```python
profiler.set_python_profiling_enabled(True)
```

**Performance warning:** Significant overhead. Tracy file size ~4x larger (measured: 275MB → 1.2GB). **Never use during benchmark measurement** — only in the TRACY analysis phase.

## Profiling Backend Summary

| Backend | Plugin | Output | Best For |
|---------|--------|--------|----------|
| CPU (ChromeTrace) | `carb.profiler-cpu.plugin` | `.json`/`.gz` | Offline analysis, targeted captures |
| Tracy | `carb.profiler-tracy.plugin` | `.tracy` (live capture) | Real-time flame graphs, GPU context, stats |
| NVTX | `carb.profiler-nvtx.plugin` | `.nsys-rep` (via nsys) | GPU kernels, CUDA/Vulkan analysis |

CPU backend can be toggled on/off at runtime for targeted capture:
```python
profiler.set_capture_mask(1)   # start
# ... section to profile ...
profiler.set_capture_mask(0)   # stop
```
