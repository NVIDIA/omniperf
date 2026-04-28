# Phase 2 Prompt Smoke: benchmark-isaacsim

**Prompt:** "Plan a tiny headless Isaac Sim benchmark smoke test."

## Validation

### Would it answer correctly?
✅ **YES** — The skill provides:
1. Script table with all available benchmarks and their key params.
2. Common params including `--num-frames` (can be set low for smoke test).
3. Critical gotchas (hyphens not underscores, headless viewport waste, JWT tokens).
4. Output file expectations (`kpis_benchmark_*.json`).

A plan for a tiny smoke test would be:
- Use `benchmark_camera.py --num-cameras 1 --resolution 640 480 --num-frames 10`
- Or `benchmark_scene_loading.py --env-url <local_scene> --num-frames 10`
- Apply os._exit patch first, set CPU governor.

### Adjacent skill redirects
✅ References `install-isaacsim` for setup.
✅ References `profiling` for os._exit patch and Tracy.
✅ References `perf-tuning` for headless/governor/viewport tuning.

### Command safety
| Command | Gated? | Notes |
|---------|--------|-------|
| `./python.sh <benchmark>` | GPU workload | Not executed in plan mode |
| `kill -9` | Explicit — for hung processes only | Clearly gated with conditions |
| viewport destroy code | Python snippet | Informational |

### Dry-run suitability
✅ The skill is informational enough to construct a plan without running anything. All heavy commands are clearly workload commands, not auto-executed.

### Warnings
⚠️ **Minor:** The "Before Running Any Benchmark" section says "Apply the os._exit(0) patch — see profiling skill" but doesn't inline the patch. An agent following this skill for planning would need to cross-reference. This is fine for skill selection but adds a hop.

## Result: ✅ PASS

Well-structured for planning. The HYPHENS gotcha is excellent and would prevent a common silent-failure mode.
