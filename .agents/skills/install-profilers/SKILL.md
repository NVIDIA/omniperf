---
name: install-profilers
description: Install profiling tools for Isaac Sim / Isaac Lab / Kit-based applications. Covers Nsight Systems (nsys CLI), Tracy Profiler (`csvexport`, `tracy-capture`), and sqlite3 for nsys SQLite exports. Use when setting up a profiling environment, when nsys/tracy/csvexport/sqlite3 are missing, or before running the profiling or nsys-analyze skills.
---

# Install Profilers for Omniverse / Kit Apps

## Quick Check — What's Already Installed?

```bash
nsys --version 2>/dev/null && echo "nsys: OK" || echo "nsys: MISSING"
csvexport --help 2>/dev/null && echo "csvexport: OK" || echo "csvexport: MISSING"
which tracy-capture >/dev/null 2>&1 && echo "tracy-capture: OK" || echo "tracy-capture: MISSING"
sqlite3 --version 2>/dev/null && echo "sqlite3: OK" || echo "sqlite3: MISSING"
```

Install only what's missing.

---

## 1. Nsight Systems (nsys CLI)

The `nsys` CLI captures GPU/CPU traces and exports `.nsys-rep` → SQLite.

### Option A: From NVIDIA CUDA apt repo (recommended on Ubuntu)

If the CUDA apt repo is already configured (check `ls /etc/apt/sources.list.d/*cuda*`):

```bash
# List available versions
apt-cache search nsight-systems-20 | sort -V

# Install latest (or pick a specific version)
sudo apt-get update
sudo apt-get install -y nsight-systems-2025.6.3   # adjust version

# Verify
nsys --version
```

The package installs to `/opt/nvidia/nsight-systems/<version>/bin/nsys`.
It typically creates a symlink at `/usr/local/bin/nsys`, but if not:

```bash
sudo ln -sf /opt/nvidia/nsight-systems/*/bin/nsys /usr/local/bin/nsys
```

### Option B: Add CUDA repo first (if not present)

```bash
# Ubuntu 22.04 x86_64
wget https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2204/x86_64/cuda-keyring_1.1-1_all.deb
sudo dpkg -i cuda-keyring_1.1-1_all.deb
sudo apt-get update

# Then install as in Option A
sudo apt-get install -y nsight-systems-2025.6.3
```

For other distros, replace `ubuntu2204/x86_64` with your platform.
See: https://developer.nvidia.com/cuda-downloads (select "deb (network)").

### Option C: Standalone .run installer

Download from https://developer.nvidia.com/nsight-systems — requires NVIDIA developer account login.

```bash
chmod +x NsightSystems-linux-public-*.run
sudo ./NsightSystems-linux-public-*.run --accept
# Installs to /opt/nvidia/nsight-systems/
```

### Option D: CLI-only (headless servers)

```bash
sudo apt-get install -y nsight-systems-cli
# Smaller package, no GUI — just the nsys command
```

### Post-install: perf_event_paranoid

`nsys` needs sampling access. Check and fix:

```bash
cat /proc/sys/kernel/perf_event_paranoid
# If > 2:
sudo sh -c 'echo 2 > /proc/sys/kernel/perf_event_paranoid'
# Persistent (survives reboot):
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

### Key usage with nsys

```bash
# Export .nsys-rep to SQLite
nsys export --type=sqlite -o profile.sqlite profile.nsys-rep

# Query top NVTX zones
sqlite3 profile.sqlite "
SELECT COALESCE(e.text, s.value) as zone_name,
       COUNT(*) as cnt,
       ROUND(AVG(e.end - e.start) / 1e6, 2) as avg_ms,
       ROUND(SUM(e.end - e.start) / 1e6, 2) as total_ms
FROM NVTX_EVENTS e
LEFT JOIN StringIds s ON e.textId = s.id
WHERE e.end IS NOT NULL AND (e.end - e.start) > 0
GROUP BY zone_name ORDER BY total_ms DESC LIMIT 30;
"
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

## 3. Tracy Profiler Tools (`csvexport`, `tracy-capture`)

Tracy is used by Kit/Isaac Sim when `--/app/profilerBackend=tracy` is set.
You need two tools: `tracy-capture` (record traces) and `csvexport` (export to CSV for analysis).

### Option A: Build from source (recommended — gets latest)

```bash
sudo apt-get install -y build-essential cmake git libcapstone-dev

git clone https://github.com/wolfpld/tracy.git
cd tracy
git checkout v0.11.1   # or latest stable tag

# Build csvexport (headless, no GUI deps)
cmake -B csvexport/build -S csvexport -DCMAKE_BUILD_TYPE=Release -DNO_ISA_EXTENSIONS=ON
cmake --build csvexport/build --parallel
sudo cp csvexport/build/csvexport /usr/local/bin/csvexport

# Build capture (headless trace recorder)
cmake -B capture/build -S capture -DCMAKE_BUILD_TYPE=Release
cmake --build capture/build --parallel
sudo cp capture/build/tracy-capture /usr/local/bin/tracy-capture

# Verify
csvexport --help
tracy-capture --help
```

> **Note:** The GUI profiler (`tracy-profiler`) requires `libglfw3-dev libdbus-1-dev libfreetype-dev`
> and a display. Skip on headless servers — `csvexport` + `sqlite3` queries are sufficient for
> automated analysis.

### Option B: Ubuntu 25.04+ packages (if available)

```bash
# Available in Ubuntu 25.04+ universe repo
sudo apt-get install -y tracy-csvexport tracy-capture
```

Not available on Ubuntu 22.04/24.04 from default repos.

### Tracy capture usage

```bash
# Start the Isaac Sim benchmark first:
./python.sh benchmark_script.py \
  --/app/profilerBackend=tracy --/app/profileFromStart=true \
  --/profiler/gpu/tracyInject/enabled=true &
APP_PID=$!

# Wait for the Tracy port, then attach the recorder:
for i in $(seq 1 60); do
  ss -tlnp | grep -q :8086 && break
  sleep 2
done

tracy-capture -o trace.tracy -f -p 8086
wait $APP_PID
```

### Tracy CSV export usage

```bash
csvexport trace.tracy > zones.csv
# Columns: name, src_file, src_line, total_ns, total_perc, counts, mean_ns, min_ns, max_ns, std_ns
# Sort by total time descending:
sort -t',' -k4 -rn zones.csv | head -50
```

---

## Verification Checklist

After installation, verify the full toolchain:

```bash
echo "=== Profiling Toolchain ==="
nsys --version 2>/dev/null        || echo "MISSING: nsys"
sqlite3 --version 2>/dev/null     || echo "MISSING: sqlite3"
csvexport --help 2>&1 | head -1   || echo "MISSING: csvexport (Tracy)"
tracy-capture --help 2>&1 | head -1 || echo "MISSING: tracy-capture"
echo "perf_event_paranoid: $(cat /proc/sys/kernel/perf_event_paranoid 2>/dev/null || echo 'N/A')"
```

All four tools are needed for the full profiling workflow:
- `nsys` — capture Nsight Systems traces
- `sqlite3` — query nsys SQLite exports
- `csvexport` — export Tracy `.tracy` files to CSV
- `tracy-capture` — record Tracy traces from Kit apps
