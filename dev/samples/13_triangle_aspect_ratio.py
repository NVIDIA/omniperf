# =============================================================================
# Triangle Aspect Ratio Analyzer — ASYNC version for Kit Script Editor
# -----------------------------------------------------------------------------
# Answers: are the triangles "long and skinny" or more "equilateral"?
#
# For every UsdGeomMesh, triangulate each face by fanning from vertex 0
# (this is an approximation — fine for stats, NOT for geometry output),
# then compute an aspect ratio per triangle.
#
# Two metrics reported per triangle:
#   ar1 = longest_edge / shortest_edge           (1.0 = equilateral, >> 1.0 = sliver)
#   ar2 = longest_edge / (2 * inradius)          (radius ratio; 2.0 = equilateral,
#                                                 larger = more sliver-like)
# We use ar1 (longest/shortest) as the primary metric — simpler to interpret.
#
# Output:
#   - Total triangles scanned
#   - Mean / median / p95 of ar1 across the whole stage
#   - Histogram of ar1 buckets
#   - Optional pipe-subset stats (re-uses 10_pipe_density.py heuristic)
#
# Tuning: SAMPLE_EVERY_NTH_TRI=1 means analyze every triangle.  For very
# heavy stages, set higher (e.g. 5) to subsample.
#
# IP-safe: aggregate stats only; no vertex positions leave the stage.
# Read-only. Re-running cancels previous run.
# =============================================================================

# ---- Tuning ----------------------------------------------------------------
SAMPLE_EVERY_NTH_TRI = 1     # 1 = every triangle, 5 = 1-in-5, 10 = 1-in-10
MAX_VERTS_PER_MESH   = 200000  # skip extremely dense meshes (perf)
INCLUDE_PIPE_SUBSET  = True
ELONGATION_RATIO     = 5.0   # same as 10_pipe_density.py
MIN_VERTS_PIPE       = 6
MAX_VERTS_PIPE       = 5000
YIELD_EVERY          = 50    # meshes between UI yields (this script is heavier)
OUTPUT_CSV           = "./triangle_aspect_ratio.csv"
TOP_N                = 20
# ---------------------------------------------------------------------------

import asyncio
import csv
import math
import statistics
import traceback

import omni.kit.app
import omni.usd
from pxr import Usd, UsdGeom

_GLOBAL = globals()
_prev = _GLOBAL.get("_TRI_AR_TASK")
if _prev is not None and not _prev.done():
    print("[cancel] previous run is still active — cancelling it")
    _prev.cancel()


async def _yield():
    await omni.kit.app.get_app().next_update_async()


def _is_pipe_like(prim, bbox_cache):
    try:
        mesh = UsdGeom.Mesh(prim)
        pts = mesh.GetPointsAttr().Get()
        n_verts = len(pts) if pts else 0
    except Exception:
        return False
    if n_verts < MIN_VERTS_PIPE or n_verts > MAX_VERTS_PIPE:
        return False
    try:
        bb = bbox_cache.ComputeWorldBound(prim).ComputeAlignedBox()
        mn, mx = bb.GetMin(), bb.GetMax()
        dx = float(mx[0] - mn[0]); dy = float(mx[1] - mn[1]); dz = float(mx[2] - mn[2])
    except Exception:
        return False
    dims = sorted([dx, dy, dz], reverse=True)
    long_, second_, short_ = dims
    if long_ <= 0 or second_ <= 0:
        return False
    if long_ / max(second_, 1e-9) < ELONGATION_RATIO:
        return False
    if second_ > 0 and short_ / second_ < 0.5:
        return False
    return True


def _tri_ar(p0, p1, p2):
    """Aspect ratio = longest_edge / shortest_edge of a triangle."""
    e0 = (p1[0] - p0[0], p1[1] - p0[1], p1[2] - p0[2])
    e1 = (p2[0] - p1[0], p2[1] - p1[1], p2[2] - p1[2])
    e2 = (p0[0] - p2[0], p0[1] - p2[1], p0[2] - p2[2])
    L0 = math.sqrt(e0[0]**2 + e0[1]**2 + e0[2]**2)
    L1 = math.sqrt(e1[0]**2 + e1[1]**2 + e1[2]**2)
    L2 = math.sqrt(e2[0]**2 + e2[1]**2 + e2[2]**2)
    mx = max(L0, L1, L2)
    mn = min(L0, L1, L2)
    if mn <= 0.0:
        return None
    return mx / mn


def _accumulate_mesh(mesh, sampler_state):
    """Return (count, sum_ar, ar_list) for one mesh."""
    pts = mesh.GetPointsAttr().Get()
    fvc = mesh.GetFaceVertexCountsAttr().Get()
    fvi = mesh.GetFaceVertexIndicesAttr().Get()
    if not pts or not fvc or not fvi:
        return 0, 0.0, []

    n_verts = len(pts)
    if n_verts > MAX_VERTS_PER_MESH:
        return 0, 0.0, []

    ar_local = []
    idx = 0
    total = 0
    sum_ar = 0.0
    skip = SAMPLE_EVERY_NTH_TRI
    counter = sampler_state[0]
    for n in fvc:
        if n < 3:
            idx += n
            continue
        # Fan triangulation from vertex 0 of this face
        i0 = fvi[idx]
        for k in range(1, n - 1):
            counter += 1
            if (counter % skip) != 0:
                continue
            i1 = fvi[idx + k]
            i2 = fvi[idx + k + 1]
            if i0 >= n_verts or i1 >= n_verts or i2 >= n_verts:
                continue
            ar = _tri_ar(pts[i0], pts[i1], pts[i2])
            if ar is None:
                continue
            sum_ar += ar
            total += 1
            ar_local.append(ar)
        idx += n
    sampler_state[0] = counter
    return total, sum_ar, ar_local


