---
name: install-isaaclab
description: Install Isaac Lab for Isaac Sim-backed workflows or Isaac Lab 3.0+ kit-less/Newton workflows, then verify the setup. Use when the user asks to install, set up, or build Isaac Lab.
---

# Install Isaac Lab

**Repo:** https://github.com/isaac-sim/IsaacLab.git
**Modes:** Isaac Sim-backed full install, or Isaac Lab 3.0+ kit-less/Newton install.

## Choose Install Mode

- **Full Isaac Sim-backed install:** use for PhysX, ROS, URDF/MJCF importers, Omniverse visualization, and most benchmarking/profiling work. This requires Isaac Sim first.
- **Kit-less/Newton install (Isaac Lab 3.0+):** use only when the user explicitly wants core Isaac Lab/Newton workflows that do not require Isaac Sim features.

If the user does not specify, default to the full Isaac Sim-backed install for performance benchmarking.

## Kit-less / Newton Quick Install (Isaac Lab 3.0+)

Use this path only when Isaac Sim features are not needed.

```bash
git clone https://github.com/isaac-sim/IsaacLab.git
cd IsaacLab
git checkout develop   # or a specific commit/tag

# Installs core Isaac Lab packages plus the Newton backend.
./isaaclab.sh -i
```

Do not use this mode for PhysX, ROS, URDF/MJCF importers, or Omniverse visualizers.

## Full Isaac Sim-Backed Install

### Step 1: Install Isaac Sim

See the `install-isaacsim` skill. You need a working Isaac Sim before proceeding.

### Step 2: Install an Environment Manager (if not present)

Conda is the most common path; uv is also supported by recent Isaac Lab versions.

```bash
# Conda / Miniconda
which conda && echo "CONDA OK" || {
  wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -O /tmp/miniconda.sh
  bash /tmp/miniconda.sh -b -p ~/miniconda3
  ~/miniconda3/bin/conda init bash
  source ~/.bashrc
}

# Optional uv path
which uv && echo "UV OK" || echo "Install uv if you plan to use ./isaaclab.sh -u"
```

### Step 3: Clone Isaac Lab

```bash
git clone https://github.com/isaac-sim/IsaacLab.git
cd IsaacLab
git checkout develop   # or a specific commit/tag
```

### Step 4: Link Isaac Sim

```bash
# If Isaac Sim was source-built:
ln -s /path/to/IsaacSim/_build/linux-x86_64/release _isaac_sim

# If Isaac Sim was pip-installed, the link may not be needed —
# isaaclab.sh should detect the pip installation automatically.
# Check: ./isaaclab.sh -p -c "import isaacsim; print('OK')"
```

### Step 5: Create Environment

```bash
# Choose one. Default environment name is env_isaaclab if omitted.
# Conda:
./isaaclab.sh -c env_isaaclab

# uv on supported versions:
./isaaclab.sh -u env_isaaclab
```

This creates an environment with the correct Python version and base dependencies.
The default name (if you omit the argument) is `env_isaaclab`.

> **Note:** You may need to accept conda channel TOS first if this is a fresh install:
> ```bash
> conda tos accept --override-channels --channel https://repo.anaconda.com/pkgs/main
> conda tos accept --override-channels --channel https://repo.anaconda.com/pkgs/r
> ```

### Step 6: Install Dependencies

```bash
# Conda
source "$(conda info --base)/etc/profile.d/conda.sh"
conda activate env_isaaclab

# Or uv
# source env_isaaclab/bin/activate

./isaaclab.sh -i
```

> **Important:** Make sure to run these commands in `bash` (not `sh`). The `source` builtin
> and `conda activate` require bash.

## Verify

```bash
source "$(conda info --base)/etc/profile.d/conda.sh"
conda activate env_isaaclab
cd IsaacLab

# Quick import check
./isaaclab.sh -p -c "import isaaclab; print('OK')"

# Run a minimal benchmark (few frames)
./isaaclab.sh -p scripts/benchmarks/benchmark_non_rl.py \
  --task=Isaac-Cartpole-Direct-v0 --viz none --num_frames 10 --num_envs=16
```

> **Note:** `--headless` is deprecated in recent versions. Omit `--viz` for headless mode,
> or use `--viz none` to force headless when visualizers are configured.

## Day-to-Day Activation

```bash
source "$(conda info --base)/etc/profile.d/conda.sh"
conda activate env_isaaclab
cd IsaacLab
```

## Common Issues

### `./isaaclab.sh -i` fails finding Isaac Sim
Make sure the `_isaac_sim` symlink points to a valid Isaac Sim build/install:
```bash
ls -la _isaac_sim/
# Should show Isaac Sim files (python.sh, kit/, exts/, etc.)
```

### Conda env already exists
```bash
conda env remove -n env_isaaclab
./isaaclab.sh -c env_isaaclab
```

### GPU not found / CUDA errors
Verify NVIDIA driver and CUDA:
```bash
nvidia-smi
python -c "import torch; print(torch.cuda.is_available())"
```

---
