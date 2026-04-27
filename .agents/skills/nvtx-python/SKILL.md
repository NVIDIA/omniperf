---
name: nvtx-python
description: Profile Python functions with NVTX in non-Kit environments (Isaac Lab 3.0+ standalone, any Python app without Carbonite). Sets up sitecustomize.py with sys.setprofile hook, NVTX push/pop ranges, module include/exclude filtering, and Nsight Systems integration. Use when CARB_PROFILING_PYTHON doesn't work (no Kit/Carbonite runtime), when profiling standalone Isaac Lab scripts, or when you need per-function Python tracing in nsys captures outside Kit.
---

# NVTX Python Function Profiling (Non-Kit Environments)

For Isaac Lab 3.0+ standalone mode and other Python apps without Kit/Carbonite, `CARB_PROFILING_PYTHON` doesn't work. This skill sets up a `sys.setprofile()` hook with NVTX ranges instead.

## Setup

```bash
# From the Isaac Lab directory (or any Python project with uv/pip)

# 1. Install nvtx
uv pip install nvtx

# 2. Create sitecustomize.py (auto-loaded at interpreter startup)
SITE_PACKAGES=$(uv run python -c "import site; print(site.getsitepackages()[0])")
cat > "$SITE_PACKAGES/sitecustomize.py" << 'PYEOF'
import os
if os.environ.get('NVTX_PROFILE_PYTHON') == '1':
    import sys
    try:
        import threading, nvtx
        _inc = tuple(filter(None, os.environ.get('NVTX_PROFILE_INCLUDE', '').split(',')))
        _exc = tuple(filter(None, os.environ.get('NVTX_PROFILE_EXCLUDE', 'importlib').split(',')))
        _cache = {}
        _tls = threading.local()

        def _cb(f, ev, a):
            if ev == 'call':
                m = f.f_globals.get('__name__', '')
                r = _cache.get(m)
                if r is None:
                    if any(m.startswith(e) for e in _exc):
                        r = False
                    else:
                        r = not _inc or any(m.startswith(i) for i in _inc)
                    _cache[m] = r
                if r:
                    if not hasattr(_tls, 'd'): _tls.d = 0
                    nvtx.push_range(f"{m}.{f.f_code.co_name}")
                    _tls.d += 1
            elif ev == 'return' and hasattr(_tls, 'd') and _tls.d > 0:
                nvtx.pop_range()
                _tls.d -= 1
            return _cb

        sys.setprofile(_cb)
        threading.setprofile(_cb)
        print(f"[NVTX] Python profiling enabled (include={_inc or 'all'}, exclude={_exc})", file=sys.stderr)
    except Exception as e:
        print(f"[NVTX] Failed: {e}", file=sys.stderr)
PYEOF
echo "Created: $SITE_PACKAGES/sitecustomize.py"
```

## Environment Variables

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `NVTX_PROFILE_PYTHON` | Set to `1` to enable | (disabled) | `1` |
| `NVTX_PROFILE_INCLUDE` | Module prefixes to trace (comma-separated). Empty = all. | (all) | `isaaclab,skrl,torch` |
| `NVTX_PROFILE_EXCLUDE` | Module prefixes to exclude (comma-separated). | `importlib` | `importlib,threading,nvtx` |

## Usage with Nsight Systems

```bash
# Capture all Python modules
NVTX_PROFILE_PYTHON=1 \
nsys profile -t nvtx,cuda,osrt \
uv run python scripts/reinforcement_learning/skrl/train.py \
  --task=Isaac-Velocity-Flat-Anymal-C-v0 --num_envs=1024 --max_iterations=10

# Capture specific modules only (recommended — reduces overhead)
NVTX_PROFILE_PYTHON=1 NVTX_PROFILE_INCLUDE=isaaclab,skrl \
nsys profile -t nvtx,cuda,osrt \
uv run python scripts/reinforcement_learning/skrl/train.py \
  --task=Isaac-Velocity-Flat-Anymal-C-v0 --num_envs=1024 --max_iterations=10
```

## Performance Considerations

- **Every function call/return fires a callback** — significant overhead when tracing all modules
- Use `NVTX_PROFILE_INCLUDE` to limit scope to modules of interest
- To disable: unset `NVTX_PROFILE_PYTHON` or delete `sitecustomize.py`

## Alternative: nsys Built-in Python Tracing

If you know exactly which modules/functions to trace, nsys has a built-in option:
```bash
nsys profile --python-functions-trace=... <command>
```
See the [Nsight Systems User Guide](https://docs.nvidia.com/nsight-systems/UserGuide/index.html) for details.
