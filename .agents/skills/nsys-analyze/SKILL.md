---
name: nsys-analyze
description: Analyze profiling data from Kit-based apps. Covers Omniverse-specific NVTX zone interpretation, phase detection using sqlite3/csvexport queries, and two-version comparison methodology. Use after capturing profiles with the profiling skill.
---

# Profile Analysis for Omniverse / Kit-based Apps

Analyze profiling data from Kit, Isaac Sim, and Isaac Lab using `sqlite3` (for `.nsys-rep`) and `csvexport` (for `.tracy`).
For capturing profiles and installing tools, see the `profiling` and `install-profilers` skills.

**Required tools:** `nsys`, `sqlite3`, `csvexport` — see `install-profilers` skill.

## Omniverse NVTX Zone Reference

| Zone Pattern | Meaning | Phase |
|---|---|---|
| `App Update` / `App Main loop` | Frame boundaries | Runtime |
| `UsdFileOp` / `UsdFileOp::open` / `UsdFileOp::newStage` | Stage operations | Startup/Loading |
| `UsdContext::Impl::render` | USD render context | Runtime |
| `RtxHydraEngine::render*` | RTX render passes | Runtime |
| `Hydra render views*` | Hydra render delegate ops | Runtime |
| `OmniGraph::*` / `ComputeGraphImpl::*` | OmniGraph compute | Runtime |
| `GeoTreeNode::*` / `Fabric::*` | Fabric/scene population | Loading/Runtime |
| `Carbonite::*` / `carb::*` | Low-level framework (**noise — exclude**) | All |
| `Thread waiting...` | Idle thread (**noise — exclude**) | All |
| `Executing task` / `Running fiber` | Task scheduler (**noise — exclude**) | All |

## Phase Detection Rules

Kit apps have phases: **startup** → **loading** → **runtime** → **shutdown**.

- **Startup** = trace start → first `App Update` frame
- **Loading frames** = frames with duration > 5× median (stage loading spikes — can appear at start *or* mid-run)
- **Runtime frames** = frames with duration ≤ 5× median (steady-state)
- **Frame marker** = `App Update` zone (NOT `App::beginUpdate`)

> **Note:** Loading in Kit apps often happens *during* runtime as a long frame, not as a separate phase before the first frame. The 5× median threshold reliably separates loading spikes from runtime frames.

---

## Analysis Path A: nsys SQLite (for .nsys-rep files)

### Step 1: Export to SQLite

```bash
nsys export --type=sqlite -o profile.sqlite profile.nsys-rep --force-overwrite=true
```

### Step 2: Overview + Phases + Frame Analysis

```sql
sqlite3 -header -column profile.sqlite "
WITH frames AS (
  SELECT ROW_NUMBER() OVER (ORDER BY e.start) as n,
         e.start, e.end, (e.end - e.start) as dur_ns
  FROM NVTX_EVENTS e LEFT JOIN StringIds s ON e.textId = s.id
  WHERE COALESCE(e.text, s.value) = 'App Update' AND e.end IS NOT NULL
),
frame_med AS (
  SELECT dur_ns as med FROM frames ORDER BY dur_ns
  LIMIT 1 OFFSET (SELECT COUNT(*)/2 FROM frames)
),
runtime AS (
  SELECT dur_ns FROM frames, frame_med WHERE dur_ns <= med * 5 ORDER BY dur_ns
)
SELECT
  ROUND((SELECT (MIN(start) - (SELECT MIN(start) FROM NVTX_EVENTS)) / 1e9 FROM frames), 2) as startup_sec,
  ROUND((SELECT (MAX(end) - MIN(start)) / 1e9 FROM frames), 2) as total_sec,
  (SELECT COUNT(*) FROM frames) as total_frames,
  (SELECT COUNT(*) FROM frames, frame_med WHERE dur_ns > med * 5) as loading_frames,
  COUNT(*) as runtime_frames,
  ROUND(AVG(dur_ns)/1e6, 2) as mean_ms,
  (SELECT ROUND(dur_ns/1e6,2) FROM runtime LIMIT 1 OFFSET (SELECT COUNT(*)/2 FROM runtime)) as p50_ms,
  (SELECT ROUND(dur_ns/1e6,2) FROM runtime LIMIT 1 OFFSET (SELECT CAST(COUNT(*)*0.95 AS INT) FROM runtime)) as p95_ms,
  ROUND(MIN(dur_ns)/1e6, 2) as min_ms,
  ROUND(MAX(dur_ns)/1e6, 2) as max_ms,
  ROUND(1000.0/(AVG(dur_ns)/1e6), 1) as fps
FROM runtime;
"
```

### Step 3: Top Zones (runtime only, noise excluded)

