# =============================================================================
# Instancing Opportunities Analyzer — ASYNC
# -----------------------------------------------------------------------------
# Detects meshes that COULD be instanced but currently are NOT.
# (Inverse of 02_instancing.py which measures CURRENT instancing.)
#
# Verified facts (read directly from C++ source):
#   - Op name (Operation ctor):    "deduplicateGeometry"
#     scene-optimizer-core/source/operations/deduplicateGeometry/DeduplicateGeometry.cpp
#     omniverse-scene-optimizer Kit ext BUNDLES this op (works at runtime).
#   - Analysis shape:              [ [path, path, ...], [path, path, ...], ... ]
#                                  (list of sets; each set is one duplicate group)
#   - "deduplicateHierarchies" is in scene-optimizer-core but is NOT YET BUNDLED
#     in the omniverse-scene-optimizer Kit extension (changelog confirms — no
#     mentions of "Deduplicate Hierarchies", grep of omniverse repo returns 0).
#     Runtime registry will reject it. We DO NOT call it.
#
# Strategy:
#   1) Call SO deduplicateGeometry (analysis mode) for mesh-level dups
#   2) USD pass: signature-hash grouping by (verts, faces, quantized bbox)
#      Catches dups that SO might miss (different vertex order etc.)
#   3) Path-pattern detection for repeated reference paths
#
# Read-only. Re-running cancels previous.
# =============================================================================

# ---- Tuning ----------------------------------------------------------------
TOP_N                    = 20
YIELD_EVERY              = 200
MIN_DUP_GROUP_SIZE       = 2
MIN_VERTS_FOR_REPORT     = 10
BBOX_QUANTIZE            = 0.001
INCLUDE_INSIDE_INSTANCES = False
OUTPUT_CSV               = "/tmp/instancing_opportunities.csv"
STAGE_PATH               = None
ENABLE_USD_FALLBACK      = True
# ---------------------------------------------------------------------------

import asyncio
import csv
import re
import traceback
from collections import defaultdict
from pxr import Usd, UsdGeom

import omni.usd
import omni.kit.app

_GLOBAL = globals()
_prev = _GLOBAL.get("_OPPORTUNITIES_TASK")
if _prev is not None and not _prev.done():
    print("[cancel] previous run is still active — cancelling it")
    _prev.cancel()


async def _yield():
    await omni.kit.app.get_app().next_update_async()


def _get_so_core():
    try:
        from omni.scene.optimizer.core import SceneOptimizerCore
    except ImportError as e:
        print(f"[so] omni.scene.optimizer.core not loadable: {e}")
        return None, None
    try:
        core = SceneOptimizerCore.getInstance()
        ops = set()
        try:
            for o in core.getOperations():
                name = getattr(o, "name", None) or getattr(o, "getName", lambda: None)()
                if isinstance(name, str): ops.add(name)
                elif isinstance(o, str): ops.add(o)
                else: ops.add(str(o))
        except Exception as e:
            print(f"[so] getOperations() failed: {e}")
        return core, ops
    except Exception as e:
        print(f"[so] failed to acquire SceneOptimizerCore: {e}")
        return None, None


def _call_so(core, op_name, args, stage, available_ops):
    if available_ops and op_name not in available_ops:
        print(f"[so] '{op_name}' NOT registered in this Kit — using USD fallback.")
        return None
    try:
        from omni.scene.optimizer.core import ExecutionContext
        ctx = ExecutionContext()
        ctx.set_stage(stage)
        ctx.analysisMode = 1
        success, error, output = core.executeOperation(op_name, ctx, args)
        try: ctx.remove_stage()
        except Exception: pass
        if not success:
            print(f"[so] {op_name} returned failure: {error!r}")
            return None
        if output is None:
            print(f"[so] {op_name} returned no output.")
            return None
        if isinstance(output, dict):
            return output.get("analysis", output)
        return output
    except Exception as e:
        print(f"[so] direct call failed for {op_name}: {e}")
        return None


_INDEX_RE = re.compile(r"(_\d+|\.\d+|\[\d+\])$")


def _normalize_path(path_str):
    parts = path_str.split("/")
    return "/".join(_INDEX_RE.sub("", p) for p in parts)


