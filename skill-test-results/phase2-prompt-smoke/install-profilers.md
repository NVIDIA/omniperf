# Phase 2 Prompt Smoke: install-profilers

**Prompt:** "Check what profiler tools are installed and tell me the missing install steps. Do not install anything."

## Validation

### Would it answer correctly?
✅ **YES** — The skill starts with a "Quick Check" section containing exact bash one-liners to detect `nsys`, `csvexport`, `tracy-capture`, and `sqlite3`. It would produce clear "OK" / "MISSING" output per tool. For missing tools, it provides install instructions without auto-executing them.

### Adjacent skill redirects
✅ Correctly references the `profiling` and `nsys-analyze` skills as downstream consumers.

### Command safety
| Command | Gated? | Notes |
|---------|--------|-------|
| `nsys --version` | N/A (read-only) | Safe |
| `sudo apt-get install` | Yes — explicit | User must approve |
| `sudo dpkg -i` | Yes — explicit | User must approve |
| `sudo ln -sf` | Yes — explicit | User must approve |
| `git clone` + `cmake --build` | Yes — manual steps | User must approve |
| `sudo cp ... /usr/local/bin/` | Yes — explicit | User must approve |

### Dry-run suitability
✅ The "Quick Check" section is completely non-mutating — perfect for a plan-only response. The skill clearly separates detection (safe) from installation (requires approval).

## Result: ✅ PASS

No defects found. Skill is well-structured for the "check but don't install" use case.
