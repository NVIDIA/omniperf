---
name: install-isaacsim
description: Install Isaac Sim via pip or source build. Covers Docker setup, verification, and common install issues. Use when the user asks to install, set up, or build Isaac Sim.
---

# Install Isaac Sim

**Public repo:** https://github.com/isaac-sim/IsaacSim
**Branch convention:** `develop` (latest), `release/*` (stable), version tags (e.g., `6.0.0`)

## System Requirements

- **GPU:** NVIDIA RTX (Ada, Ampere, or newer recommended)
- **Driver:** 535+ (check with `nvidia-smi`)
- **OS:** Ubuntu 22.04+ (Linux), Windows 10/11
- **Python:** see [Python version matrix](#python-version-matrix) below (version is pinned per Isaac Sim release)
- **RAM:** 32 GB+ recommended
- **Disk:** ~30 GB for full install with cached assets

## Python version matrix

Isaac Sim is built against a single, specific CPython version per release. Using the wrong Python version will cause `pip install` to fail to resolve wheels, or import-time ABI errors for the source build. Match the table exactly — newer or older minor versions are not supported.

| Isaac Sim | Python | Notes |
|-----------|--------|-------|
| 4.0.x – 4.2.x | 3.10 | Linux/Windows |
| 4.5.x | 3.10 | Last 3.10 release |
| 5.0.x | 3.11 | GLIBC 2.35+ required on Linux |
| 5.1.x | 3.11 | |
| 6.0.x | 3.12 | Current (Early Developer Release → GA) |

Primary sources:
- 4.5: <https://docs.isaacsim.omniverse.nvidia.com/4.5.0/installation/install_python.html>
- 5.0: <https://docs.isaacsim.omniverse.nvidia.com/5.0.0/installation/install_python.html>
- 5.1: <https://docs.isaacsim.omniverse.nvidia.com/5.1.0/installation/install_python.html>
- 6.0: <https://docs.isaacsim.omniverse.nvidia.com/6.0.0/installation/install_python.html>

Check your Python:
```bash
python3 --version
```

If the required version isn't installed (Ubuntu example):
```bash
sudo add-apt-repository -y ppa:deadsnakes/ppa
sudo apt-get update
sudo apt-get install -y python3.12 python3.12-venv python3.12-dev   # adjust version to match the table
```

## Virtual Environment (Strongly Recommended)

Always install Isaac Sim into an isolated Python environment. Installing into the system Python conflicts with distro packages (especially on Ubuntu) and makes upgrades/uninstalls messy. Use one of the options below before running any `pip install` command from this skill.

> **Pick the Python version that matches your target Isaac Sim release** — see the [Python version matrix](#python-version-matrix). Examples below use 3.12 for Isaac Sim 6.0.x; substitute 3.11 for 5.x or 3.10 for 4.5.x.

### Option A: `venv` (stdlib, simplest)

```bash
# Replace 3.12 with the version required by your Isaac Sim release
python3.12 -m venv ~/venvs/isaacsim
source ~/venvs/isaacsim/bin/activate
python -m pip install --upgrade pip setuptools wheel
```

Deactivate later with `deactivate`. Re-activate in any new shell before running Isaac Sim commands.

### Option B: `uv` (fast, recommended for CI)

```bash
# Install uv once: https://docs.astral.sh/uv/
uv venv --python 3.12 ~/venvs/isaacsim   # match Python to Isaac Sim release
source ~/venvs/isaacsim/bin/activate
uv pip install --upgrade pip
```

### Option C: `conda` / `mamba`

```bash
conda create -n isaacsim python=3.12 -y   # match Python to Isaac Sim release
conda activate isaacsim
```

### Notes

- **Python version is strict.** Each Isaac Sim release is built against one specific CPython minor version — see the [matrix](#python-version-matrix). Mismatches cause wheel resolution failures or import-time ABI errors.
- **Method 2 (source build) ships its own Python** via `_build/linux-x86_64/release/python.sh` — you do not need a venv for running the source build, but you still want one for any host-side tooling (tests, scripts, editable installs).
- **Editable install (Method 3) needs an active venv** — never `pip install -e .` into system Python.
- **Cached assets & shader caches** live under `~/.cache/ov` and `~/.local/share/ov`. These are shared across venvs; deleting the venv does not clear them.
- To completely reset: `deactivate && rm -rf ~/venvs/isaacsim ~/.cache/ov ~/.local/share/ov`.

## Method 1: Pip Install (Quickest)

> **Note:** As of April 2026, PyPI ships `isaacsim` up through `6.0.0.0`. Pick the version that matches your venv's Python (see the [matrix](#python-version-matrix)); `pip install isaacsim` without a pin will resolve to the newest compatible wheel.

Activate your venv first (see [Virtual Environment](#virtual-environment-strongly-recommended)), then:

```bash
# Latest compatible with the active Python
pip install isaacsim

# Or pin to a specific release
pip install 'isaacsim==4.5.0.0'   # Python 3.10
pip install 'isaacsim==5.1.0.0'   # Python 3.11
pip install 'isaacsim==6.0.0.0'   # Python 3.12
```

Verify:
```bash
python -c "import isaacsim; print('OK')"
```

## Method 2: Source Build from GitHub

Use this when you need to modify code, run tests, or link a custom Kit build.

### Prerequisites

**Docker is required by default.** Check and install if missing:
```bash
docker ps > /dev/null 2>&1 && echo "DOCKER OK" || echo "NEED INSTALL"

# Install Docker (Ubuntu/Debian)
sudo apt-get update && sudo apt-get install -y docker.io
sudo systemctl start docker && sudo systemctl enable docker
sudo usermod -aG docker $USER && newgrp docker

# If docker ps still fails after group add:
sudo chmod 666 /var/run/docker.sock
```

### Build

```bash
git clone https://github.com/isaac-sim/IsaacSim.git
cd IsaacSim
git checkout develop   # or a specific version tag

# With Docker (default, recommended)
./build.sh -xr

# Without Docker (fallback — needs extra deps)
sudo apt-get install -y libglu1-mesa-dev libegl1-mesa-dev libgles2-mesa-dev patchelf
./build.sh -xr --no-docker
```

Build output: `_build/linux-x86_64/release`

### Verify source build

```bash
cd _build/linux-x86_64/release
./python.sh -c "import omni; print('OK')"
```

## Method 3: Pip Editable Install from Source

Activate your venv first (see [Virtual Environment](#virtual-environment-strongly-recommended)), then:

```bash
git clone https://github.com/isaac-sim/IsaacSim.git
cd IsaacSim
git checkout develop
pip install -e .
```

## Nucleus Authentication (Optional)

Only needed for benchmarks/scenes that use Nucleus-hosted assets. Many workflows use local assets and skip this.

```bash
export OMNI_USER='$omni-api-token'
export OMNI_PASS='<YOUR-API-TOKEN>'
```

- `OMNI_USER` is always the literal string `$omni-api-token` (not a shell variable)
- Ask the user for their `OMNI_PASS` token if needed
- Expired JWT tokens cause silent failures (scenes load but materials are missing — all-black renders)

Check token expiry:
```bash
echo "$OMNI_PASS" | cut -d. -f2 | base64 -d 2>/dev/null | python3 -c "
import json, sys; from datetime import datetime; d = json.load(sys.stdin)
print(f'Expires: {datetime.fromtimestamp(d.get(\"exp\", 0))}')"
```

## Common Issues

### Build fails with Docker permission error
```bash
sudo usermod -aG docker $USER
newgrp docker
# If still fails: sudo chmod 666 /var/run/docker.sock
```

### No DISPLAY / Vulkan init fails
Kit needs a display even in headless mode. Set up Xvfb:
```bash
sudo apt-get install -y xvfb
Xvfb :99 -screen 0 1920x1080x24 &
export DISPLAY=:99
```

### Shutdown hangs
Apply the `os._exit(0)` patch before running benchmarks — see the `profiling` skill.

---
