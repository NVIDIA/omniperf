# =============================================================================
# HOOPS Category "Pipe" / "Pipes" Counter — ASYNC version for Kit Script Editor
# -----------------------------------------------------------------------------
# Answers: how many prims in the stage are tagged with HOOPS metadata category
# "Pipe" or "Pipes"?
#
# Background:
#   When CAD data is imported via HOOPS Exchange (Revit / NX / Creo / etc.),
#   the converter often attaches an attribute named
#     omni:hoops:metadata:Other:Category
#   to each prim, carrying the original CAD category string (e.g. "Pipe",
#   "Wall", "Duct", "Door"). This script walks the stage and counts those
#   tags so we can quickly answer "how much of this scene is pipes?".
#
# What is reported:
#   - Exact-case counts for "Pipe" and "Pipes"
#   - Case-insensitive count for any value matching pipe/pipes
#   - Top-N most common Category values across the whole stage
#   - Mesh vs non-mesh split for Pipe/Pipes prims
#   - Total triangle count for matching mesh prims (fan triangulation)
#
# IP-safe: aggregate counts + prim paths only. No vertex positions exfiltrated.
# Read-only. Re-running cancels previous run.
# =============================================================================

# ---- Tuning ----------------------------------------------------------------
ATTR_NAME            = "omni:hoops:metadata:Other:Category"
EXACT_TARGETS        = ("Pipe", "Pipes")          # case-sensitive matches
CASE_INSENSITIVE     = True                        # also count case-insensitive
TOP_N_CATEGORIES     = 30                          # top categories to print
TOP_N_PIPE_PATHS     = 30                          # top pipe-prim paths to print
YIELD_EVERY          = 500                         # prims between UI yields
OUTPUT_CSV           = "./hoops_category_pipes.csv"
OUTPUT_DISTRIBUTION_CSV = "./hoops_category_distribution.csv"
# ---------------------------------------------------------------------------

import asyncio
import csv
import traceback
from collections import Counter

import omni.kit.app
import omni.usd
from pxr import Usd, UsdGeom

_GLOBAL = globals()
_prev = _GLOBAL.get("_HOOPS_CAT_TASK")
if _prev is not None and not _prev.done():
    print("[cancel] previous run is still active — cancelling it")
    _prev.cancel()


async def _yield():
    await omni.kit.app.get_app().next_update_async()


def _count_triangles(mesh):
    """Fan-triangulation triangle count for a UsdGeomMesh (approximate)."""
    try:
        fvc = mesh.GetFaceVertexCountsAttr().Get()
    except Exception:
        return 0
    if not fvc:
        return 0
    total = 0
    for n in fvc:
        if n >= 3:
            total += (n - 2)
    return total


