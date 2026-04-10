---
name: benchmark-isaaclab
description: Run Isaac Lab benchmarks. Covers setup, RL training, environment step FPS, and convergence testing. Use when the user asks to benchmark Isaac Lab or test RL performance.
---

# Isaac Lab Benchmarking

> **Parameter references may be outdated.** Always verify with `./isaaclab.sh -p <script> --help`.
> For profiling details (Tracy, Nsight, CPU governor), see the `profiling` skill.
> For Isaac Sim setup, see the `benchmark-isaacsim` skill.

## Setup

**Repo:** https://github.com/isaac-sim/IsaacLab.git
**Requires:** Isaac Sim + Miniconda

```bash
# 1. Install Isaac Sim first (see benchmark-isaacsim skill)
# 2. Clone Isaac Lab
git clone https://github.com/isaac-sim/IsaacLab.git
cd IsaacLab && git checkout develop

# 3. Link Isaac Sim
ln -s <ISAAC_SIM_PATH> _isaac_sim

# 4. Create conda env and install
./isaaclab.sh -c _isaaclab_env
./isaaclab.sh -i
```

**Activate:**
```bash
source ~/miniconda3/etc/profile.d/conda.sh
conda activate _isaaclab_env
```

## Before Running Any Benchmark

1. **Apply the `os._exit(0)` patch** on Isaac Sim — see `profiling` skill
2. **Set CPU governor to performance** — see `profiling` skill

## Benchmark Scripts

All in `scripts/benchmarks/`. Run via `./isaaclab.sh -p scripts/benchmarks/<script>.py`.

| Script | What it measures | Key params |
|--------|-----------------|------------|
| `benchmark_non_rl.py` | Environment step FPS (most common) | `--task`, `--num_envs`, `--num_frames` |
| `benchmark_rlgames.py` | RL-Games training throughput | `--task`, `--num_envs`, `--max_iterations` |
| `benchmark_rsl_rl.py` | RSL-RL training throughput | `--task`, `--num_envs`, `--max_iterations` |
| `benchmark_cameras.py` | Camera system FPS + autotune | `--num_tiled_cameras`, `--height`, `--width`, `--autotune` |
| `benchmark_load_robot.py` | Robot loading time | `--num_envs`, `--robot` |
| `benchmark_lazy_export.py` | Lazy export/import speed | `--iterations` |
| `benchmark_view_comparison.py` | XformPrimView vs PhysX | `--num_envs`, `--num_iterations` |

**Common params:** `--headless`, `--device`, `--enable_cameras`, `--benchmark_backend`, `--output_path`, `--distributed`

### Batch suites
```bash
bash scripts/benchmarks/run_training_benchmarks.sh    # RSL-RL, 500 iters
bash scripts/benchmarks/run_non_rl_benchmarks.sh      # non-RL, various env counts
bash scripts/benchmarks/run_physx_benchmarks.sh        # PhysX assets
```

## Critical Gotcha: Parameter Format

Isaac Lab uses **UNDERSCORES** (standard argparse). Isaac Sim uses **HYPHENS**.
```
Isaac Lab:  --num_envs 4096  --num_frames 100  --enable_cameras
Isaac Sim:  --num-cameras 8  --num-gpus 1      --num-frames 600
```
Mixing them up is a common source of silent misconfiguration.

## Common Tasks and Env Counts

**Camera tasks** (add `--enable_cameras`):
- `Isaac-Cartpole-RGB-Camera-Direct-v0`: 512-4096 envs

**Classic physics** (4096 / 8192 / 16384 envs):
- `Isaac-Ant-Direct-v0`, `Isaac-Cartpole-Direct-v0`, `Isaac-Humanoid-Direct-v0`

**Locomotion** (4096 envs):
- `Isaac-Velocity-Rough-Anymal-C-v0`, `Isaac-Velocity-Rough-H1-v0`, `Isaac-Velocity-Rough-G1-v0`

**Manipulation** (128-8192 envs):
- `Isaac-Reach-Franka-v0`, `Isaac-Factory-GearMesh-Direct-v0`

## Output Files

- `kpis_*.json` — KPI results
- `benchmark_result.json` — final results
- `kit.log` — execution log
- `*.tracy` / `*.nsys-rep` — profiling traces

### JSON structure
Top-level keys: `startup`, `runtime` (step times, FPS, GPU%), `train` (rewards — RL only), `metadata` (task, hardware)

---
