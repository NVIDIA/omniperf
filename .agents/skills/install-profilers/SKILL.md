---
name: install-profilers
description: Install profiling tools for Isaac Sim / Isaac Lab / Kit-based applications. Covers Nsight Systems (`nsys` CLI), `sqlite3`, Tracy `csvexport`, canonical Tracy `capture`/`capture-release`, and `update` for memory strip tests, with optional `tracy-capture`/`tracy-update` aliases. Use when setting up a profiling environment, when nsys/sqlite3/csvexport/capture/update tools are missing, or before running profiling, nsys-analyze, or tracy-memory.
---

# Install Profilers for Omniverse / Kit Apps

## Quick Check — What's Already Installed?

```bash
nsys --version 2>/dev/null && echo "nsys: OK" || echo "nsys: MISSING"
csvexport --help 2>/dev/null && echo "csvexport: OK" || echo "csvexport: MISSING"
CAPTURE_BIN=$(command -v capture || command -v capture-release || command -v tracy-capture)
[ -n "$CAPTURE_BIN" ] && echo "capture: OK ($CAPTURE_BIN)" || echo "capture: MISSING"
UPDATE_BIN=$(command -v update || command -v tracy-update)
[ -n "$UPDATE_BIN" ] && echo "update: OK ($UPDATE_BIN)" || echo "update: MISSING (optional; needed for memory strip tests)"
sqlite3 --version 2>/dev/null && echo "sqlite3: OK" || echo "sqlite3: MISSING"
```

Install only what's missing.

**Approval gates:** Commands that install packages, write `/usr/local/bin`, change `/proc/sys/kernel/perf_event_paranoid`, or create system symlinks are host mutations. Check first, then ask/obtain approval before running the `sudo` examples. In containers where sysctl or GPU-counter access is unavailable, do not fight the host: use the container-safe capture mode in the `profiling` skill.

---

## 1. Nsight Systems (nsys CLI)

The `nsys` CLI captures GPU/CPU traces and exports `.nsys-rep` → SQLite.

### Option A: Standalone installer from NVIDIA (recommended)

The profiling guide recommends the latest standalone Nsight Systems package because CUDA Toolkit packages may lag behind.

```bash
# Get the current .deb URL from https://developer.nvidia.com/nsight-systems.
# Do not blindly reuse stale versioned URLs from old docs.
wget '<nsight-systems-current-linux-amd64.deb-url-from-download-page>' -O nsight-systems.deb
sudo dpkg -i nsight-systems.deb
nsys --version
```

For non-Debian Linux, use the standalone `.run` installer from the same download page:

```bash
chmod +x NsightSystems-linux-public-*.run
sudo ./NsightSystems-linux-public-*.run --accept
```

### Option B: From NVIDIA CUDA apt repo (fallback)

If the CUDA apt repo is already configured (check `ls /etc/apt/sources.list.d/*cuda*`):

```bash
# List available versions
apt-cache search nsight-systems-20 | sort -V

# Install the newest available package from the repo
sudo apt-get update
NSYS_PKG="nsight-systems-<version-from-apt-cache>"
sudo apt-get install -y "$NSYS_PKG"

# Verify
nsys --version
```

The package location varies by Nsight Systems version, commonly under `/opt/nvidia/nsight-systems/<version>/target-linux-x64/nsys` or a `bin/nsys` subdirectory. It typically creates a symlink at `/usr/local/bin/nsys`, but if not:

```bash
NSYS_BIN=$(find /opt/nvidia/nsight-systems -type f -name nsys 2>/dev/null | sort -V | tail -1)
[ -n "$NSYS_BIN" ] || { echo "nsys binary not found under /opt/nvidia/nsight-systems"; exit 1; }
sudo ln -sf "$NSYS_BIN" /usr/local/bin/nsys
nsys --version
```

### Option C: Add CUDA repo first (if not present)

