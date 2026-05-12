# =============================================================================
# Pipe/Cylinder Density Analyzer — ASYNC, USD-only, HEURISTIC
# -----------------------------------------------------------------------------
# WARNING — this is a HEURISTIC, not a semantic "pipe" detector.
# USD has no concept of "pipe". We detect cylinder-like geometry by bbox shape:
#
#   1) "Elongated"     : longest-axis / second-longest-axis > ELONGATION_RATIO
#   2) "Thin-section"  : ratio of two short axes >= 0.5 (roughly circular cross-section)
#   3) "Reasonable verts": vertex count between MIN_VERTS and MAX_VERTS
#                          (cylinders/tubes typically have a moderate vert count)
#
# Outputs:
#   - Cylinder-like mesh count
#   - Density per stage volume (count / stage_bbox_volume), normalized
#   - Length distribution (histogram of long-axis lengths)
#   - Axis-alignment ratio: how many are aligned to world X/Y/Z axes
#     (rough proxy for "straight run" vs "diagonal/bent")
#   - Top-N longest cylinder-like meshes
#
# Limits / caveats (read carefully before quoting numbers):
#   - Cannot detect bent pipes — they would be classified as bent only if their
#     bbox is no longer elongated. A long bent pipe with large bbox dx ≈ dy will
#     NOT be elongated and will be MISSED.
#   - Cannot tell pipes from beams, columns, cables, tubes, rails. All look
#     "cylinder-like" by bbox.
#   - "Straight vs curved" full split would need polyline/centerline analysis,
#     out of scope for a Script-Editor one-shot.
#
# IP-safe: COUNT/DIMENSION only.
# Read-only. Re-running cancels previous run.
# =============================================================================

# ---- Tuning ----------------------------------------------------------------
ELONGATION_RATIO         = 5.0      # long_axis / second_longest > this => elongated
MIN_VERTS                = 6        # below this, too trivial
MAX_VERTS                = 5000     # above this, probably not a simple cylinder
AXIS_ALIGN_TOLERANCE     = 0.10     # short-axis / long-axis below this => "axis-aligned"
TOP_N                    = 20
YIELD_EVERY              = 200      # yield to Kit UI every N meshes
OUTPUT_CSV               = "./pipe_density.csv"

# ---------------------------------------------------------------------------
import asyncio
import csv
import traceback
import omni.kit.app
import omni.usd
from pxr import Usd, UsdGeom

# ---- Cancel any previous run -----------------------------------------------
_prev = globals().get("_PIPE_DENSITY_TASK")
if _prev is not None and not _prev.done():
    _prev.cancel()


def _bbox_dims(prim, bbox_cache):
    try:
        bbox = bbox_cache.ComputeWorldBound(prim).ComputeAlignedBox()
    except Exception:
        return None
    mn, mx = bbox.GetMin(), bbox.GetMax()
    dx = float(mx[0] - mn[0])
    dy = float(mx[1] - mn[1])
    dz = float(mx[2] - mn[2])
    return dx, dy, dz


def _classify_cylinder(dx, dy, dz):
    """Return (is_cylinder_like, long_axis_index, long_len, second_len, short_len)."""
    dims = [(dx, 0), (dy, 1), (dz, 2)]
    dims.sort(key=lambda x: x[0], reverse=True)
    long_len, long_ax = dims[0]
    second_len, _ = dims[1]
    short_len, _ = dims[2]
    if long_len <= 0 or second_len <= 0:
        return False, long_ax, long_len, second_len, short_len
    elong = long_len / max(second_len, 1e-9)
    if elong < ELONGATION_RATIO:
        return False, long_ax, long_len, second_len, short_len
    # Cross-section roughly circular: shortest and second-shortest similar
    if second_len > 0 and short_len / second_len < 0.5:
        return False, long_ax, long_len, second_len, short_len
    return True, long_ax, long_len, second_len, short_len


