---
name: install-isaaclab
description: Install Isaac Lab for Isaac Sim-backed workflows or Isaac Lab 3.0+ kit-less/Newton workflows, then verify the setup. Use when the user asks to install, set up, or build Isaac Lab.
---

# Install Isaac Lab

**Repo:** https://github.com/isaac-sim/IsaacLab.git
**Modes:** Isaac Sim-backed full install, or Isaac Lab 3.0+ kit-less/Newton install. Conda is the most common setup path for full installs, while newer Isaac Lab versions can also use `uv`/pip virtual environments.

## Choose Install Mode

First, check for an existing Isaac Lab installation:

```bash
# Find isaaclab.sh
find /home /opt /data -maxdepth 5 -name isaaclab.sh 2>/dev/null | head -20

# Check _isaac_sim symlink if Isaac Lab dir is found
# ls -la /path/to/IsaacLab/_isaac_sim 2>/dev/null
```

If an existing installation is found, activate the intended conda/uv/venv environment and verify it works before reinstalling.

**Safety gates:** Environment creation is usually safe; environment removal, package-manager installs, and shell-startup mutations are not. Do not run `conda init`; ask/obtain approval before deleting environments or installing system packages.

### Mode Selection

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
# Prefer an existing environment manager.
command -v conda >/dev/null && echo "CONDA OK" || echo "CONDA MISSING"
command -v uv >/dev/null && echo "UV OK" || echo "UV MISSING (needed for ./isaaclab.sh -u)"
```

If neither `conda` nor `uv` is available, ask before installing one. Do not run `conda init` from this skill; it mutates user shell startup files. If the user approves a local Miniconda install, use a non-mutating activation path:

```bash
wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -O /tmp/miniconda.sh
bash /tmp/miniconda.sh -b -p "$HOME/miniconda3"
source "$HOME/miniconda3/etc/profile.d/conda.sh"
conda --version
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

# If Isaac Sim was pip-installed in a venv, activate that venv first. The link
# may not be needed because isaaclab.sh can detect the active pip installation.
# Check in the target env: ./isaaclab.sh -p -c "import isaacsim; from isaacsim.simulation_app import SimulationApp; print('OK')"
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

# Run a minimal benchmark (few frames). Headless flag is version-dependent:
HELP=$(./isaaclab.sh -p scripts/benchmarks/benchmark_non_rl.py --help 2>&1)
if echo "$HELP" | grep -q -- '--viz'; then HEADLESS_ARG="--viz none"; else HEADLESS_ARG="--headless"; fi

./isaaclab.sh -p scripts/benchmarks/benchmark_non_rl.py \
  --task=Isaac-Cartpole-Direct-v0 $HEADLESS_ARG --num_frames 10 --num_envs=16
```

> **Note:** Check `--help` before choosing headless flags. Some Isaac Lab versions expose
> `--headless`; newer versions may expose `--viz none`.

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
Only remove an environment after confirming it is the intended target and approval is granted:
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