async def _hoops_main():
    stage = omni.usd.get_context().get_stage()
    if stage is None:
        print("[error] no stage open")
        return
    print(f"[stage] {stage.GetRootLayer().identifier}")
    print(f"[attr]  {ATTR_NAME}")

    # Counters
    exact_counts = {t: 0 for t in EXACT_TARGETS}
    ci_pipe_count = 0
    category_counter = Counter()
    n_prims = 0
    n_with_attr = 0

    # Per-prim records for matching Pipe/Pipes
    pipe_records = []   # list of (path, category_value, is_mesh, tri_count)
    pipe_tri_total = 0
    pipe_mesh_count = 0
    pipe_nonmesh_count = 0

    for prim in Usd.PrimRange.Stage(stage, Usd.TraverseInstanceProxies()):
        n_prims += 1
        if n_prims % YIELD_EVERY == 0:
            await _yield()
        if n_prims % (YIELD_EVERY * 50) == 0:
            print(f"  ... {n_prims:,} prims scanned "
                  f"(with Category attr so far={n_with_attr:,})")

        attr = prim.GetAttribute(ATTR_NAME)
        if not attr or not attr.IsValid() or not attr.HasAuthoredValue():
            continue
        try:
            value = attr.Get()
        except Exception:
            continue
        if value is None:
            continue
        # Normalize to string
        sval = str(value)
        n_with_attr += 1
        category_counter[sval] += 1

        # Exact-case match
        exact_hit = sval in exact_counts
        if exact_hit:
            exact_counts[sval] += 1

        # Case-insensitive match for pipe/pipes
        ci_hit = CASE_INSENSITIVE and (sval.lower() in ("pipe", "pipes"))
        if ci_hit:
            ci_pipe_count += 1

        if exact_hit or ci_hit:
            is_mesh = prim.IsA(UsdGeom.Mesh)
            tris = 0
            if is_mesh:
                try:
                    tris = _count_triangles(UsdGeom.Mesh(prim))
                except Exception:
                    tris = 0
                pipe_mesh_count += 1
                pipe_tri_total += tris
            else:
                pipe_nonmesh_count += 1
            pipe_records.append((str(prim.GetPath()), sval, is_mesh, tris))

    # ---------------- Report ----------------
    print()
    print("=" * 78)
    print(f"HOOPS CATEGORY SUMMARY — attr: {ATTR_NAME}")
    print("=" * 78)
    print(f"  Total prims scanned                 : {n_prims:,}")
    print(f"  Prims with authored Category        : {n_with_attr:,}")
    print(f"  Distinct Category values            : {len(category_counter):,}")

    print()
    print("EXACT MATCHES (case-sensitive)")
    for t in EXACT_TARGETS:
        print(f"  Category == \"{t}\"  : {exact_counts[t]:,}")
    print(f"  Sum of exact Pipe/Pipes              : {sum(exact_counts.values()):,}")
    if CASE_INSENSITIVE:
        print(f"  Case-insensitive 'pipe'/'pipes'      : {ci_pipe_count:,}")

    print()
    print(f"PIPE/PIPES PRIM TYPE BREAKDOWN ({len(pipe_records):,} prims)")
    print(f"  Mesh prims        : {pipe_mesh_count:,}")
    print(f"  Non-mesh prims    : {pipe_nonmesh_count:,}")
    print(f"  Triangle total    : {pipe_tri_total:,}  (fan-triangulation, "
          f"approx)")
    if pipe_mesh_count > 0:
        avg = pipe_tri_total / pipe_mesh_count
        print(f"  Avg tris / mesh   : {avg:,.1f}")

    # Top categories overall
    if category_counter:
        print()
        print("=" * 78)
        print(f"TOP {TOP_N_CATEGORIES} CATEGORY VALUES (entire stage)")
        print("=" * 78)
        print(f"  {'#':>3}  {'count':>10}  category")
        for i, (cat, c) in enumerate(category_counter.most_common(TOP_N_CATEGORIES),
                                     1):
            print(f"  {i:>3}  {c:>10,}  {cat!r}")

    # Top pipe prim paths (largest triangle count first)
    if pipe_records:
        worst = sorted(pipe_records, key=lambda r: r[3], reverse=True)
        print()
        print("=" * 78)
        print(f"TOP {TOP_N_PIPE_PATHS} PIPE/PIPES PRIMS BY TRIANGLE COUNT")
        print("=" * 78)
        for i, (path, cat, is_mesh, tris) in enumerate(worst[:TOP_N_PIPE_PATHS], 1):
            tag = "MESH" if is_mesh else "----"
            print(f"  {i:>3}  tris={tris:>10,}  {tag}  cat={cat!r}  {path}")

    # CSV: per-prim Pipe/Pipes
    if OUTPUT_CSV:
        try:
            with open(OUTPUT_CSV, "w", newline="") as f:
                w = csv.writer(f)
                w.writerow(["path", "category", "is_mesh", "tri_count"])
                for path, cat, is_mesh, tris in pipe_records:
                    w.writerow([path, cat, is_mesh, tris])
            print(f"\n[csv] wrote {OUTPUT_CSV} ({len(pipe_records)} rows)")
        except Exception as e:
            print(f"\n[csv] write failed: {e}")

    # CSV: full category distribution
    if OUTPUT_DISTRIBUTION_CSV:
        try:
            with open(OUTPUT_DISTRIBUTION_CSV, "w", newline="") as f:
                w = csv.writer(f)
                w.writerow(["category", "count"])
                for cat, c in category_counter.most_common():
                    w.writerow([cat, c])
            print(f"[csv] wrote {OUTPUT_DISTRIBUTION_CSV} "
                  f"({len(category_counter)} rows)")
        except Exception as e:
            print(f"[csv] distribution write failed: {e}")

    print("\n[done]")


async def _wrapped():
    try:
        await _hoops_main()
    except asyncio.CancelledError:
        print("[cancelled]")
        raise
    except Exception:
        traceback.print_exc()


def _on_done(t):
    try: t.result()
    except Exception: pass


_HOOPS_CAT_TASK = asyncio.ensure_future(_wrapped())
_HOOPS_CAT_TASK.add_done_callback(_on_done)
print("[started] async HOOPS Category Pipe/Pipes scan — cell returns now, "
      "work runs in background.")
print("           re-run this cell to cancel and restart.")
