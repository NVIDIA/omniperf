---
name: tracy-memory
description: Profile CPU and GPU memory allocations using Tracy in Kit-based applications. Covers LD_PRELOAD setup for liballocwrapper.so, Kit flags for CPU/GPU memory channels, capture binary isolation (unset LD_PRELOAD), strip test verification, and debug symbol requirements. Use when investigating memory leaks, allocation hotspots, or VRAM growth in Isaac Sim, Isaac Lab, or Kit apps via Tracy's Memory tab.
---

# Tracy Memory Profiling for Kit-Based Applications

Capture per-allocation CPU and GPU memory data in Tracy.
Prerequisite: Tracy capture setup (see `profiling` skill), `install-profilers` for binaries.

## Step 1: Environment Variables (Linux, required)

The `omni.cpumemorytracking` extension uses LD_PRELOAD to intercept malloc/free. Without it, Kit logs `Failed to load library: 'liballocwrapper.so'` and **zero memory events are captured**.

```bash
# Path varies by packman version
export LD_PRELOAD=~/.cache/packman/chk/allocmemwrapper/<version>/liballocwrapper.so
export TRACY_USE_LIB_UNWIND_FOR_BT=1   # libunwind-based backtrace
export TRACY_NO_SYS_TRACE=1            # reduce overhead
```

## Step 2: Kit Flags

```bash
# Base Tracy backend
--/app/profilerBackend=tracy
--/app/profileFromStart=true
--/profiler/enabled=true
--/plugins/carb.profiler-tracy.plugin/skipEventsOnShutdown=true
--/plugins/carb.profiler-tracy.plugin/memoryTraceStackCaptureDepth=16

# Reduce noise
--/profiler/channels/carb.tasking/enabled=false
--/profiler/channels/carb.events/enabled=false

# CPU memory tracking
--enable omni.cpumemorytracking
--/profiler/channels/cpu.memory/enabled=true
--/plugins/carb.cpumemorytracking.plugin/minCpuAllocSizeInBytesToTrack=1024

# GPU memory tracking
--/plugins/carb.memorytracking.plugin/enabled=true
--/profiler/channels/graphics.memory/enabled=true
```

## Step 3: Unset LD_PRELOAD Before Capture Binary

Only Kit should use the interposer. The Tracy capture binary must NOT inherit it:

```bash
# After launching Kit with LD_PRELOAD in background
unset LD_PRELOAD
./tracy/capture -o memtrace.tracy -f
```

## Step 4: Verify — Strip Test (MANDATORY)

Do not rely on Kit log lines alone. Verify actual memory data in the output:

```bash
# Strip memory events and compare file sizes
./tracy/update -s M memtrace.tracy memtrace_no_mem.tracy

# Good:   67 MB → 44 MB (~23 MB of memory data)
# Broken: 18 MB → 18 MB (zero memory data — LD_PRELOAD failed)
```

### Kit Log Verification

Must see both lines:
```
[carb.cpumemorytracking] Loaded shared library: 'liballocwrapper.so'
[carb.cpumemorytracking] set memory alloc/free callbacks successfully!
```

If you see `Failed to load library: 'liballocwrapper.so'` → LD_PRELOAD path is wrong. Stop and fix before re-running.

## Step 5: Analysis in Tracy

Open in Tracy GUI → **Memory** tab. A successful capture shows:
- Live counters: Active allocations, Memory usage
- Callstack tree grouping allocations by function
- Timeline showing allocation/free events

If Memory tab is empty: recheck LD_PRELOAD path and `cpu.memory` channel setting.

## Debug Symbols

`??` and `[unknown] ??:???` in allocation callstacks = **debug symbols missing**. Stripped release binaries only have addresses.

To see function names and source locations:
- Build with `RelWithDebInfo` or keep `.debug`/`.pdb` files
- Or use `debuginfod` / Tracy's symbol path setting (**Tools → Resolve symbol path**)

Without symbols: allocation size/count/lifetime analysis still works, but code-level attribution doesn't.

## Common Mistakes

- Missing `LD_PRELOAD=liballocwrapper.so` → extension starts but hooks never install
- Missing `TRACY_USE_LIB_UNWIND_FOR_BT=1` → poor backtrace quality
- Missing GPU memory: need both `carb.memorytracking.plugin/enabled=true` AND `graphics.memory` channel
- LD_PRELOAD bleeding into capture binary → corrupt capture
- Trusting Kit log text without strip test → false positive
