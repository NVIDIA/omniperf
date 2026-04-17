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
- **Python:** 3.10+
- **RAM:** 32 GB+ recommended
- **Disk:** ~30 GB for full install with cached assets

## Virtual Environment (Strongly Recommended)

Always install Isaac Sim into an isolated Python environment. Installing into the system Python conflicts with distro packages (especially on Ubuntu) and makes upgrades/uninstalls messy. Use one of the options below before running any `pip install` command from this skill.

### Option A: `venv` (stdlib, simplest)

```bash
python3.10 -m venv ~/venvs/isaacsim
source ~/venvs/isaacsim/bin/activate
python -m pip install --upgrade pip setuptools wheel
```

Deactivate later with `deactivate`. Re-activate in any new shell before running Isaac Sim commands.

### Option B: `uv` (fast, recommended for CI)

```bash
# Install uv once: https://docs.astral.sh/uv/
uv venv --python 3.10 ~/venvs/isaacsim
source ~/venvs/isaacsim/bin/activate
uv pip install --upgrade pip
```

### Option C: `conda` / `mamba`

```bash
conda create -n isaacsim python=3.10 -y
conda activate isaacsim
```

### Notes

- **Python version must match.** Isaac Sim requires Python 3.10+; pinning to 3.10 is the safest default.
- **Method 2 (source build) ships its own Python** via `_build/linux-x86_64/release/python.sh` — you do not need a venv for running the source build, but you still want one for any host-side tooling (tests, scripts, editable installs).
- **Editable install (Method 3) needs an active venv** — never `pip install -e .` into system Python.
- **Cached assets & shader caches** live under `~/.cache/ov` and `~/.local/share/ov`. These are shared across venvs; deleting the venv does not clear them.
- To completely reset: `deactivate && rm -rf ~/venvs/isaacsim ~/.cache/ov ~/.local/share/ov`.

## Method 1: Pip Install (Quickest)

> **Note:** As of April 2026, pip only has IsaacSim up to v4.5.0.0.
> For v5.x and v6.x, use the source build (Method 2) or editable install (Method 3).

Activate your venv first (see [Virtual Environment](#virtual-environment-strongly-recommended)), then:

```bash
pip install isaacsim
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
