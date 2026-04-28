---
name: benchmark-isaacsim
description: Run Isaac Sim benchmark scripts and interpret benchmark outputs. Covers camera, SDG, scene-loading, robot, lidar/radar/sensor benchmark scripts, common parameters, output files, and benchmark-specific pitfalls. Use when the user asks to run or compare Isaac Sim benchmark results. NOT for initial bottleneck triage (use diagnose-perf), profiling capture (use profiling), trace analysis (use nsys-analyze), or applying performance fixes (use perf-tuning).
---

# Isaac Sim Benchmarking

> **Parameter references may be outdated.** Always verify with `./python.sh <script> --help`.
> For profiling details (Tracy, Nsight), see the `profiling` skill.

## Setup

See the `install-isaacsim` skill for installation (pip, source build, Docker).

### Discover Existing Isaac Sim Installation

Before running any benchmark, locate the Isaac Sim Python entry point:

```bash
# Source build or pip-env helper scripts: find python.sh / isaac-sim.sh
find /home /opt /data -maxdepth 5 \( -name python.sh -o -name isaac-sim.sh \) 2>/dev/null | head -20

# Pip install: check the currently active Python env only
python -c "import isaacsim; from isaacsim.simulation_app import SimulationApp; print('pip env OK')" \
  2>/dev/null || echo "Not usable in current Python env"
```

If neither is found, Isaac Sim must be installed first (see `install-isaacsim`). If Isaac Sim is installed in a venv, activate that venv before checking; a system `python3` import failure does not rule out an isolated install.

Also verify the benchmark scripts exist. A pip Isaac Sim install can provide `SimulationApp` and benchmark services without shipping the source-tree `standalone_examples/benchmarks/*.py` scripts:

```bash
# Source checkout / source build layout
find /path/to/IsaacSim -path '*/standalone_examples/benchmarks/*.py' 2>/dev/null | head -20

# Pip installs may include benchmark extension tests but not runnable standalone scripts.
python - <<'PY'
import pathlib, site
for root in site.getsitepackages():
    hits = list(pathlib.Path(root).glob('**/standalone_examples/benchmarks/*.py'))
    if hits:
        print('\n'.join(map(str, hits[:20])))
PY
```

Do not proceed with Isaac Sim standalone benchmarks until both the runtime and the benchmark script path are available. If only pip runtime is available, use Isaac Lab benchmarks or install/clone an Isaac Sim source tree that includes `standalone_examples/benchmarks`.

## Before Running Any Benchmark

1. **Use a WARM run for headline FPS/frametime** — see the COLD/WARM/TRACY method in the `profiling` skill.
2. **Set CPU governor to performance when the host allows it** — see `perf-tuning` skill. In containers where governor control is unavailable, record that limitation instead of trying privileged changes.
3. **Set Nucleus auth** if using Nucleus-hosted assets — see `install-isaacsim` skill.
4. **Do not patch Isaac Sim shutdown by default.** If Tracy shutdown hangs after outputs are complete, use the scoped last-resort guidance in the `profiling` skill.

## Benchmark Scripts

All in `standalone_examples/benchmarks/`. Run via `./python.sh <script> [args]`.

> **Packaging note:** These standalone scripts are available in source checkouts/source builds and some container/archive layouts. Pip installs can provide the Isaac Sim runtime without this directory. If `standalone_examples/benchmarks` is missing, do not improvise paths; clone/use a source layout, or switch to Isaac Lab benchmarks for local validation.

| Script | What it measures | Key params |
|--------|-----------------|------------|
| `benchmark_camera.py` | Multi-camera rendering FPS | `--num-cameras`, `--resolution W H` |
| `benchmark_sdg.py` | Synthetic data generation throughput | `--num-cameras`, `--annotators`, `--asset-count` |
| `benchmark_scene_loading.py` | Scene load time + FPS | `--env-url` (required) |
| `benchmark_robots_o3dyn.py` | O3Dyn robot physics | `--num-robots`, `--physics` |
| `benchmark_robots_humanoid.py` | Humanoid physics | `--num-robots`, `--physics` |
| `benchmark_robots_nova_carter.py` | Nova Carter (no ROS) | `--num-robots` |
| `benchmark_robots_nova_carter_ros2.py` | Nova Carter + ROS2 | `--num-robots`, `--enable-3d-lidar`, `--enable-hawks` |
| `benchmark_robots_evobot.py` | Evobot multi-phase | `--num-robots 1 10 20` |
| `benchmark_robots_ur10.py` | UR10 manipulation | `--num-robots`, `--device` |
| `benchmark_core_world.py` | Core world cloning | `--num-envs` (no `--num-frames`) |
| `benchmark_rtx_lidar.py` | RTX lidar sensor | `--num-sensors`, `--lidar-type` |
| `benchmark_physx_lidar.py` | PhysX lidar sensor | `--num-sensors` |
| `benchmark_rtx_radar.py` | RTX radar sensor | `--num-sensors` |
| `benchmark_single_view_depth_sensor.py` | Single-view depth camera | `--num-cameras`, `--resolution W H` |
| `benchmark_rtx_lidar_ros2_pcl_metadata.py` | RTX lidar + ROS2 PCL (v6+) | `--num-sensors`, `--metadata` |
| `benchmark_nucleus_kpis.py` | Nucleus KPIs | (none) |

**Common params:** `--num-frames` (default 600), `--num-gpus`, `--backend-type`, `--viewport-updates`, `--non-headless`

**Output control Kit args** (append to any benchmark command):
```
--/exts/isaacsim.benchmark.services/metrics/metrics_output_folder=<output_dir>
--/log/file=<output_dir>/kit.log
```

## Critical Gotchas

### Parameter format: HYPHENS, not underscores
Isaac Sim uses **hyphens** in parameter names. Underscores are **silently ignored** by argparse:
```
CORRECT: --num-cameras 8 --num-gpus 1 --num-frames 600
WRONG:   --num_cameras 8  (silently uses default=1!)
```
Always verify result JSON to confirm params were applied.

### Headless and viewport validation
When comparing benchmark outputs, record whether the run used `--non-headless`, `--viewport-updates`, render products, or camera sensors. Do not change viewport code or settings from this skill; if extra viewport work appears to affect results, hand off to `perf-tuning`.

### JWT token expiry = silent black renders
Expired `OMNI_PASS` tokens cause silent asset loading failure. See `install-isaacsim` skill for the expiry check command.

### carb.log_warn() doesn't go to stdout
Monitor progress by polling for result JSON files, not watching stdout.
Kit log: `~/.nvidia-omniverse/logs/Kit/isaacsim*/kit.log` or `--/log/file=/tmp/kit.log`.

### Hung processes after results are written
If `kpis_*.json` and `*.tracy` exist with non-zero size and the process has not exited after 2 minutes with no new output, follow the `profiling` skill's guide-aligned shutdown handling and force-kill the app and capture processes.

## Optimization Handoff

If results indicate per-camera viewport overhead, too many render products, default viewport work in headless mode, or poor multi-GPU scaling, do not apply fixes here. Summarize the benchmark evidence and use `perf-tuning` for the configuration changes.

## Output Files

- `kpis_benchmark_<name>.json` — benchmark KPIs (main results)
- `kit.log` — execution log (if `--/log/file=` is set)
- `*.tracy` — Tracy profiling trace (only with Tracy args)
- `*.nsys-rep` — Nsight profiling trace (only with nsys)

> **Note:** `benchmark_result.json` and `startup_*.json` are NOT produced by default
> in v5.x/v6.x. The primary results file is `kpis_benchmark_<name>.json`.

---
