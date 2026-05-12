# =============================================================================
# Hierarchy Depth Analyzer — ASYNC, USD-only
# -----------------------------------------------------------------------------
# Reports:
#   - Max / mean / median / p95 / p99 depth across all prims
#   - Depth histogram (count of prims at each depth level)
#   - Branch-factor distribution (children per non-leaf prim)
#   - Top-N deepest prim paths
#   - Top-N widest prims (most direct children)
#
# IP-safe: COUNT only — paths are needed but no geometry data.
# Read-only. Re-running cancels previous run.
# =============================================================================

# ---- Tuning ----------------------------------------------------------------
TOP_N                    = 20
YIELD_EVERY              = 5000     # yield to Kit UI every N prims
OUTPUT_CSV               = "./hierarchy_depth.csv"

# ---------------------------------------------------------------------------
import asyncio
import csv
import math
import statistics
import traceback
from collections import Counter, defaultdict
import omni.kit.app
import omni.usd

# ---- Cancel any previous run -----------------------------------------------
_prev = globals().get("_HIERARCHY_DEPTH_TASK")
if _prev is not None and not _prev.done():
    _prev.cancel()


def _pct(values, p):
    if not values:
        return 0
    s = sorted(values)
    k = max(0, min(len(s) - 1, int(math.ceil(p * len(s))) - 1))
    return s[k]


async def _hier_main():
    stage = omni.usd.get_context().get_stage()
    if not stage:
        print("[error] no stage open")
        return
    root = stage.GetRootLayer().identifier if stage.GetRootLayer() else "?"
    print(f"[stage] {root}")

    depth_counter = Counter()
    branch_counter = Counter()
    deepest = []         # (depth, path_str)
    widest = []          # (n_children, path_str)

    n = 0
    n_yield_chunk = 0

    # Use TraverseAll so we don't skip instance proxies / disabled prims
    for prim in stage.TraverseAll():
        path = prim.GetPath()
        depth = path.pathElementCount  # absolute depth from root
        depth_counter[depth] += 1

        kids = prim.GetChildren()
        nkids = len(kids)
        if nkids > 0:
            branch_counter[nkids] += 1
            widest.append((nkids, str(path)))

        deepest.append((depth, str(path)))

        n += 1
        n_yield_chunk += 1
        if n_yield_chunk >= YIELD_EVERY:
            n_yield_chunk = 0
            await omni.kit.app.get_app().next_update_async()
            if (n % (YIELD_EVERY * 5)) == 0:
                print(f"  ... {n:,} prims scanned")

    if n == 0:
        print("[error] stage has 0 prims")
        return

    # ---- Stats ----
    depths = [d for d, _ in deepest]
    max_d = max(depths)
    mean_d = statistics.mean(depths)
    med_d = statistics.median(depths)
    p95 = _pct(depths, 0.95)
    p99 = _pct(depths, 0.99)

    print()
    print("=" * 78)
    print("HIERARCHY DEPTH SUMMARY")
    print("=" * 78)
    print(f"  Total prims          : {n:,}")
    print(f"  Max depth            : {max_d}")
    print(f"  Mean depth           : {mean_d:.2f}")
    print(f"  Median depth         : {med_d}")
    print(f"  p95 depth            : {p95}")
    print(f"  p99 depth            : {p99}")

    print()
    print("=" * 78)
    print("DEPTH HISTOGRAM (prim count by depth)")
    print("=" * 78)
    max_depth_seen = max(depth_counter.keys())
    max_count = max(depth_counter.values())
    bar_max = 50
    for d in range(0, max_depth_seen + 1):
        c = depth_counter.get(d, 0)
        bar = "#" * max(0, int(bar_max * c / max_count)) if max_count else ""
        print(f"  depth {d:>3}  {c:>10,}  {bar}")

    print()
    print("=" * 78)
    print("BRANCH FACTOR DISTRIBUTION (children per non-leaf prim)")
    print("=" * 78)
    if not branch_counter:
        print("  (no non-leaf prims)")
    else:
        # bucket: 1, 2, 3-5, 6-10, 11-50, 51-200, 201-1k, >1k
        buckets = [(1, 1), (2, 2), (3, 5), (6, 10), (11, 50), (51, 200),
                   (201, 1000), (1001, float("inf"))]
        bucket_counts = [0] * len(buckets)
        for nkids, count in branch_counter.items():
            for i, (lo, hi) in enumerate(buckets):
                if lo <= nkids <= hi:
                    bucket_counts[i] += count
                    break
        for (lo, hi), c in zip(buckets, bucket_counts):
            label = f"{lo}" if lo == hi else (f"{lo}-{hi}" if hi != float("inf") else f">{lo - 1}")
            print(f"  children={label:<12}  prims={c:>10,}")

    # ---- Top deepest ----
    deepest.sort(key=lambda x: x[0], reverse=True)
    print()
    print("=" * 78)
    print(f"TOP {TOP_N} DEEPEST PRIMS")
    print("=" * 78)
    for i, (d, p) in enumerate(deepest[:TOP_N], 1):
        print(f"  {i:>3}  depth={d:>3}  {p}")

    # ---- Top widest ----
    widest.sort(key=lambda x: x[0], reverse=True)
    print()
    print("=" * 78)
    print(f"TOP {TOP_N} WIDEST PRIMS (most direct children)")
    print("=" * 78)
    for i, (k, p) in enumerate(widest[:TOP_N], 1):
        print(f"  {i:>3}  children={k:>7,}  {p}")

    # ---- CSV ----
    try:
        with open(OUTPUT_CSV, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["section", "key", "value"])
            w.writerow(["summary", "total_prims", n])
            w.writerow(["summary", "max_depth", max_d])
            w.writerow(["summary", "mean_depth", f"{mean_d:.4f}"])
            w.writerow(["summary", "median_depth", med_d])
            w.writerow(["summary", "p95_depth", p95])
            w.writerow(["summary", "p99_depth", p99])
            for d in sorted(depth_counter.keys()):
                w.writerow(["depth_histogram", d, depth_counter[d]])
            for d, p in deepest[:TOP_N]:
                w.writerow(["deepest_top", d, p])
            for k, p in widest[:TOP_N]:
                w.writerow(["widest_top", k, p])
        print(f"\n[csv] wrote {OUTPUT_CSV}")
    except Exception as e:
        print(f"\n[csv] write failed: {e}")

    print("\n[done]")


async def _wrapped():
    try:
        await _hier_main()
    except asyncio.CancelledError:
        print("[cancelled]")
        raise
    except Exception:
        traceback.print_exc()


def _on_done(task):
    if task.cancelled():
        return
    exc = task.exception()
    if exc is not None:
        print(f"[task error] {exc!r}")


_HIERARCHY_DEPTH_TASK = asyncio.ensure_future(_wrapped())
_HIERARCHY_DEPTH_TASK.add_done_callback(_on_done)
print("[started] async hierarchy-depth — cell returns now, work runs in background.")
print("          re-run this cell to cancel and restart.")
