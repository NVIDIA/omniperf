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

> **Note:** As of April 2026, NVIDIA's pip install flow uses PyPI plus the NVIDIA package index, installs PyTorch first, and installs the full Isaac Sim extras plus the extension cache. A bare `pip install isaacsim` installs only the metapackage and can pass an import check while missing app, benchmark, or extension-cache components.

Activate your venv first (see [Virtual Environment](#virtual-environment-strongly-recommended)), then:

```bash
# Accept the Omniverse EULA non-interactively for scripts/CI.
export OMNI_KIT_ACCEPT_EULA=YES

# Isaac Sim 6.0 docs use PyTorch 2.10.0; choose the CUDA wheel index for your platform.
pip install torch==2.10.0 --index-url https://download.pytorch.org/whl/cu128

# Latest compatible full install for the active Python.
pip install 'isaacsim[all,extscache]' --extra-index-url https://pypi.nvidia.com

# Or pin to a specific release family. Match the Python version matrix above.
pip install 'isaacsim[all,extscache]==4.5.0' --extra-index-url https://pypi.nvidia.com   # Python 3.10
pip install 'isaacsim[all,extscache]==5.1.0' --extra-index-url https://pypi.nvidia.com   # Python 3.11
pip install 'isaacsim[all,extscache]==6.0.0' --extra-index-url https://pypi.nvidia.com   # Python 3.12
```

Verify:
```bash
python -c "import isaacsim; print('OK')"
python -c "import isaacsim; from isaacsim.simulation_app import SimulationApp; print('SimulationApp OK')"
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
sudo usermod -aG docker $USER

# Start a new login session, or run this shell-only refresh:
newgrp docker

# If docker ps still fails, use `sudo docker ...` for the current command
# or ask an administrator to fix Docker group/session setup.
# Do NOT chmod /var/run/docker.sock: it grants root-equivalent Docker access
# to every local user.
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
# If still fails in this shell: use `sudo docker ps` to verify Docker works,
# then start a fresh login session so group membership is applied.
```

### No DISPLAY / Vulkan init fails
Kit needs a display even in headless mode. Set up Xvfb:
```bash
sudo apt-get install -y xvfb
Xvfb :99 -screen 0 1920x1080x24 &
export DISPLAY=:99
```

### Shutdown hangs
Do not patch installed Isaac Sim files by default. For repeated Tracy shutdown hangs, use the scoped last-resort workaround in the `profiling` skill, and restore the original file afterward.

---
