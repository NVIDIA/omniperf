# OmniPerf Agent Skills

Agent skills for performance engineering across the NVIDIA Omniverse stack (Isaac Sim, Isaac Lab, Kit SDK). Each skill is a self-contained guide that an AI agent loads on-demand to perform specific tasks.

## Skills

### Setup & Installation

| Skill | Description |
|---|---|
| [install-isaacsim](install-isaacsim/) | Install Isaac Sim via pip, source build, or Docker |
| [install-isaaclab](install-isaaclab/) | Install Isaac Lab for full Isaac Sim-backed or kit-less/Newton workflows |
| [install-profilers](install-profilers/) | Install nsys, sqlite3, Tracy csvexport/capture/update tools |

### Benchmarking

| Skill | Description |
|---|---|
| [benchmark-isaacsim](benchmark-isaacsim/) | Run Isaac Sim benchmark scripts and interpret outputs |
| [benchmark-isaaclab](benchmark-isaaclab/) | Run Isaac Lab throughput/camera/startup benchmarks and interpret outputs |

### Profiling & Analysis

| Skill | Description |
|---|---|
| [profiling](profiling/) | Capture CPU ChromeTrace, Tracy, and nsys/NVTX traces and hand off exports for analysis |
| [profiling-api](profiling-api/) | Add profiling zones to C++/Python code (macros, API, masks, channels) |
| [nsys-analyze](nsys-analyze/) | Analyze captured traces (NVTX zones, Tracy Statistics, phase detection, version comparison) |
| [tracy-memory](tracy-memory/) | Profile CPU/GPU memory allocations via Tracy memory channels |
| [nvtx-python](nvtx-python/) | Python function tracing with NVTX for non-Kit environments |

### Performance

| Skill | Description |
|---|---|
| [diagnose-perf](diagnose-perf/) | Quick triage — identify bottleneck category without profiling tools |
| [perf-tuning](perf-tuning/) | Apply specific fixes for known performance issues |

## Workflow

```
Install               Benchmark              Profile & Fix
───────               ─────────              ─────────────
install-isaacsim  ──→ benchmark-isaacsim ──→ diagnose-perf (quick triage)
install-isaaclab  ──→ benchmark-isaaclab     │
install-profilers                            ├→ profiling (capture traces)
                                             ├→ nsys-analyze (analyze traces)
                                             ├→ tracy-memory (memory allocation traces)
                                             └→ perf-tuning (apply fixes)
```

Specialized profiling:
- **profiling-api** — when writing new code that needs profiling zones
- **tracy-memory** — when investigating memory leaks or allocation hotspots
- **nvtx-python** — when profiling Python in standalone Isaac Lab (no Kit runtime)

Routing boundaries:
- Use **benchmark-*** skills to run benchmark scripts and read benchmark outputs, not to diagnose or fix bottlenecks.
- Use **diagnose-perf** for first-pass bottleneck triage before full profiling.
- Use **profiling** to follow the guide-aligned COLD/WARM/TRACY method and capture CPU ChromeTrace, Tracy, or nsys/NVTX traces; use **nsys-analyze** for Tracy Statistics/Range Limit and deeper trace analysis.
- Use **perf-tuning** only after the bottleneck category or trace evidence is known.

## Adding Skills

Each skill is a directory containing a `SKILL.md` with YAML frontmatter (`name`, `description`) and markdown instructions. Optional subdirectories: `references/` for detailed docs loaded on-demand, `scripts/` for executable helpers.

## Sources

The profiling guide [dev/docs/profiling-guide.md](../../dev/docs/profiling-guide.md) is the source of truth for profiling-related skills and any overlapping benchmark, diagnosis, or tuning guidance.