```bash
# Ubuntu 22.04 x86_64
wget https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2204/x86_64/cuda-keyring_1.1-1_all.deb
sudo dpkg -i cuda-keyring_1.1-1_all.deb
sudo apt-get update

# Then install the newest available package as in Option B
apt-cache search nsight-systems-20 | sort -V
NSYS_PKG="nsight-systems-<version-from-apt-cache>"
sudo apt-get install -y "$NSYS_PKG"
```

For other distros, replace `ubuntu2204/x86_64` with your platform.
See: https://developer.nvidia.com/cuda-downloads (select "deb (network)").

### Option D: CLI-only (headless servers)

```bash
sudo apt-get install -y nsight-systems-cli
# Smaller package, no GUI — just the nsys command
```

### Post-install: perf_event_paranoid

CPU IP/backtrace sampling needs perf access. Check first; change only on a host where privileged profiling is approved:

```bash
cat /proc/sys/kernel/perf_event_paranoid

# Host-only, approval-gated fix if > 2 and CPU sampling is required:
sudo sh -c 'echo 2 > /proc/sys/kernel/perf_event_paranoid'

# Persistent host-only fix, also approval-gated:
sudo sh -c 'echo kernel.perf_event_paranoid=2 > /etc/sysctl.d/99-nsys.conf'
```

> **Container note:** `perf_event_paranoid` may be read-only in containers.
> `nsys` can still trace CUDA/NVTX but won't collect CPU IP samples.

> **Container note:** `--gpu-metrics-devices` may fail with `ERR_NVGPUCTRPERM`
> ("Insufficient privilege"). Drop this flag in containers — NVTX/CUDA tracing
> still works fine without GPU hardware counters.

---

## 2. sqlite3 (for nsys SQLite exports)

`nsys export --type=sqlite` creates a `.sqlite` file from `.nsys-rep` traces.
Use `sqlite3` to query NVTX events, CUDA kernels, and GPU metrics.

```bash
sudo apt-get install -y sqlite3
sqlite3 --version
```

### Export smoke test

```bash
# Export .nsys-rep to SQLite
nsys export --type=sqlite -o profile.sqlite profile.nsys-rep

# Confirm SQLite can read the export
sqlite3 profile.sqlite ".tables"
```

### SQLite schema reference (key tables)

| Table | Contents |
|-------|----------|
| `NVTX_EVENTS` | NVTX ranges/markers — use `text` or join `textId→StringIds.id` for names |
| `CUPTI_ACTIVITY_KIND_KERNEL` | CUDA kernel launches (empty for Kit/RTX apps — normal) |
| `CUPTI_ACTIVITY_KIND_MEMCPY` | CUDA memcpy operations |
| `TARGET_INFO_GPU` | GPU hardware info |
| `TARGET_INFO_SYSTEM_ENV` | System environment |
| `StringIds` | String lookup table for `textId` foreign keys |

> **Gotcha:** `NVTX_EVENTS` has NO `name` column — use `text` (inline string) or join on `textId`.

---

## 3. Tracy Profiler Tools (`csvexport`, `capture`, `update`)

Tracy is used by Kit/Isaac Sim when `--/app/profilerBackend=tracy` is set.
You need two tools for the standard flow: `capture` (record traces) and `csvexport` (export to CSV for analysis). For memory profiling strip tests, also expose Tracy's `update` tool. `tracy-capture` and `tracy-update` are acceptable local aliases, but `capture` / `capture-release` / `update` are the source-guide names.

### Option A: Use the bundled Kit binary (best protocol match)

Building Isaac Sim from source, or another Kit-based app, downloads `omni.kit.profiler.tracy`, which ships a matching Tracy `capture` binary. Look under:

- `exts/omni.kit.profiler.tracy/`
- `extscore/omni.kit.profiler.tracy/`
- `extscache/omni.kit.profiler.tracy/`