def _summarize_dedup_geometry(analysis):
    print("=" * 78)
    print("SO deduplicateGeometry — analysis mode (mesh-level)")
    print("=" * 78)
    if analysis is None:
        print("  (analysis not available — see above for reason)")
        return
    if not isinstance(analysis, (list, tuple)):
        print(f"  (non-list result: {type(analysis).__name__})")
        return
    groups = [list(g) for g in analysis if isinstance(g, (list, tuple))]
    groups.sort(key=len, reverse=True)
    total_meshes = sum(len(g) for g in groups)
    potential_saving = sum(len(g) - 1 for g in groups)
    print(f"  Duplicate groups             : {len(groups):,}")
    print(f"  Total meshes inside groups   : {total_meshes:,}")
    print(f"  Potential mesh reductions    : {potential_saving:,}")
    print(f"  (if every group → 1 prototype + N instances)\n")
    if groups:
        print(f"  TOP {TOP_N} groups by copy count:")
        print(f"  {'#':>3}  {'copies':>7}  sample-path")
        for i, g in enumerate(groups[:TOP_N], 1):
            print(f"  {i:>3}  {len(g):>7}  {g[0]}")
            for p in g[1:4]:
                print(f"           └─ {p}")
            if len(g) > 4:
                print(f"           └─ ... and {len(g) - 4} more")
    print()


