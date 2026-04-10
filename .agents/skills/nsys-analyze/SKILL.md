---
name: nsys-analyze
description: Analyze profiling data from Kit-based apps. Covers Omniverse-specific NVTX zone interpretation, phase detection config, and two-version comparison methodology.
---

# Profile Analysis for Omniverse / Kit-based Apps

This skill covers how to interpret and compare profiling data from Kit, Isaac Sim, and Isaac Lab.
For capturing profiles, see the `profiling` skill.

## Omniverse NVTX Zone Reference

These zone patterns appear in Tracy and Nsight profiles of all Kit-based applications:

| Zone Pattern | Meaning | Phase |
|---|---|---|
| `App::beginUpdate` / `App::endUpdate` | Frame boundaries | Runtime |
| `App::startup` / `App::shutdown` | Application lifecycle | Startup/Shutdown |
| `UsdFileOp::newStage` | Stage creation | Startup→Loading transition |
| `UsdContext::Impl::render` | USD render context | Loading→Runtime transition |
| `Hydra::*` | Hydra render delegate ops | Runtime |
| `OmniGraph::*` | OmniGraph compute | Runtime |
| `Fabric::*` | Fabric data operations | Runtime |
| `Carbonite::*` | Low-level framework (noise) | All |

## Phase Detection Configuration

Kit-based apps have distinct execution phases: startup, loading, runtime, shutdown.
Use this TOML config for phase-aware analysis tools:

```toml
# .nsys-analyzer.toml — Omniverse profile config
startup_end_marker_pattern = "UsdFileOp::newStage"
loading_stabilization_zone_pattern = "UsdContext::Impl::render"
loading_stabilization_cv_threshold = 0.15
loading_stabilization_window_size = 5
loading_stabilization_consecutive = 3
frame_marker_pattern = "App::beginUpdate"

startup_extra_keywords = ["carbonite", "omniverse", "kit", "fabric"]
loading_extra_keywords = ["usd", "hydra", "stage", "prim", "mdl"]
global_exclude_patterns = ["^Carbonite::Framework::", "^carb::"]
```

## Two-Version Comparison Methodology

When comparing profiling captures between two versions (e.g., v5.1.0 vs v6.0.0):

### Data to collect for each version
1. **Full analysis** — bottleneck detection, issue ranking
2. **Overview** — total duration, zone count
3. **Phase breakdown** — startup, loading, runtime, shutdown durations
4. **Frame patterns** — mean frametime, P95 frametime, stability (CV)
5. **Top zones by duration** — top 30 zones sorted by total time

### Report structure
1. **Overall metrics** — total duration, zone count, GPU utilization
2. **Phase comparison** — startup, loading, runtime, shutdown for both versions
3. **Frame analysis** — mean frametime, P95 frametime, CV
4. **Top regressions** — zones that got slower, ranked by absolute time impact
5. **Top improvements** — zones that got faster
6. **New/resolved issues** — issues appearing or disappearing between versions
7. **Root cause analysis** — WHY the regression/improvement happened

The goal is not just "FPS dropped 10%" but "FPS dropped 10% because
rtUpdatePipeline added 59ms/frame in v6.0.0, a new shader pipeline
recompilation step not present in v5.1.0."

## nsys-analyzer CLI (if available)

nsys-analyzer is a Rust-based high-performance analyzer for `.nsys-rep`, `.sqlite`, and `.tracy` files.
It auto-detects GPU starvation, memory bottlenecks, CPU bottlenecks, frame patterns, and application phases.

<!-- TODO: Update with public release URL when nsys-analyzer is published -->

### Key commands
```bash
nsys-analyzer analyze profile.tracy --config .nsys-analyzer.toml --format claude
nsys-analyzer overview profile.tracy
nsys-analyzer phases profile.tracy --config .nsys-analyzer.toml
nsys-analyzer frames profile.tracy
nsys-analyzer nvtx profile.tracy --sort duration --limit 30
nsys-analyzer issue profile.tracy <issue-id>
```

### Two-version comparison workflow
```bash
# Run on both profiles
for v in v1 v2; do
  nsys-analyzer analyze $v.tracy --config .nsys-analyzer.toml --format claude > analysis_$v.txt 2>&1
  nsys-analyzer overview $v.tracy > overview_$v.txt 2>&1
  nsys-analyzer phases $v.tracy --config .nsys-analyzer.toml > phases_$v.txt 2>&1
  nsys-analyzer frames $v.tracy > frames_$v.txt 2>&1
  nsys-analyzer nvtx $v.tracy --sort duration --limit 30 > zones_$v.txt 2>&1
done
# Read ALL 10 output files before writing the comparison report
```

**Requires:** `csvexport` on PATH for `.tracy` files, `nsys` on PATH for `.nsys-rep` files.

## Fallback: Manual Analysis Without nsys-analyzer

If nsys-analyzer is not available, use Tracy CSV export or nsys SQLite export directly.
See the `profiling` skill for SQLite query examples and csvexport usage.

For manual two-version comparison:
```bash
# Export both profiles
csvexport v1.tracy > v1_zones.csv
csvexport v2.tracy > v2_zones.csv

# Compare top zones (aggregate by name, sort by total time)
# Use Python/awk to pivot and diff the zone timing data
```

---
