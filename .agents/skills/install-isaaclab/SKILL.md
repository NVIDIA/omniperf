---
name: install-isaaclab
description: Install Isaac Lab with conda, link Isaac Sim, and verify the setup. Use when the user asks to install, set up, or build Isaac Lab.
---

# Install Isaac Lab

**Repo:** https://github.com/isaac-sim/IsaacLab.git
**Requires:** Isaac Sim (installed first) + Miniconda/Conda

## Step 1: Install Isaac Sim

See the `install-isaacsim` skill. You need a working Isaac Sim before proceeding.

## Step 2: Install Miniconda (if not present)

```bash
which conda && echo "CONDA OK" || {
  wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -O /tmp/miniconda.sh
  bash /tmp/miniconda.sh -b -p ~/miniconda3
  ~/miniconda3/bin/conda init bash
  source ~/.bashrc
}
```

## Step 3: Clone Isaac Lab

```bash
git clone https://github.com/isaac-sim/IsaacLab.git
cd IsaacLab
git checkout develop   # or a specific commit/tag
```

## Step 4: Link Isaac Sim

```bash
# If Isaac Sim was source-built:
ln -s /path/to/IsaacSim/_build/linux-x86_64/release _isaac_sim

# If Isaac Sim was pip-installed, the link may not be needed —
# isaaclab.sh should detect the pip installation automatically.
# Check: ./isaaclab.sh -p -c "import isaacsim; print('OK')"
```

## Step 5: Create Conda Environment

```bash
./isaaclab.sh -c isaaclab_env
```

This creates a conda env with the correct Python version and base dependencies.
The default name (if you omit the argument) is `env_isaaclab`.

> **Note:** You may need to accept conda channel TOS first if this is a fresh install:
> ```bash
> conda tos accept --override-channels --channel https://repo.anaconda.com/pkgs/main
> conda tos accept --override-channels --channel https://repo.anaconda.com/pkgs/r
> ```

## Step 6: Install Dependencies

```bash
source ~/miniconda3/etc/profile.d/conda.sh
conda activate isaaclab_env
./isaaclab.sh -i
```

> **Important:** Make sure to run these commands in `bash` (not `sh`). The `source` builtin
> and `conda activate` require bash.

## Verify

```bash
source ~/miniconda3/etc/profile.d/conda.sh
conda activate isaaclab_env
cd IsaacLab

# Quick import check
./isaaclab.sh -p -c "import isaaclab; print('OK')"

# Run a minimal benchmark (few frames)
./isaaclab.sh -p scripts/benchmarks/benchmark_non_rl.py \
  --task=Isaac-Cartpole-Direct-v0 --num_frames 10 --num_envs=16
```

> **Note:** `--headless` is deprecated in recent versions. Omit `--viz` for headless mode,
> or use `--viz none` to force headless when visualizers are configured.

## Day-to-Day Activation

```bash
source ~/miniconda3/etc/profile.d/conda.sh
conda activate isaaclab_env
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
conda env remove -n isaaclab_env
./isaaclab.sh -c isaaclab_env
```

### GPU not found / CUDA errors
Verify NVIDIA driver and CUDA:
```bash
nvidia-smi
python -c "import torch; print(torch.cuda.is_available())"
```

---
