# Phase 2 Prompt Smoke: benchmark-isaaclab

**Prompt:** "Plan a tiny Isaac Lab env-step FPS smoke test."

## Validation

### Would it answer correctly?
✅ **YES** — The skill provides:
1. `benchmark_non_rl.py` as the primary env-step FPS script.
2. Key params: `--task`, `--num_envs`, `--num_frames`.
3. Example tasks at various env counts.
4. A "tiny" test would be: `./isaaclab.sh -p scripts/benchmarks/benchmark_non_rl.py --task=Isaac-Cartpole-Direct-v0 --num_envs=16 --num_frames=10`
5. Output format: JSON with phases/measurements.

### Adjacent skill redirects
✅ References `install-isaaclab` for setup.
✅ References `profiling` for os._exit patch and trace capture.
✅ Clearly notes `--headless` deprecation (use `--viz none`).

### Command safety
| Command | Gated? | Notes |
|---------|--------|-------|
| `./isaaclab.sh -p scripts/benchmarks/...` | GPU workload | Not auto-executed |
| Batch suite scripts | GPU workload | Not auto-executed |

### Dry-run suitability
✅ Perfect for planning. The agent can recommend exact command with small `--num_envs` and `--num_frames` without running it.

### Warnings
⚠️ **Minor:** The skill notes that `benchmark_lazy_export.py`, `benchmark_view_comparison.py`, and `benchmark_xform_prim_view.py` do NOT support `--benchmark_backend` or `--output_path`. Good documentation of edge cases.

⚠️ **Note:** The `--headless` deprecation is clearly called out: "Omit `--viz` for headless mode, or use `--viz none`". However, the Isaac Lab nsys example in the `profiling` skill still uses `--headless`. Minor inconsistency.

## Result: ✅ PASS (with minor cross-skill inconsistency)

The `profiling` skill example uses deprecated `--headless` flag for Isaac Lab. Should be updated to `--viz none`.