Using the bundled binary guarantees version compatibility with the Tracy protocol embedded in Kit.

### Option B: Build Tracy 0.11.1 from source (recommended fallback)

```bash
sudo apt-get install -y build-essential cmake git libcapstone-dev

git clone https://github.com/wolfpld/tracy.git
cd tracy
git checkout v0.11.1

# Build csvexport (headless, no GUI deps)
cmake -B csvexport/build -S csvexport -DCMAKE_BUILD_TYPE=Release -DNO_ISA_EXTENSIONS=ON
cmake --build csvexport/build --parallel --target tracy-csvexport
sudo cp csvexport/build/tracy-csvexport /usr/local/bin/csvexport

# Build capture. Tracy 0.11.x uses CMake targets here; older docs may mention
# capture/build/unix/capture-release, which does not exist in all checkouts.
cmake -B capture/build -S capture -DCMAKE_BUILD_TYPE=Release
cmake --build capture/build --parallel --target tracy-capture
sudo cp capture/build/tracy-capture /usr/local/bin/capture
sudo ln -sf /usr/local/bin/capture /usr/local/bin/capture-release  # compatibility alias
sudo ln -sf /usr/local/bin/capture /usr/local/bin/tracy-capture    # optional compatibility alias

# Build update (optional; required by the tracy-memory strip test)
cmake -B update/build -S update -DCMAKE_BUILD_TYPE=Release
cmake --build update/build --parallel --target tracy-update
sudo cp update/build/tracy-update /usr/local/bin/update
sudo ln -sf /usr/local/bin/update /usr/local/bin/tracy-update  # optional compatibility alias

# If any target name fails, inspect the checkout instead of guessing paths:
# cmake --build capture/build --target help | grep -E 'tracy|capture'
# find capture/build update/build csvexport/build -maxdepth 2 -type f -perm -111 | sort

# Verify
csvexport --help
capture --help
capture-release --help
update --help
```

> **Note:** The GUI profiler (`tracy-profiler`) requires `libglfw3-dev libdbus-1-dev libfreetype-dev`
> and a display. Skip on headless servers — `csvexport` + `sqlite3` queries are sufficient for
> automated analysis.

### Option C: Ubuntu 25.04+ packages (if available)

```bash
# Available in Ubuntu 25.04+ universe repo
sudo apt-get install -y tracy-csvexport tracy-capture
```

Not available on Ubuntu 22.04/24.04 from default repos.

For Tracy capture, CSV export usage, shutdown handling, and analysis handoff, use the `profiling` skill. This skill only installs and verifies the capture/export binaries.

---

## Verification Checklist

After installation, verify the full toolchain:

```bash
echo "=== Profiling Toolchain ==="
nsys --version 2>/dev/null        || echo "MISSING: nsys"
sqlite3 --version 2>/dev/null     || echo "MISSING: sqlite3"
csvexport --help 2>&1 | head -1   || echo "MISSING: csvexport (Tracy)"
CAPTURE_BIN=$(command -v capture || command -v capture-release || command -v tracy-capture)
[ -n "$CAPTURE_BIN" ] && "$CAPTURE_BIN" --help 2>&1 | head -1 || echo "MISSING: capture"
UPDATE_BIN=$(command -v update || command -v tracy-update)
[ -n "$UPDATE_BIN" ] && "$UPDATE_BIN" --help 2>&1 | head -1 || echo "MISSING: update (optional; needed for tracy-memory)"
echo "perf_event_paranoid: $(cat /proc/sys/kernel/perf_event_paranoid 2>/dev/null || echo 'N/A')"
```

These tools are needed for the full profiling workflow:
- `nsys` — capture Nsight Systems traces
- `sqlite3` — query nsys SQLite exports
- `csvexport` — export Tracy `.tracy` files to CSV
- `capture` / `capture-release` — record Tracy traces from Kit apps
- `update` — strip/transform Tracy captures for memory-capture verification
