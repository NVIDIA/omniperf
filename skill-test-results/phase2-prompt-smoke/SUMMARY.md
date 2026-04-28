# Phase 2 — Skill Prompt / Selection Smoke Tests: SUMMARY

**Date:** 2026-04-28
**Phase:** 2 (Prompt-level dry-run validation)
**Method:** Read each SKILL.md, evaluate against its representative prompt from TEST_PLAN.md Phase 2, validate answer quality, adjacent-skill redirects, command safety, and dry-run suitability.

## Results Table

| Skill | Status | Representative Prompt | Notes |
|-------|--------|----------------------|-------|
| `install-profilers` | ✅ PASS | Check installed profiler tools | Clean separation of detect vs install |
| `install-isaacsim` | ✅ PASS | Plan pip Isaac Sim 5.1 install | Python version matrix excellent |
| `install-isaaclab` | ✅ PASS | Plan Isaac Lab + existing Isaac Sim | Minor: no uv/pip install path |
| `diagnose-perf` | ✅ PASS | No-profiling triage for low FPS | Excellent decision tree, all read-only |
| `benchmark-isaacsim` | ✅ PASS | Tiny headless smoke test plan | HYPHENS gotcha is critical value-add |
| `benchmark-isaaclab` | ✅ PASS | Tiny env-step FPS smoke test plan | Cross-skill `--headless` inconsistency |
| `profiling` | ⚠️ WARNING | 10-second nsys capture plan | `sudo` not gated, deprecated flag, container note missing |
| `nsys-analyze` | ✅ PASS | Analysis commands + expected tables | Copy-pastable SQL, excellent schema ref |
| `nvtx-python` | ✅ PASS | Minimal Python NVTX test | Minor: sitecustomize.py conflict risk |
| `profiling-api` | ✅ PASS | C++ and Python zone examples | Pure reference, no safety concerns |
| `tracy-memory` | ⚠️ WARNING | Tracy memory capture plan | Path inconsistencies, missing discovery cmd |
| `perf-tuning` | ✅ PASS | PresentFrame + GPU saturation fixes | Quantified impact, evidence-based |

**Summary: 10 PASS, 2 WARNING, 0 FAIL**

## Concrete Doc Defects

### D1: `profiling` — `sudo` in nsys command not gated (MEDIUM)
**File:** `profiling/SKILL.md`, Nsys Command section
**Issue:** `sudo -E nsys profile` presented as the default. On DGX, containers, and many setups, nsys works without sudo.
**Fix:** Add note: "Try without sudo first; `sudo` is only needed when `perf_event_paranoid > 2` and you need CPU sampling. In containers, sudo may not be available."

### D2: `profiling` — Deprecated `--headless` flag in Isaac Lab example (MINOR)
**File:** `profiling/SKILL.md`, Isaac Lab with Nsight example
**Issue:** Uses `--headless` which is deprecated per `benchmark-isaaclab` skill.
**Fix:** Replace `--headless` with `--viz none` in the Isaac Lab nsys example.

### D3: `profiling` — Container note for `--gpu-metrics-devices` missing (MINOR)
**File:** `profiling/SKILL.md`, Nsys Command section
**Issue:** `--gpu-metrics-devices=all` may fail with `ERR_NVGPUCTRPERM` in containers. This is documented in `install-profilers` but not in the nsys command section of `profiling`.
**Fix:** Add inline note or cross-reference to `install-profilers` container notes.

### D4: `tracy-memory` — Missing discovery command for liballocwrapper.so (MINOR)
**File:** `tracy-memory/SKILL.md`, Step 1
**Issue:** Uses `<version>` placeholder in LD_PRELOAD path but provides no command to find the actual path.
**Fix:** Add: `find ~/.cache/packman -name liballocwrapper.so 2>/dev/null` before the export.

### D5: `tracy-memory` — Tracy binary path inconsistent with install-profilers (MINOR)
**File:** `tracy-memory/SKILL.md`, Steps 3-4
**Issue:** Uses `./tracy/capture` and `./tracy/update` but `install-profilers` installs to `/usr/local/bin/tracy-capture`.
**Fix:** Use `tracy-capture` (PATH-resolved) instead of `./tracy/capture`. Same for `update` → reference it as the Tracy `update` utility.

### D6: `install-isaaclab` — No uv/pip install path mentioned (MINOR)
**File:** `install-isaaclab/SKILL.md`
**Issue:** Only documents conda-based install. Isaac Lab 3.0+ supports uv/pip venvs (as implied by `nvtx-python` skill which uses `uv run`).
**Fix:** Add a brief "Alternative: uv/pip install" section or note that conda is not the only option.

## Cross-Skill Consistency Issues

1. **`--headless` deprecation:** `benchmark-isaaclab` correctly notes it's deprecated, but `profiling` still uses it in an Isaac Lab example.
2. **Tracy binary naming:** `install-profilers` installs `tracy-capture` to PATH; `tracy-memory` references `./tracy/capture`. Should be consistent.
3. **Container limitations:** `install-profilers` has good container notes for nsys; `profiling` does not cross-reference them.

## Skill Selection Quality

All 12 skills have clear, non-overlapping descriptions with explicit trigger conditions and NOT-for boundaries. The skill selection system would correctly route each representative prompt to the intended skill. No prompt would be ambiguously routed between skills.

## Adjacent Skill Redirect Quality

All skills correctly reference their neighbors:
- Install skills → referenced by benchmark/profiling skills as prerequisites
- `diagnose-perf` → escalates to `profiling` + `nsys-analyze`
- `profiling` → sends analysis to `nsys-analyze`, zones to `profiling-api`
- `nsys-analyze` → sends fixes to `perf-tuning`
- `perf-tuning` → assumes prior diagnosis from `diagnose-perf` or profiling pipeline

The skill graph forms a coherent workflow: **install → diagnose → profile → analyze → tune**.

## Files Written

```
omniperf/skill-test-results/phase2-prompt-smoke/
├── SUMMARY.md              (this file)
├── install-profilers.md
├── install-isaacsim.md
├── install-isaaclab.md
├── diagnose-perf.md
├── benchmark-isaacsim.md
├── benchmark-isaaclab.md
├── profiling.md
├── nsys-analyze.md
├── nvtx-python.md
├── profiling-api.md
├── tracy-memory.md
└── perf-tuning.md
```