async def _pipe_main():
    stage = omni.usd.get_context().get_stage()
    if not stage:
        print("[error] no stage open")
        return
    root = stage.GetRootLayer().identifier if stage.GetRootLayer() else "?"
    print(f"[stage] {root}")

    bbox_cache = UsdGeom.BBoxCache(Usd.TimeCode.Default(),
                                   [UsdGeom.Tokens.default_, UsdGeom.Tokens.render])

    # Stage bbox for density normalization
    try:
        stage_bb = bbox_cache.ComputeWorldBound(stage.GetPseudoRoot()).ComputeAlignedBox()
        sdx = float(stage_bb.GetMax()[0] - stage_bb.GetMin()[0])
        sdy = float(stage_bb.GetMax()[1] - stage_bb.GetMin()[1])
        sdz = float(stage_bb.GetMax()[2] - stage_bb.GetMin()[2])
        stage_vol = max(sdx * sdy * sdz, 1.0)
    except Exception:
        stage_vol = 1.0
        sdx = sdy = sdz = 0.0

    print(f"[stage bbox] dx={sdx:.2f} dy={sdy:.2f} dz={sdz:.2f}  vol={stage_vol:.2e}")

    total_meshes = 0
    cyl_meshes = []          # list of (long_len, second_len, short_len, long_ax, path)
    axis_aligned = 0         # cylinders where 2 short axes << long axis (i.e. axis-aligned)
    n_yield_chunk = 0

    for prim in stage.TraverseAll():
        if not prim.IsA(UsdGeom.Mesh):
            continue
        total_meshes += 1

        # Skip extremely complex meshes — not cylinders
        try:
            mesh = UsdGeom.Mesh(prim)
            points_attr = mesh.GetPointsAttr()
            n_verts = len(points_attr.Get()) if points_attr.Get() else 0
        except Exception:
            n_verts = 0
        if n_verts < MIN_VERTS or n_verts > MAX_VERTS:
            n_yield_chunk += 1
            if n_yield_chunk >= YIELD_EVERY:
                n_yield_chunk = 0
                await omni.kit.app.get_app().next_update_async()
            continue

        dims = _bbox_dims(prim, bbox_cache)
        if dims is None:
            continue
        dx, dy, dz = dims
        is_cyl, long_ax, long_len, second_len, short_len = _classify_cylinder(dx, dy, dz)
        if is_cyl:
            cyl_meshes.append((long_len, second_len, short_len, long_ax, str(prim.GetPath())))
            # Axis-alignment: both shorter axes are small relative to long axis
            if (second_len / long_len) < AXIS_ALIGN_TOLERANCE * 5:
                axis_aligned += 1

        n_yield_chunk += 1
        if n_yield_chunk >= YIELD_EVERY:
            n_yield_chunk = 0
            await omni.kit.app.get_app().next_update_async()
            if (total_meshes % (YIELD_EVERY * 25)) == 0:
                print(f"  ... {total_meshes:,} meshes scanned (cyl so far={len(cyl_meshes):,})")

    n_cyl = len(cyl_meshes)
    pct = (100.0 * n_cyl / total_meshes) if total_meshes else 0.0
    density = (n_cyl / stage_vol) if stage_vol > 0 else 0.0

    print()
    print("=" * 78)
    print("CYLINDER-LIKE MESH SUMMARY (heuristic)")
    print("=" * 78)
    print(f"  Total meshes scanned        : {total_meshes:,}")
    print(f"  Cylinder-like meshes        : {n_cyl:,}  ({pct:.1f}%)")
    print(f"  Axis-aligned cylinders      : {axis_aligned:,}")
    print(f"  Density (count / stage vol) : {density:.4e}")
    print(f"  Criteria: elong>{ELONGATION_RATIO}, verts {MIN_VERTS}-{MAX_VERTS}, "
          f"cross-section roughly round (short/second >= 0.5)")

    # Length histogram
    if n_cyl > 0:
        lens = sorted([c[0] for c in cyl_meshes])
        lo, hi = lens[0], lens[-1]
        print()
        print("=" * 78)
        print("LENGTH DISTRIBUTION (long-axis length)")
        print("=" * 78)
        if hi > 0 and lo >= 0:
            # Logarithmic bins
            buckets_def = [(0, 0.01), (0.01, 0.1), (0.1, 1.0), (1.0, 10.0),
                           (10.0, 100.0), (100.0, 1000.0), (1000.0, float("inf"))]
            buckets = [0] * len(buckets_def)
            for L in lens:
                for i, (lo_b, hi_b) in enumerate(buckets_def):
                    if lo_b <= L < hi_b:
                        buckets[i] += 1
                        break
            max_b = max(buckets) if buckets else 1
            bar_max = 40
            for (lo_b, hi_b), c in zip(buckets_def, buckets):
                lab = f"[{lo_b}, {hi_b})" if hi_b != float("inf") else f"[{lo_b}, inf)"
                bar = "#" * int(bar_max * c / max_b) if max_b else ""
                print(f"  {lab:<20}  {c:>8,}  {bar}")
        # Longest
        cyl_meshes.sort(key=lambda x: x[0], reverse=True)
        print()
        print("=" * 78)
        print(f"TOP {TOP_N} LONGEST CYLINDER-LIKE MESHES")
        print("=" * 78)
        axis_lbl = {0: "X", 1: "Y", 2: "Z"}
        for i, (L, S2, S3, ax, p) in enumerate(cyl_meshes[:TOP_N], 1):
            print(f"  {i:>3}  long={L:>10.3f}  cross=({S2:.3f}, {S3:.3f})  axis={axis_lbl.get(ax,'?')}  {p}")

    # ---- CSV ----
    try:
        with open(OUTPUT_CSV, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["section", "key", "value"])
            w.writerow(["summary", "total_meshes", total_meshes])
            w.writerow(["summary", "cylinder_like", n_cyl])
            w.writerow(["summary", "cylinder_pct", f"{pct:.4f}"])
            w.writerow(["summary", "axis_aligned", axis_aligned])
            w.writerow(["summary", "density_per_vol", f"{density:.6e}"])
            w.writerow(["summary", "stage_vol", f"{stage_vol:.6e}"])
            for i, (L, S2, S3, ax, p) in enumerate(cyl_meshes[:TOP_N], 1):
                w.writerow([f"top_{i}", "long_len", L])
                w.writerow([f"top_{i}", "short1", S2])
                w.writerow([f"top_{i}", "short2", S3])
                w.writerow([f"top_{i}", "axis", ax])
                w.writerow([f"top_{i}", "path", p])
        print(f"\n[csv] wrote {OUTPUT_CSV}")
    except Exception as e:
        print(f"\n[csv] write failed: {e}")

    print("\n[done]")


async def _wrapped():
    try:
        await _pipe_main()
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


_PIPE_DENSITY_TASK = asyncio.ensure_future(_wrapped())
_PIPE_DENSITY_TASK.add_done_callback(_on_done)
print("[started] async pipe-density (heuristic) — cell returns now, work runs in background.")
print("          re-run this cell to cancel and restart.")