```sql
sqlite3 -header -column profile.sqlite "
WITH frames AS (
  SELECT ROW_NUMBER() OVER (ORDER BY e.start) as n,
         e.start, e.end, (e.end - e.start) as dur_ns
  FROM NVTX_EVENTS e LEFT JOIN StringIds s ON e.textId = s.id
  WHERE COALESCE(e.text, s.value) = 'App Update' AND e.end IS NOT NULL
),
frame_med AS (
  SELECT dur_ns as med FROM frames ORDER BY dur_ns
  LIMIT 1 OFFSET (SELECT COUNT(*)/2 FROM frames)
),
runtime_bounds AS (
  -- Use the span of runtime frames (≤5x median) as the analysis window
  SELECT MIN(f.start) as t_start, MAX(f.end) as t_end
  FROM frames f, frame_med m WHERE f.dur_ns <= m.med * 5
)
SELECT
  COALESCE(e.text, s.value) as zone_name,
  COUNT(*) as cnt,
  ROUND(AVG(e.end - e.start)/1e6, 3) as avg_ms,
  ROUND(SUM(e.end - e.start)/1e6, 2) as total_ms,
  ROUND(MAX(e.end - e.start)/1e6, 3) as max_ms
FROM NVTX_EVENTS e
LEFT JOIN StringIds s ON e.textId = s.id
CROSS JOIN runtime_bounds rb
WHERE e.start >= rb.t_start AND e.start <= rb.t_end
  AND e.end IS NOT NULL AND (e.end - e.start) > 0
  AND COALESCE(e.text, s.value) NOT LIKE '%Thread waiting%'
  AND COALESCE(e.text, s.value) NOT LIKE 'Carbonite::%'
  AND COALESCE(e.text, s.value) NOT LIKE 'carb::%'
  AND COALESCE(e.text, s.value) NOT IN ('Executing task','Running fiber')
GROUP BY zone_name
HAVING total_ms > 1
ORDER BY total_ms DESC LIMIT 30;
"
```

### SQLite Schema Quick Reference

| Table | Use |
|-------|-----|
| `NVTX_EVENTS` | NVTX ranges/markers. **No `name` column** — use `text` (inline) or join `textId→StringIds.id`. |
| `StringIds` | String lookup (`id` → `value`) |
| `CUPTI_ACTIVITY_KIND_KERNEL` | CUDA kernel launches (**empty for Kit/RTX apps — normal**) |
| `TARGET_INFO_GPU` | GPU hardware info |
| `TARGET_INFO_SYSTEM_ENV` | System environment |

---

## Analysis Path B: Tracy CSV (for .tracy files)

```bash
csvexport profile.tracy > zones.csv
```

**CSV columns:** `name,src_file,src_line,total_ns,total_perc,counts,mean_ns,min_ns,max_ns,std_ns`

Data is **pre-aggregated** — one row per unique zone, covering the entire trace (no phase separation).

```bash
# Top zones, noise filtered
tail -n+2 zones.csv | grep -v -E '^(Carbonite|carb::|Thread waiting|Executing task|Running fiber)' \
  | sort -t',' -k4 -rn | head -30
```

> **Tracy CSV limitation:** No per-invocation timestamps — only aggregates. For phase-aware analysis, prefer the nsys SQLite path.

---

## Two-Version Comparison

### With nsys SQLite (recommended)

```bash
nsys export --type=sqlite -o v1.sqlite v1.nsys-rep --force-overwrite=true
nsys export --type=sqlite -o v2.sqlite v2.nsys-rep --force-overwrite=true
```

Run the overview/frames/zones queries (Steps 2-3) on both databases, save outputs, then compare.

### With Tracy CSV

```bash
csvexport v1.tracy > v1_zones.csv
csvexport v2.tracy > v2_zones.csv
```

Compare with Python:

```python
import csv

def load_zones(path):
    zones = {}
    with open(path) as f:
        for row in csv.DictReader(f):
            zones[row['name']] = {
                'total_ms': int(row['total_ns']) / 1e6,
                'count': int(row['counts']),
                'mean_ms': int(row['mean_ns']) / 1e6,
            }
    return zones

v1, v2 = load_zones('v1_zones.csv'), load_zones('v2_zones.csv')

diffs = []
for name in set(v1) | set(v2):
    t1 = v1.get(name, {}).get('total_ms', 0)
    t2 = v2.get(name, {}).get('total_ms', 0)
    if t1 > 0.1 or t2 > 0.1:  # skip trivial zones
        diffs.append((name, t1, t2, t2 - t1))

print("=== Top Regressions (slower in v2) ===")
for name, t1, t2, d in sorted(diffs, key=lambda x: -x[3])[:15]:
    print(f"  {d:+10.1f}ms  {name}  (v1={t1:.1f}, v2={t2:.1f})")

print("\n=== Top Improvements (faster in v2) ===")
for name, t1, t2, d in sorted(diffs, key=lambda x: x[3])[:15]:
    print(f"  {d:+10.1f}ms  {name}  (v1={t1:.1f}, v2={t2:.1f})")
```

### Report Structure

1. **Overall metrics** — total duration, frame count per version
2. **Phase comparison** — startup time, loading frames count/duration
3. **Frame analysis** — mean frametime, P50, P95, FPS (runtime frames only)
4. **Top regressions** — zones slower in v2, ranked by absolute ms impact
5. **Top improvements** — zones faster in v2
6. **New/removed zones** — zones appearing only in one version
7. **Root cause analysis** — explain *why* the change happened

The goal: not just "FPS dropped 10%" but "FPS dropped 10% because
`rtUpdatePipeline` added 59ms/frame in v2, a new shader pipeline
recompilation step not present in v1."

---
