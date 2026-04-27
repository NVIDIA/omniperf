# OmniPerf Agent Skills

Agent skills for performance engineering across the NVIDIA Omniverse stack (Isaac Sim, Isaac Lab, Kit SDK). Each skill is a self-contained guide that an AI agent loads on-demand to perform specific tasks.

## Skills

### Setup & Installation

| Skill | Description |
|---|---|
| [install-isaacsim](install-isaacsim/) | Install Isaac Sim via pip, source build, or Docker |
| [install-isaaclab](install-isaaclab/) | Install Isaac Lab with conda and link Isaac Sim |
| [install-profilers](install-profilers/) | Install nsys, Tracy (csvexport, capture), and sqlite3 |

### Benchmarking

| Skill | Description |
|---|---|
| [benchmark-isaacsim](benchmark-isaacsim/) | Run Isaac Sim benchmarks (camera, SDG, robots, sensors) |
| [benchmark-isaaclab](benchmark-isaaclab/) | Run Isaac Lab benchmarks (RL training, env step FPS, cameras) |

### Profiling & Analysis

| Skill | Description |
|---|---|
| [profiling](profiling/) | Capture traces with Tracy and Nsight Systems |
| [profiling-api](profiling-api/) | Add profiling zones to C++/Python code (macros, API, masks, channels) |
| [nsys-analyze](nsys-analyze/) | Analyze captured traces (NVTX zones, phase detection, version comparison) |
| [tracy-memory](tracy-memory/) | Profile CPU/GPU memory allocations via Tracy |
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
                                             └→ perf-tuning (apply fixes)
```

Specialized profiling:
- **profiling-api** — when writing new code that needs profiling zones
- **tracy-memory** — when investigating memory leaks or allocation hotspots
- **nvtx-python** — when profiling Python in standalone Isaac Lab (no Kit runtime)

## Adding Skills

Each skill is a directory containing a `SKILL.md` with YAML frontmatter (`name`, `description`) and markdown instructions. Optional subdirectories: `references/` for detailed docs loaded on-demand, `scripts/` for executable helpers.

## Sources

The profiling-related skills (`profiling`, `profiling-api`, `perf-tuning`, `tracy-memory`, `nvtx-python`) were derived from [dev/docs/profiling-guide.md](../../dev/docs/profiling-guide.md). The remaining skills (`install-*`, `benchmark-*`, `diagnose-perf`, `nsys-analyze`) were authored independently.
