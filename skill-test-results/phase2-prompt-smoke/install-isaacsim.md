# Phase 2 Prompt Smoke: install-isaacsim

**Prompt:** "Plan a pip-based Isaac Sim install for version 5.1 on Ubuntu. Do not install."

## Validation

### Would it answer correctly?
✅ **YES** — The skill has:
1. A Python version matrix (5.1 → Python 3.11).
2. Clear venv setup instructions (Options A/B/C).
3. Explicit `pip install 'isaacsim==5.1.0.0'` command.
4. A verification command (`python -c "import isaacsim; print('OK')"`).

For a "plan only" response, the agent would outline: create Python 3.11 venv → pip install isaacsim==5.1.0.0 → verify import. All actionable without executing.

### Adjacent skill redirects
✅ References `profiling` skill for os._exit patch.
✅ Referenced BY `install-isaaclab` as prerequisite.

### Command safety
| Command | Gated? | Notes |
|---------|--------|-------|
| `python3 --version` | N/A (read-only) | Safe |
| `sudo add-apt-repository` | Yes — explicit sudo | User must approve |
| `pip install isaacsim` | Yes — inside venv context | Non-destructive to system |
| `sudo apt-get install docker.io` | Yes — Method 2 only | Not needed for pip path |
| `sudo chmod 666 /var/run/docker.sock` | Yes — Method 2 only | Security-sensitive, flagged |

### Dry-run suitability
✅ The skill is well-structured for planning — each method is self-contained and the pip path requires no sudo for the core install (only for deadsnakes PPA if Python version is missing).

## Result: ✅ PASS

No defects found for the pip install path. The Docker socket `chmod 666` in Method 2 is a security concern but is clearly scoped to source-build only and not invoked for pip installs.
