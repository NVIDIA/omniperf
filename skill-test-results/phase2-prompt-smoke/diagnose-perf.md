# Phase 2 Prompt Smoke: diagnose-perf

**Prompt:** "Given low FPS in Isaac Sim, perform a no-profiling triage plan."

## Validation

### Would it answer correctly?
✅ **YES** — The skill is explicitly designed for this exact scenario. It provides:
1. Phase 1: System snapshot commands (nvidia-smi, CPU governor, memory) — all read-only.
2. Phase 2: Runtime GPU monitoring (`nvidia-smi dmon`, process checks).
3. Phase 3: Bottleneck classification decision tree (GPU/CPU/VRAM/loading/idle).
4. Phase 4: Quick wins ordered by impact.
5. A structured triage report template.

The skill is the best match in the entire skill set for "no-profiling triage."

### Adjacent skill redirects
✅ Correctly escalates to `profiling` and `nsys-analyze` for deeper analysis.
✅ References `perf-tuning` for applying fixes.
✅ Clear NOT-for boundaries: "NOT for applying specific fixes (use perf-tuning), capturing traces (use profiling), or analyzing traces (use nsys-analyze)."

### Command safety
| Command | Gated? | Notes |
|---------|--------|-------|
| `nvidia-smi -q` | N/A (read-only) | Safe |
| `nvidia-smi dmon` | N/A (read-only) | Safe |
| `cat /sys/devices/system/cpu/...` | N/A (read-only) | Safe |
| `free -h` | N/A (read-only) | Safe |
| `top -bn1 -p PID` | N/A (read-only) | Safe |
| `sudo cpupower frequency-set` | Yes — explicit sudo | Noted as may be read-only in containers |

### Dry-run suitability
✅ All Phase 1-3 commands are non-destructive. The skill naturally produces a plan/report without requiring installs or workloads.

## Result: ✅ PASS

Excellent skill for this prompt. Clear boundaries, safe commands, actionable decision tree.
