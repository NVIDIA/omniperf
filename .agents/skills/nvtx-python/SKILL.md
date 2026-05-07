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

# Resolve this skill's directory, then put its scripts/ directory on PYTHONPATH.
# From this repository, the default below points at the bundled helper.
NVTX_SKILL_DIR="${NVTX_SKILL_DIR:-$PWD/.agents/skills/nvtx-python}"
test -f "$NVTX_SKILL_DIR/scripts/sitecustomize.py"
export PYTHONPATH="$NVTX_SKILL_DIR/scripts:${PYTHONPATH:-}"
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
NVTX_SKILL_DIR="${NVTX_SKILL_DIR:-$PWD/.agents/skills/nvtx-python}"
PYTHONPATH="$NVTX_SKILL_DIR/scripts:${PYTHONPATH:-}" \
NVTX_PROFILE_PYTHON=1 \
nsys profile -t nvtx,cuda,osrt \
uv run python scripts/reinforcement_learning/skrl/train.py \
  --task=Isaac-Velocity-Flat-Anymal-C-v0 --num_envs=1024 --max_iterations=10

# Capture specific modules only (recommended — reduces overhead)
NVTX_SKILL_DIR="${NVTX_SKILL_DIR:-$PWD/.agents/skills/nvtx-python}"
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

## Caveat: Isaac Lab / Kit-based hosts clobber `sys.setprofile`

Isaac Lab 3.0+ standalone *does* boot Kit/Carb under the hood via `AppLauncher`. Just running `from isaaclab.app import AppLauncher` (or any import that transitively pulls `carb` / `isaacsim`) registers Carb's own Python profile callback during module load, **silently overwriting the hook this skill installed at interpreter startup**. The resulting `.nsys-rep` then shows Python NVTX only for the brief window between interpreter startup and the first Carb-pulling import — typically just `argparse`, then nothing.

**Fix:** call `sitecustomize.install()` after the import to re-arm. `install()` is idempotent, re-reads `NVTX_PROFILE_INCLUDE` / `NVTX_PROFILE_EXCLUDE` each call, and re-installs both `sys.setprofile` and `threading.setprofile`.

```python
import sys
print(f"[NVTX] before AppLauncher: {sys.getprofile()!r}", flush=True)  # likely None
app_launcher = AppLauncher(args_cli)
simulation_app = app_launcher.app
print(f"[NVTX] after AppLauncher:  {sys.getprofile()!r}", flush=True)  # still None

import sitecustomize
sitecustomize.install()
print(f"[NVTX] re-installed:       {sys.getprofile()!r}", flush=True)  # callback restored
```

The probes are how you confirm the issue and the fix in one run. Drop them once verified.

### Limitations even after re-install

- `sys.setprofile` is **per-thread**. `threading.setprofile` only catches threads created via Python's `threading` module — Kit / PhysX / Hydra / Fabric / TBB native threads stay invisible. Most of `env.step()` runs in C++ on those threads, so even with the hook re-armed you'll see relatively few Python NVTX zones during the step loop.
- Tracing every module floods the trace and can swamp nsys's NVTX backend; **always set `NVTX_PROFILE_INCLUDE`** to your own packages (e.g. `simulation,isaaclab.envs,isaaclab_tasks`) for Isaac Lab workloads.
- For native-side coverage of Kit/PhysX/Hydra, use `CARB_PROFILING_PYTHON=1` + Carb's NVTX backend (see `profiling` skill) instead of, or alongside, this skill.
- For a clean, low-overhead view of specific hot paths, drop the auto-tracer entirely and decorate the functions you care about with `@nvtx.annotate` (`env.step`, IK solve, observation manager, camera readout).

## Alternative: nsys Built-in Python Tracing

If you know exactly which modules/functions to trace, nsys has a built-in option:
```bash
nsys profile --python-functions-trace=... <command>
```
See the [Nsight Systems User Guide](https://docs.nvidia.com/nsight-systems/UserGuide/index.html) for details.
