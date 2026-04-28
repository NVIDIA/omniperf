# Phase 2 Prompt Smoke: install-isaaclab

**Prompt:** "Plan an Isaac Lab install linked to an existing Isaac Sim. Do not install."

## Validation

### Would it answer correctly?
✅ **YES** — The skill provides a clear 6-step sequence:
1. Prerequisite: Isaac Sim installed (references `install-isaacsim` skill).
2. Install Miniconda if missing.
3. Clone repo.
4. Link Isaac Sim via symlink.
5. Create conda env (`./isaaclab.sh -c isaaclab_env`).
6. Install deps (`./isaaclab.sh -i`).
7. Verify with import check + minimal benchmark.

For planning, the agent can enumerate these steps without executing.

### Adjacent skill redirects
✅ Correctly directs to `install-isaacsim` as prerequisite (Step 1).
✅ Referenced by `benchmark-isaaclab` for setup.

### Command safety
| Command | Gated? | Notes |
|---------|--------|-------|
| `which conda` | N/A (read-only) | Safe |
| `wget ... miniconda.sh` | Network download | Requires approval |
| `bash /tmp/miniconda.sh -b` | Install | Requires approval |
| `git clone` | Network + disk | Requires approval |
| `conda env remove` | Destructive | Only in troubleshooting section, explicit |
| `./isaaclab.sh -c` | Creates conda env | Requires approval |

### Dry-run suitability
✅ Each step is clearly delineated. An agent can present the plan without executing.

### Warnings
⚠️ **Minor:** The skill assumes conda is the ONLY install method. Isaac Lab 3.0+ also supports `uv`/`pip` venvs (per the `nvtx-python` skill which uses `uv run`). The skill could mention this alternative.

## Result: ✅ PASS (with minor note)

Minor gap: no mention of uv/pip-based Isaac Lab install path (relevant for Isaac Lab 3.0+ standalone).
