---
name: benchmark-isaaclab
description: Run Isaac Lab benchmark scripts and interpret their outputs. Covers RL training throughput, non-RL environment step FPS, camera/load/startup benchmarks, batch suites, parameter gotchas, output files, and JSON result structure. Use when the user asks to run or compare Isaac Lab benchmarks. NOT for RL convergence or policy-quality validation, profiling capture (use profiling), trace analysis (use nsys-analyze), or applying performance fixes (use perf-tuning).
---

# Isaac Lab Benchmarking

> **Parameter references may be outdated.** Always verify with `./isaaclab.sh -p <script> --help`.
> For profiling details (Tracy, Nsight), see the `profiling` skill.
> For installation, see the `install-isaaclab` skill.

## Setup

See the `install-isaaclab` skill for installation (clone, conda env, Isaac Sim linking).

### Discover Existing Isaac Lab Installation

Before running any benchmark, locate the Isaac Lab entry point:

```bash
# Find isaaclab.sh
find /home /opt /data -maxdepth 5 -name isaaclab.sh 2>/dev/null | head -20

# If found, activate the intended conda/uv/venv first, then verify it works:
# ./isaaclab.sh -p -c "import isaaclab; print('OK')"
```

If `isaaclab.sh` is not found, Isaac Lab must be installed first (see `install-isaaclab`). Do not proceed with benchmarks until the discovery check succeeds in the target environment.

## Before Running Any Benchmark

1. **Use a WARM run for headline FPS/frametime** — see the COLD/WARM/TRACY method in the `profiling` skill
2. **Set CPU governor to performance when the host allows it** — see `perf-tuning` skill. In containers where governor control is unavailable, record that limitation instead of trying privileged changes.
3. **Do not patch Isaac Sim shutdown by default.** If Tracy shutdown hangs after outputs are complete, use the scoped last-resort guidance in the `profiling` skill

## Benchmark Scripts

All in `scripts/benchmarks/`. Run via `./isaaclab.sh -p scripts/benchmarks/<script>.py`.

| Script | What it measures | Key params |
|--------|-----------------|------------|
| `benchmark_non_rl.py` | Environment step FPS (most common) | `--task`, `--num_envs`, `--num_frames` |
| `benchmark_rlgames.py` | RL-Games training throughput | `--task`, `--num_envs`, `--max_iterations` |
| `benchmark_rsl_rl.py` | RSL-RL training throughput | `--task`, `--num_envs`, `--max_iterations` |
| `benchmark_cameras.py` | Camera system FPS + autotune | `--num_tiled_cameras`, `--num_standard_cameras`, `--height`, `--width`, `--autotune` |
| `benchmark_load_robot.py` | Robot loading time | `--num_envs`, `--robot {anymal_d,h1,g1}` |
| `benchmark_startup.py` | App startup time profiling | `--task` (required), `--num_envs`, `--top_n` |
| `benchmark_lazy_export.py` | Lazy export/import speed | `--iterations`, `--tasks` (stdout only, no JSON backend) |
| `benchmark_view_comparison.py` | XformPrimView vs PhysX | `--num_envs`, `--num_iterations`, `--profile` (stdout/cProfile, no JSON backend) |
| `benchmark_xform_prim_view.py` | XformPrimView performance | `--num_envs`, `--num_iterations`, `--profile` (stdout/cProfile, no JSON backend) |

> **Note:** `benchmark_lazy_export.py`, `benchmark_view_comparison.py`, and `benchmark_xform_prim_view.py`
> do NOT support `--benchmark_backend` or `--output_path`. They output results to stdout.
> Use `--profile` (where available) to save cProfile `.prof` files.

**Common params:** `--device`, `--enable_cameras`, `--benchmark_backend`, `--output_path`, `--distributed`

> **Headless flag is version-dependent.** Some Isaac Lab versions expose `--headless`; newer versions may expose `--viz none`. Always check `--help` and choose the supported flag:
>
> ```bash
> HELP=$(./isaaclab.sh -p scripts/benchmarks/benchmark_non_rl.py --help 2>&1)
> if echo "$HELP" | grep -q -- '--viz'; then HEADLESS_ARG="--viz none"; else HEADLESS_ARG="--headless"; fi
> ```

**Passing Kit args** (for profiling, output control, etc.):
```bash
HELP=$(./isaaclab.sh -p scripts/benchmarks/benchmark_non_rl.py --help 2>&1)
if echo "$HELP" | grep -q -- '--viz'; then HEADLESS_ARG="--viz none"; else HEADLESS_ARG="--headless"; fi

./isaaclab.sh -p scripts/benchmarks/benchmark_non_rl.py \
    --task=Isaac-Ant-Direct-v0 $HEADLESS_ARG --num_envs=4096 \
    --kit_args "--/app/profilerBackend=tracy --/log/file=/tmp/kit.log"
```

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

- `benchmark_<type>_<task>_<timestamp>.json` — main results file
- `kit.log` — execution log (if `--/log/file=` is set via `--kit_args`)
- `*.tracy` / `*.nsys-rep` — profiling traces (only with profiling args)

### JSON structure
Array of phase objects, each with `phase_name`, `measurements` (list of `{name, data, type, unit}`),
and `metadata` (list of `{name, data, type}`). Phases: `benchmark_info`, `startup`, `runtime`,
`hardware_info`, `version_info`. RL benchmarks add a `train` phase.

---
