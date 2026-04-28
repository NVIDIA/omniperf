---
name: nvtx-python
description: Profile Python functions with NVTX in non-Kit environments (Isaac Lab 3.0+ standalone, any Python app without Carbonite). Uses a bundled PYTHONPATH-scoped sitecustomize.py with sys.setprofile hook, NVTX push/pop ranges, module include/exclude filtering, and Nsight Systems integration. Use when CARB_PROFILING_PYTHON doesn't work (no Kit/Carbonite runtime), when profiling standalone Isaac Lab scripts, or when you need per-function Python tracing in nsys captures outside Kit.
---

# NVTX Python Function Profiling (Non-Kit Environments)

For Isaac Lab 3.0+ standalone mode and other Python apps without Kit/Carbonite, `CARB_PROFILING_PYTHON` doesn't work. This skill uses the bundled `scripts/sitecustomize.py` helper to install a `sys.setprofile()` hook with NVTX ranges.

Do not write into an environment's existing `sitecustomize.py`. Load the bundled helper with `PYTHONPATH` so disabling it is just unsetting `PYTHONPATH` or `NVTX_PROFILE_PYTHON`.

## Setup

```bash
# From the Isaac Lab directory (or any Python project with uv/pip)
uv pip install nvtx

# Resolve this skill's scripts/ directory and put it on PYTHONPATH.
# The sitecustomize.py bundled here is PYTHONPATH-scoped: it activates only when
# PYTHONPATH includes this directory. It does NOT overwrite the environment's
# site-packages/sitecustomize.py. To disable, simply unset PYTHONPATH or
# remove this entry.
NVTX_SKILL_DIR="$(find "$PWD" -path '*/.agents/skills/nvtx-python/scripts/sitecustomize.py' -print -quit | xargs -r dirname | xargs -r dirname)"
# Or set it explicitly to wherever the skill is installed:
# NVTX_SKILL_DIR=/path/to/omniperf/.agents/skills/nvtx-python
[ -n "$NVTX_SKILL_DIR" ] || { echo "Set NVTX_SKILL_DIR to .agents/skills/nvtx-python"; exit 1; }
export PYTHONPATH="$NVTX_SKILL_DIR/scripts:${PYTHONPATH:-}"
```

> **Warning:** Do not copy `sitecustomize.py` into `site-packages/` — that would
> overwrite any existing `sitecustomize.py` (breaking tools like coverage.py,
> virtualenv hooks, etc.). Always use the `PYTHONPATH` approach above.

## Environment Variables

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `NVTX_PROFILE_PYTHON` | Set to `1` to enable | (disabled) | `1` |
| `NVTX_PROFILE_INCLUDE` | Module prefixes to trace (comma-separated). Empty = all. | (all) | `isaaclab,skrl,torch` |
| `NVTX_PROFILE_EXCLUDE` | Module prefixes to exclude (comma-separated). | `importlib` | `importlib,threading,nvtx` |

## Usage with Nsight Systems

```bash
# Capture all Python modules
# Set NVTX_SKILL_DIR to the nvtx-python skill directory (see Setup above)
PYTHONPATH="$NVTX_SKILL_DIR/scripts:${PYTHONPATH:-}" \
NVTX_PROFILE_PYTHON=1 \
nsys profile -t nvtx,cuda,osrt \
uv run python scripts/reinforcement_learning/skrl/train.py \
  --task=Isaac-Velocity-Flat-Anymal-C-v0 --num_envs=1024 --max_iterations=10

# Capture specific modules only (recommended — reduces overhead)
PYTHONPATH="$NVTX_SKILL_DIR/scripts:${PYTHONPATH:-}" \
NVTX_PROFILE_PYTHON=1 NVTX_PROFILE_INCLUDE=isaaclab,skrl \
nsys profile -t nvtx,cuda,osrt \
uv run python scripts/reinforcement_learning/skrl/train.py \
  --task=Isaac-Velocity-Flat-Anymal-C-v0 --num_envs=1024 --max_iterations=10
```

## Performance Considerations

- **Every function call/return fires a callback** — significant overhead when tracing all modules
- Use `NVTX_PROFILE_INCLUDE` to limit scope to modules of interest
- To disable: unset `NVTX_PROFILE_PYTHON` or remove the skill's `scripts/` directory from `PYTHONPATH`

## Alternative: nsys Built-in Python Tracing

If you know exactly which modules/functions to trace, nsys has a built-in option:
```bash
nsys profile --python-functions-trace=... <command>
```
See the [Nsight Systems User Guide](https://docs.nvidia.com/nsight-systems/UserGuide/index.html) for details.
