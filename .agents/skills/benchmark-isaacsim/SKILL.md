---
name: benchmark-isaacsim
description: Run Isaac Sim benchmarks. Covers setup, known pitfalls, and performance optimization tips. Use when the user asks to benchmark Isaac Sim, compare versions, or test performance.
---

# Isaac Sim Benchmarking

> **Parameter references may be outdated.** Always verify with `./python.sh <script> --help`.
> For profiling details (Tracy, Nsight, CPU governor), see the `profiling` skill.

## Setup

**Public repo:** https://github.com/isaac-sim/IsaacSim

```bash
# Pip install (quickest)
pip install isaacsim

# Or source build
git clone https://github.com/isaac-sim/IsaacSim.git
cd IsaacSim
git checkout develop
pip install -e .       # or ./build.sh -xr (requires Docker)
```

**Branch convention:** `develop` (latest), `release/*` (stable), version tags.

**Docker:** Source build requires Docker by default. Install with `sudo apt-get install -y docker.io` if missing. Use `./build.sh -xr --no-docker` as fallback.

## Before Running Any Benchmark

1. **Apply the `os._exit(0)` patch** — see `profiling` skill. Prevents shutdown hang.
2. **Set CPU governor to performance** — see `profiling` skill.
3. **Set Nucleus auth** (if using Nucleus-hosted assets):
   ```bash
   export OMNI_USER='$omni-api-token'
   export OMNI_PASS='<YOUR-API-TOKEN>'
   ```
   Some benchmarks use local assets and don't need this.

## Benchmark Scripts

All in `standalone_examples/benchmarks/`. Run via `./python.sh <script> [args]`.

| Script | What it measures | Key params |
|--------|-----------------|------------|
| `benchmark_camera.py` | Multi-camera rendering FPS | `--num-cameras`, `--resolution W H` |
| `benchmark_sdg.py` | Synthetic data generation throughput | `--num-cameras`, `--annotators`, `--asset-count` |
| `benchmark_scene_loading.py` | Scene load time + FPS | `--env-url` (required) |
| `benchmark_robots_o3dyn.py` | O3Dyn robot physics | `--num-robots`, `--physics` |
| `benchmark_robots_humanoid.py` | Humanoid physics | `--num-robots` |
| `benchmark_robots_nova_carter.py` | Nova Carter (no ROS) | `--num-robots` |
| `benchmark_robots_nova_carter_ros2.py` | Nova Carter + ROS2 | `--num-robots`, `--enable-3d-lidar`, `--enable-hawks` |
| `benchmark_robots_evobot.py` | Evobot multi-phase | `--num-robots 1 10 20` |
| `benchmark_robots_ur10.py` | UR10 manipulation | `--num-robots`, `--device` |
| `benchmark_core_world.py` | Core world cloning | `--num-envs` |
| `benchmark_rtx_lidar.py` | RTX lidar sensor | `--num-sensors`, `--lidar-type` |
| `benchmark_nucleus_kpis.py` | Nucleus KPIs | (none) |

**Common params:** `--num-frames` (default 600), `--num-gpus`, `--backend-type`, `--viewport-updates`, `--non-headless`

## Critical Gotchas

### Parameter format: HYPHENS, not underscores
Isaac Sim uses **hyphens** in parameter names. Underscores are **silently ignored** by argparse:
```
CORRECT: --num-cameras 8 --num-gpus 1 --num-frames 600
WRONG:   --num_cameras 8  (silently uses default=1!)
```
Always verify result JSON to confirm params were applied.

### Headless viewport wastes ~35% frame time
Even with `headless=True`, Kit creates a default viewport. Destroy it after sensor setup:
```python
import omni.kit.viewport.utility as vp_util
import carb
vp_window = vp_util.get_active_viewport_window()
if vp_window:
    vp_window.visible = False
    vp_api = vp_util.get_active_viewport()
    if vp_api:
        vp_api.updates_enabled = False
    vp_window.destroy()
settings = carb.settings.get_settings()
settings.set("/app/hydraEngine/waitIdle", False)
settings.set("/app/renderer/skipWhileMinimized", True)
```

### JWT token expiry = silent black renders
Expired `OMNI_PASS` tokens cause scenes to load with missing materials (all-black).
```bash
echo "$OMNI_PASS" | cut -d. -f2 | base64 -d 2>/dev/null | python3 -c "
import json, sys; from datetime import datetime; d = json.load(sys.stdin)
print(f'Expires: {datetime.fromtimestamp(d.get(\"exp\", 0))}')"
```

### carb.log_warn() doesn't go to stdout
Monitor progress by polling for result JSON files, not watching stdout.
Kit log: `~/.nvidia-omniverse/logs/Kit/isaacsim*/kit.log` or `--/log/file=/tmp/kit.log`.

### Hung processes after results are written
If kpis_*.json and *.tracy exist with non-zero size and the process hasn't exited after 2 min, it's hung. `kill -9` it.

## Multi-Camera Optimization

```
Creating viewports per camera?
├─ YES → Remove per-camera viewports (keep render_products only) → +50-60% FPS
└─ NO → Each camera a separate render_product?
         ├─ YES → Replace with TiledCameraSensor (N RPs → 1) → +150-200% FPS
         └─ NO → Already tiled → destroy default viewport → +7-11% FPS
```

### TiledCameraSensor
```python
from isaacsim.sensors.experimental.camera import TiledCameraSensor
sensor = TiledCameraSensor(
    camera_paths,          # List[str]
    resolution=(H, W),     # NOTE: (Height, Width) — NOT (W, H)
    annotators=["rgb"],
)
data, info = sensor.get_data("rgb")  # warp array on GPU, shape (N, H, W, C)
```

## Output Files

- `startup_*.json`, `kpis_*.json` — benchmark KPIs
- `benchmark_result.json` — final results
- `kit.log` — execution log
- `*.tracy` / `*.nsys-rep` — profiling traces

---
