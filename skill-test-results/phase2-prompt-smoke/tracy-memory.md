# Phase 2 Prompt Smoke: tracy-memory

**Prompt:** "Plan a Tracy memory capture and explain required `LD_PRELOAD` handling."

## Validation

### Would it answer correctly?
✅ **YES** — The skill covers exactly this:
1. **LD_PRELOAD setup** — `liballocwrapper.so` path from packman cache.
2. **Kit flags** — CPU memory (`omni.cpumemorytracking`, `cpu.memory` channel) and GPU memory (`carb.memorytracking.plugin`, `graphics.memory` channel).
3. **Critical: unset LD_PRELOAD before capture binary** — clearly highlighted.
4. **Strip test verification** — compare file sizes to confirm memory data was captured.
5. **Kit log verification** — two specific log lines to look for.
6. **Common mistakes** — 5 pitfalls listed.

### Adjacent skill redirects
✅ References `profiling` skill for Tracy capture setup.
✅ References `install-profilers` for binaries.

### Command safety
| Command | Gated? | Notes |
|---------|--------|-------|
| `export LD_PRELOAD=...` | Env var set | Scoped to current shell |
| Kit launch with flags | GPU workload | Not auto-executed |
| `./tracy/capture -o ...` | File creation | Requires running app |
| `./tracy/update -s M ...` | File creation | Reads existing trace |

### Dry-run suitability
✅ Perfect for planning. The skill describes a sequence the agent can present step-by-step without executing.

### Warnings
⚠️ **Minor:** The LD_PRELOAD path `~/.cache/packman/chk/allocmemwrapper/<version>/liballocwrapper.so` uses a `<version>` placeholder but doesn't provide a command to discover the actual version/path. Should add: `find ~/.cache/packman -name liballocwrapper.so` or `ls ~/.cache/packman/chk/allocmemwrapper/`.

⚠️ **Minor:** Uses `./tracy/capture` and `./tracy/update` which assumes Tracy binaries are in a `./tracy/` directory. The `install-profilers` skill installs to `/usr/local/bin/`. Inconsistent binary paths between skills.

## Result: ⚠️ WARNING

Correct and well-structured, but:
1. Missing discovery command for the actual `liballocwrapper.so` path.
2. Tracy binary path (`./tracy/capture`) inconsistent with `install-profilers` (`/usr/local/bin/tracy-capture`).
