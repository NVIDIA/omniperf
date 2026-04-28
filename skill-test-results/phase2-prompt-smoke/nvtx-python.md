# Phase 2 Prompt Smoke: nvtx-python

**Prompt:** "Show a minimal Python NVTX function-range test."

## Validation

### Would it answer correctly?
✅ **YES** — The skill provides:
1. A complete `sitecustomize.py` script that sets up `sys.setprofile()` with NVTX push/pop ranges.
2. Environment variables for control (`NVTX_PROFILE_PYTHON=1`, include/exclude filters).
3. Usage examples with `nsys profile`.
4. Performance considerations (every call/return fires callback).
5. Alternative: nsys built-in `--python-functions-trace`.

A minimal test would be: install `nvtx`, create the sitecustomize.py, then run `NVTX_PROFILE_PYTHON=1 nsys profile python my_script.py`.

### Adjacent skill redirects
✅ Implicitly references nsys (from `install-profilers`).
✅ Distinguishes itself from Kit-based `CARB_PROFILING_PYTHON` (which uses Carbonite, covered in `profiling-api`).

### Command safety
| Command | Gated? | Notes |
|---------|--------|-------|
| `uv pip install nvtx` | Package install | Requires user approval |
| `cat > sitecustomize.py` | File write to site-packages | Modifies Python env — noted |
| `nsys profile` | Starts profiling | Requires workload |

### Dry-run suitability
✅ The sitecustomize.py content can be shown as a minimal example without executing. The environment variable table is self-documenting.

### Warnings
⚠️ **Minor:** Writing to `site-packages/sitecustomize.py` could conflict with existing customizations. The skill should note "check if sitecustomize.py already exists" or use an append/conditional approach.

⚠️ **Minor:** No explicit mention of removing/disabling the hook after profiling (deleting the file or unsetting env var). The "To disable: unset or delete" note at the end partially covers this.

## Result: ✅ PASS

Clear, minimal, and correctly scoped for non-Kit Python NVTX profiling.
