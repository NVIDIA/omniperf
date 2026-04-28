# Phase 2 Prompt Smoke: perf-tuning

**Prompt:** "Given PresentFrame stalls and GPU saturation, recommend measurable fixes."

## Validation

### Would it answer correctly?
✅ **YES** — The skill directly addresses this scenario:

1. **PresentFrame section:** Two causes identified — GPU backpressure (GPU frametime > CPU frametime) and VNC/remote desktop. Verification command provided (Tracy GPU zones).
2. **GPU-bound fixes (RTX Tuning):** 
   - DLSS execMode=0 (104.9% improvement measured)
   - isaaclab_performance preset (115.8% improvement measured)
   - resolveSamplerFeedback disable (6.72ms/frame saved)
   - HydraEngine waitIdle=false
3. **Measurable:** Each fix has quantified impact from real measurements.
4. **Verification:** Tracy/nsys evidence commands provided.

### Adjacent skill redirects
✅ Clear NOT-for: "NOT for: initial triage (use diagnose-perf), capturing profiles (use profiling), or analyzing traces (use nsys-analyze)."
✅ Assumes bottleneck is already known (correct for this skill's position in the workflow).

### Command safety
| Command | Gated? | Notes |
|---------|--------|-------|
| Kit args (`--/...`) | Config flags | Applied at launch time |
| `echo performance \| sudo tee ...` | Explicit sudo | CPU governor change |
| Python settings code | Runtime config | Informational |

### Dry-run suitability
✅ All recommendations are configuration changes. The agent can recommend specific flags and expected improvements without executing workloads.

### Strengths
- Quantified improvements with specific hardware context (RTX PRO 6000 Blackwell).
- Clear tuning checklist (5 steps in order of impact).
- DLSS-G warning about measurement vs display FPS — prevents a common misinterpretation.

## Result: ✅ PASS

Excellent evidence-based tuning guide. Every fix is measurable with quantified expected impact.