async def _main():
    if STAGE_PATH:
        stage = Usd.Stage.Open(STAGE_PATH)
        print(f"[opened] {STAGE_PATH}")
    else:
        stage = omni.usd.get_context().get_stage()
        if stage is None:
            print("[error] No stage open.")
            return
        print(f"[using current stage] {stage.GetRootLayer().identifier}\n")

    core, available_ops = _get_so_core()
    if core is not None and available_ops is not None:
        print(f"[so] SO available — {len(available_ops)} registered operations.")
        # If user wants to know what's available, set ENV var or look at this print.

    # ---- 1) SO: deduplicateGeometry only (Hierarchies not bundled) --------
    # Default args from test_operation_deduplicate_geometry.py:
    #   {"meshPrimPaths":[], "considerDeepTransforms":True, "tolerance":0.05,
    #    "duplicateMethod":0 (instanceableReference), "fuzzy":False,
    #    "useGpu":False, "allowScaling":False}
    geom_analysis = None
    if core is not None:
        geom_args = {"meshPrimPaths": [], "considerDeepTransforms": True,
                     "tolerance": 0.05, "duplicateMethod": 0,
                     "fuzzy": False, "useGpu": False, "allowScaling": False}
        geom_analysis = _call_so(core, "deduplicateGeometry", geom_args, stage, available_ops)
    await _yield()
    _summarize_dedup_geometry(geom_analysis)
    await _yield()

    if core is None and not ENABLE_USD_FALLBACK:
        print("[exit] SO unavailable and ENABLE_USD_FALLBACK=False, stopping.")
        return

    # ---- 2) USD supplement: mesh signature grouping -----------------------
    print("=" * 78)
    print("USD supplement — mesh signature grouping")
    print("(group meshes by (verts, faces, bbox dx/dy/dz) → if multiple have")
    print(" the same signature, they are CANDIDATES for instancing)")
    print("=" * 78)

    bbox_cache = UsdGeom.BBoxCache(Usd.TimeCode.Default(),
                                   includedPurposes=[UsdGeom.Tokens.default_,
                                                     UsdGeom.Tokens.render],
                                   useExtentsHint=True)

    prim_iter = (Usd.PrimRange.Stage(stage, Usd.TraverseInstanceProxies())
                 if INCLUDE_INSIDE_INSTANCES else stage.Traverse())

    sig_groups = defaultdict(list)
    n_meshes = 0
    n_skipped_instanced = 0
    n_skipped_small = 0

    for prim in prim_iter:
        if not prim.IsA(UsdGeom.Mesh): continue
        n_meshes += 1
        if n_meshes % YIELD_EVERY == 0: await _yield()
        if n_meshes % 5000 == 0:
            print(f"  ... {n_meshes} meshes scanned "
                  f"(unique signatures so far={len(sig_groups):,})")

        if prim.IsInstanceProxy() or prim.IsInstance():
            n_skipped_instanced += 1
            continue
        if UsdGeom.Imageable(prim).ComputeVisibility() == UsdGeom.Tokens.invisible:
            continue

        mesh = UsdGeom.Mesh(prim)
        pts = mesh.GetPointsAttr().Get()
        if not pts: continue
        verts = len(pts)
        if verts < MIN_VERTS_FOR_REPORT:
            n_skipped_small += 1
            continue

        fvc = mesh.GetFaceVertexCountsAttr().Get()
        faces = len(fvc) if fvc else 0

        rng = bbox_cache.ComputeWorldBound(prim).ComputeAlignedRange()
        if rng.IsEmpty(): continue
        s = rng.GetSize()
        dx, dy, dz = float(s[0]), float(s[1]), float(s[2])

        q = BBOX_QUANTIZE
        sig = (verts, faces,
               round(dx / q) * q, round(dy / q) * q, round(dz / q) * q)
        sig_groups[sig].append({
            "path": str(prim.GetPath()), "verts": verts, "faces": faces,
            "dx": dx, "dy": dy, "dz": dz,
        })

    await _yield()
    print(f"\n  Total meshes scanned         : {n_meshes:,}")
    print(f"  Skipped (already instanced)  : {n_skipped_instanced:,}")
    print(f"  Skipped (verts < {MIN_VERTS_FOR_REPORT})        : {n_skipped_small:,}")
    print(f"  Unique mesh signatures       : {len(sig_groups):,}\n")

    dup_groups = [(sig, members) for sig, members in sig_groups.items()
                  if len(members) >= MIN_DUP_GROUP_SIZE]
    dup_groups.sort(key=lambda x: (len(x[1]), x[0][0]), reverse=True)

    total_dup_meshes = sum(len(m) for _, m in dup_groups)
    total_savings = sum(len(m) - 1 for _, m in dup_groups)
    print(f"  Duplicate groups (>= {MIN_DUP_GROUP_SIZE} copies): {len(dup_groups):,}")
    print(f"  Total meshes inside groups       : {total_dup_meshes:,}")
    print(f"  Potential mesh reductions        : {total_savings:,}")
    print(f"  (if every group → 1 prototype + N instances)\n")
    await _yield()

    if dup_groups:
        print("=" * 78)
        print(f"TOP {TOP_N} DUPLICATE GROUPS (by copy count)")
        print("=" * 78)
        print(f"  {'#':>3}  {'copies':>7}  {'verts':>10}  {'faces':>10}  "
              f"{'dx':>8}  {'dy':>8}  {'dz':>8}  sample-path")
        for i, (sig, members) in enumerate(dup_groups[:TOP_N], 1):
            verts, faces, dx, dy, dz = sig
            sample = members[0]["path"]
            print(f"  {i:>3}  {len(members):>7}  {verts:>10,}  {faces:>10,}  "
                  f"{dx:>8.3f}  {dy:>8.3f}  {dz:>8.3f}  {sample}")
            for m in members[1:4]:
                print(f"       └─ {m['path']}")
            if len(members) > 4:
                print(f"       └─ ... and {len(members) - 4} more")
        print()
    await _yield()

    # ---- 3) Path-pattern detection ----------------------------------------
    print("=" * 78)
    print("PATH-PATTERN DETECTION (paths differing only by trailing _N / .N)")
    print("=" * 78)
    path_groups = defaultdict(list)
    for sig, members in sig_groups.items():
        for m in members:
            norm = _normalize_path(m["path"])
            path_groups[norm].append(m["path"])

    path_dup = [(norm, paths) for norm, paths in path_groups.items()
                if len(paths) >= MIN_DUP_GROUP_SIZE]
    path_dup.sort(key=lambda x: len(x[1]), reverse=True)

    if not path_dup:
        print("  (none — no path-pattern duplicates detected)\n")
    else:
        print(f"  Path-pattern groups: {len(path_dup):,}")
        print(f"  {'#':>3}  {'copies':>7}  normalized-path")
        for i, (norm, paths) in enumerate(path_dup[:TOP_N], 1):
            print(f"  {i:>3}  {len(paths):>7}  {norm}")
            for p in paths[:3]:
                print(f"       └─ {p}")
            if len(paths) > 3:
                print(f"       └─ ... and {len(paths) - 3} more")
        print()
    await _yield()

    if OUTPUT_CSV:
        try:
            with open(OUTPUT_CSV, "w", newline="") as f:
                w = csv.writer(f)
                w.writerow(["group_id", "copies", "verts", "faces",
                            "dx", "dy", "dz", "path"])
                for gid, (sig, members) in enumerate(dup_groups, 1):
                    verts, faces, dx, dy, dz = sig
                    for m in members:
                        w.writerow([gid, len(members), verts, faces,
                                    f"{dx:.4f}", f"{dy:.4f}", f"{dz:.4f}",
                                    m["path"]])
            print(f"[csv] wrote {OUTPUT_CSV}")
        except Exception as e:
            print(f"[csv] FAILED: {e}")

    print("\n[done]")


async def _wrapped():
    try:
        await _main()
    except asyncio.CancelledError:
        print("[cancelled]")
        raise
    except Exception:
        print("[error] exception in async task:")
        traceback.print_exc()


def _on_done(t):
    try: t.result()
    except Exception: pass


_OPPORTUNITIES_TASK = asyncio.ensure_future(_wrapped())
_OPPORTUNITIES_TASK.add_done_callback(_on_done)
print("[started] async instancing-opportunities scan — cell returns now.")
print("           re-run this cell to cancel and restart.")
