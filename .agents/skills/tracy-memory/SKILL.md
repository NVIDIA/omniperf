---
name: tracy-memory
description: Profile CPU and GPU memory allocations using Tracy in Kit-based applications after Tracy capture tooling is installed. Covers LD_PRELOAD setup for liballocwrapper.so, Kit memory-channel flags, capture binary isolation (unset LD_PRELOAD), tracy-update strip-test verification, Tracy Memory tab analysis, and debug symbol requirements. Use when investigating memory leaks, allocation hotspots, or VRAM growth in Isaac Sim, Isaac Lab, or Kit apps. Requires profiling capture setup plus install-profilers. NOT for generic trace capture (use profiling) or non-memory trace analysis (use nsys-analyze).
---

# Tracy Memory Profiling for Kit-Based Applications

Capture per-allocation CPU and GPU memory data in Tracy.
Prerequisite: Tracy capture setup (see `profiling` skill), `install-profilers` for binaries.

## Step 1: Environment Variables (Linux, required)

The `omni.cpumemorytracking` extension uses LD_PRELOAD to intercept malloc/free. Without it, Kit logs `Failed to load library: 'liballocwrapper.so'` and **zero memory events are captured**. Pip Isaac Sim installs may not ship this Packman/source-Kit library; if discovery fails, stop and install/use a Kit or Isaac Sim package that includes it.

```bash
# Path varies by packman/source build version. Discover it instead of guessing <version>.
ALLOC_WRAPPER=$(find ~/.cache/packman -name liballocwrapper.so 2>/dev/null | head -1)
if [ -z "$ALLOC_WRAPPER" ]; then
  ALLOC_WRAPPER=$(find /home /opt /data -name liballocwrapper.so 2>/dev/null | head -1)
fi
[ -n "$ALLOC_WRAPPER" ] || { echo "liballocwrapper.so not found; memory tracing blocked"; exit 1; }

export LD_PRELOAD="$ALLOC_WRAPPER"
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
TRACY_CAPTURE_BIN=$(command -v tracy-capture || command -v capture || command -v capture-release)
[ -n "$TRACY_CAPTURE_BIN" ] || { echo "Missing tracy-capture/capture/capture-release binary"; exit 1; }
"$TRACY_CAPTURE_BIN" -o memtrace.tracy -f -p "${TRACY_PORT:-8086}"
```

## Step 4: Verify — Strip Test (MANDATORY)

Do not rely on Kit log lines alone. Verify actual memory data in the output:

```bash
# Strip memory events and compare file sizes.
# The utility is named `update` in Tracy builds; use your built Tracy tools dir if it is not on PATH.
TRACY_UPDATE_BIN=$(command -v tracy-update || command -v update)
[ -n "$TRACY_UPDATE_BIN" ] || { echo "Missing tracy-update/update binary; see install-profilers"; exit 1; }
"$TRACY_UPDATE_BIN" -s M memtrace.tracy memtrace_no_mem.tracy

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