async def _ar_main():
    stage = omni.usd.get_context().get_stage()
    if stage is None:
        print("[error] no stage open")
        return
    print(f"[stage] {stage.GetRootLayer().identifier}")

    bbox_cache = UsdGeom.BBoxCache(Usd.TimeCode.Default(),
                                   [UsdGeom.Tokens.default_, UsdGeom.Tokens.render])

    sampler_state = [0]  # counter shared across meshes
    all_ar = []
    all_pipe_ar = []
    n_meshes = 0
    n_meshes_processed = 0
    per_mesh_stats = []  # list of (path, mean_ar, count, is_pipe)

    for prim in Usd.PrimRange.Stage(stage, Usd.TraverseInstanceProxies()):
        if not prim.IsA(UsdGeom.Mesh):
            continue
        n_meshes += 1

        if n_meshes % YIELD_EVERY == 0:
            await _yield()
        if n_meshes % (YIELD_EVERY * 20) == 0:
            print(f"  ... {n_meshes:,} meshes scanned "
                  f"(triangles so far={len(all_ar):,})")

        try:
            mesh = UsdGeom.Mesh(prim)
        except Exception:
            continue

        cnt, sum_ar, ar_list = _accumulate_mesh(mesh, sampler_state)
        if cnt == 0:
            continue
        n_meshes_processed += 1

        mean_ar = sum_ar / cnt
        is_pipe = INCLUDE_PIPE_SUBSET and _is_pipe_like(prim, bbox_cache)
        per_mesh_stats.append((str(prim.GetPath()), mean_ar, cnt, is_pipe))
        all_ar.extend(ar_list)
        if is_pipe:
            all_pipe_ar.extend(ar_list)

    print()
    print("=" * 78)
    print("TRIANGLE ASPECT RATIO (longest_edge / shortest_edge)")
    print("=" * 78)
    print(f"  Total meshes seen                : {n_meshes:,}")
    print(f"  Meshes with measurable triangles : {n_meshes_processed:,}")
    print(f"  Triangles analyzed (sampled 1/{SAMPLE_EVERY_NTH_TRI}) : {len(all_ar):,}")

    def _print_dist(label, lst):
        if not lst:
            print(f"  [{label}] (no triangles)")
            return
        m = statistics.mean(lst)
        med = statistics.median(lst)
        sl = sorted(lst)
        p95 = sl[int(0.95 * (len(sl) - 1))]
        mx = sl[-1]
        print(f"  [{label}]")
        print(f"    triangles    : {len(lst):,}")
        print(f"    mean ar      : {m:.3f}    (1.0 = equilateral, > 4 = sliver)")
        print(f"    median ar    : {med:.3f}")
        print(f"    p95 ar       : {p95:.3f}")
        print(f"    max ar       : {mx:.3f}")
        # Buckets
        bins = [(1.0, 1.5), (1.5, 2.0), (2.0, 3.0), (3.0, 5.0),
                (5.0, 10.0), (10.0, 50.0), (50.0, float("inf"))]
        bucket_counts = [0] * len(bins)
        for v in lst:
            for i, (lo, hi) in enumerate(bins):
                if lo <= v < hi:
                    bucket_counts[i] += 1
                    break
        mx_b = max(bucket_counts) or 1
        for (lo, hi), c in zip(bins, bucket_counts):
            lab = f"[{lo}, {hi})" if hi != float("inf") else f"[{lo}, inf)"
            bar = "#" * int(40 * c / mx_b)
            pct = 100.0 * c / len(lst)
            print(f"    {lab:<14}  {c:>10,}  ({pct:>5.1f}%)  {bar}")

    print()
    _print_dist("ALL TRIANGLES", all_ar)

    if INCLUDE_PIPE_SUBSET:
        print()
        _print_dist("PIPE-LIKE MESHES SUBSET", all_pipe_ar)

    # Top mean-AR meshes (worst-quality meshes)
    if per_mesh_stats:
        worst = sorted(per_mesh_stats, key=lambda x: x[1], reverse=True)
        print()
        print("=" * 78)
        print(f"TOP {TOP_N} MESHES BY MEAN ASPECT RATIO (worst sliver-ness)")
        print("=" * 78)
        for i, (p, m, c, is_pipe) in enumerate(worst[:TOP_N], 1):
            tag = "PIPE" if is_pipe else "    "
            print(f"  {i:>3}  mean_ar={m:>8.3f}  tris={c:>8,}  {tag}  {p}")

    # CSV
    if OUTPUT_CSV:
        try:
            with open(OUTPUT_CSV, "w", newline="") as f:
                w = csv.writer(f)
                w.writerow(["path", "mean_ar", "tri_count", "is_pipe_like"])
                for p, m, c, is_pipe in per_mesh_stats:
                    w.writerow([p, f"{m:.4f}", c, is_pipe])
            print(f"\n[csv] wrote {OUTPUT_CSV} ({len(per_mesh_stats)} rows)")
        except Exception as e:
            print(f"\n[csv] write failed: {e}")

    print("\n[done]")


async def _wrapped():
    try:
        await _ar_main()
    except asyncio.CancelledError:
        print("[cancelled]")
        raise
    except Exception:
        traceback.print_exc()


def _on_done(t):
    try: t.result()
    except Exception: pass


_TRI_AR_TASK = asyncio.ensure_future(_wrapped())
_TRI_AR_TASK.add_done_callback(_on_done)
print("[started] async triangle-aspect-ratio scan — cell returns now, work runs in background.")
print("           re-run this cell to cancel and restart.")
