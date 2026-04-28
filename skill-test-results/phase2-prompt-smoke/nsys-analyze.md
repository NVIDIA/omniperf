# Phase 2 Prompt Smoke: nsys-analyze

**Prompt:** "Given a `.nsys-rep`, list the analysis commands and expected tables."

## Validation

### Would it answer correctly?
✅ **YES** — The skill provides exactly what's asked:
1. Export command: `nsys export --type=sqlite -o profile.sqlite profile.nsys-rep`
2. Full SQL queries for:
   - Overview/phases/frame analysis (Step 2)
   - Top zones with noise exclusion (Step 3)
3. SQLite schema quick reference table (NVTX_EVENTS, StringIds, CUPTI tables, TARGET_INFO_*).
4. The critical NVTX_EVENTS gotcha (no `name` column — use `text` or join `textId`).
5. Tracy CSV alternative path.
6. Two-version comparison methodology.

### Adjacent skill redirects
✅ References `profiling` for capture.
✅ References `install-profilers` for tool setup.
✅ References `perf-tuning` for applying fixes.
✅ Clear NOT-for boundaries.

### Command safety
| Command | Gated? | Notes |
|---------|--------|-------|
| `nsys export` | File creation | Creates .sqlite from existing .nsys-rep — safe |
| `sqlite3 ... SELECT` | Read-only query | Safe |
| `csvexport` | File creation | Creates .csv from existing .tracy — safe |
| Python comparison script | Read-only analysis | Safe |

### Dry-run suitability
✅ Entirely analysis-focused. All commands are read-only on existing trace data. Perfect for a "list the commands" response.

## Result: ✅ PASS

Excellent skill. Comprehensive, copy-pastable queries, clear schema reference, safe commands.
