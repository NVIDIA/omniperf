# Phase 2 Prompt Smoke: profiling

**Prompt:** "Plan a 10-second Nsight Systems capture for a Kit app."

## Validation

### Would it answer correctly?
✅ **YES** — The skill provides:
1. Nsight Systems Kit args (NVTX backend configuration).
2. Exact `nsys profile` command with recommended flags.
3. Environment variables (`CARB_PROFILING_PYTHON=1`).
4. SQLite export command for analysis.
5. Product-specific examples for Isaac Sim and Isaac Lab.

For a 10-second capture, the agent would plan:
- Set env vars
- Run: `nsys profile -t nvtx,cuda,osrt --gpu-metrics-devices=all -d 10 <app_command> <kit_args>`
- Export: `nsys export --type=sqlite -o profile.sqlite profile.nsys-rep`

### Adjacent skill redirects
✅ Directs to `nsys-analyze` for analysis.
✅ Directs to `install-profilers` for tool installation.
✅ Directs to `profiling-api` for adding zones.
✅ Clear NOT-for boundaries in description.

### Command safety
| Command | Gated? | Notes |
|---------|--------|-------|
| `sudo -E nsys profile` | Explicit sudo | Required for full tracing; noted |
| `pkill -f tracy-capture` | Semi-destructive | Only kills Tracy processes; gated in sequence |
| `kill -9 <pid>` | Explicit — hung process only | Clearly conditional |
| `sed -i` (os._exit patch) | File modification | Clearly marked MANDATORY with explanation |

### Dry-run suitability
✅ The skill is reference-heavy and supports planning well. An agent can present the nsys command structure without executing.

### Warnings
⚠️ **Medium:** The nsys command uses `sudo -E nsys profile`. In many environments (containers, DGX), nsys works without sudo. The skill doesn't mention the non-sudo path. Adding a note like "Try without sudo first; only needed for CPU sampling on hosts with perf_event_paranoid > 2" would improve it.

⚠️ **Minor:** The Isaac Lab nsys example uses `--headless` which is deprecated per the `benchmark-isaaclab` skill. Should use `--viz none`.

⚠️ **Minor:** The `--gpu-metrics-devices=all` flag may fail with `ERR_NVGPUCTRPERM` in containers (noted in `install-profilers` but not repeated here).

## Result: ⚠️ WARNING

Functional and correct, but:
1. `sudo` usage in nsys command not adequately gated (should note it's optional in many environments).
2. Deprecated `--headless` flag in Isaac Lab example.
3. Container compatibility note for `--gpu-metrics-devices` missing from this skill (only in install-profilers).
