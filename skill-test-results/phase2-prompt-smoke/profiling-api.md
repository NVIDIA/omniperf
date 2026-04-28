# Phase 2 Prompt Smoke: profiling-api

**Prompt:** "Show minimal C++ and Python profiling-zone examples for Kit."

## Validation

### Would it answer correctly?
✅ **YES** — The skill provides exactly this:

**C++ examples:**
- `CARB_PROFILE_ZONE(kProfilerMask, "My C++ function")` — scope-based (most common)
- `CARB_PROFILE_FUNCTION(kProfilerMask)` — auto function name
- Manual begin/end pattern
- GPU zones with query-based capture

**Python examples:**
- `@carb.profiler.profile` decorator (simplest)
- `carb.profiler.begin(1, "name")` / `carb.profiler.end(1)` manual API
- Full `IProfiler` interface with value_float, instant, flow, frame methods

Additionally covers: profiler masks, channels, Tracy plots, event annotations, CARB_PROFILING_PYTHON auto-capture.

### Adjacent skill redirects
✅ Clear NOT-for: "NOT for capturing traces (use profiling skill) or analyzing them (use nsys-analyze)."
✅ References Tracy/NVTX backends for context.

### Command safety
| Command | Gated? | Notes |
|---------|--------|-------|
| All content is code examples | N/A | Informational only |
| `export CARB_PROFILING_PYTHON=1` | Env var set | Non-destructive |
| Kit args (`--/...`) | Config flags | Applied at launch time |

### Dry-run suitability
✅ Entirely reference material. No executable commands to gate — it's all code snippets and configuration.

## Result: ✅ PASS

Comprehensive API reference. Well-organized with clear categories (C++, Python, masks, channels, plots, annotations). No safety concerns.
