# =============================================================================
# Small Objects Analyzer — ASYNC, uses Scene Optimizer's removeSmallGeometry
# -----------------------------------------------------------------------------
# Verified facts (read directly from omniverse-scene-optimizer C++ source):
#   - Op name (Operation ctor):           "removeSmallGeometry"
#   - Module import path:                 omni.scene.optimizer.core
#   - Args (RemoveSmallGeometry.cpp):     paths, removeMethod, detectionMethod, threshold
#   - Analysis output (lines 130-149):    { "smallGeometry": [<prim_path>, ...] }
#                                         optionally also "suggestedOperations"
#   - analysisMode:                       ctx.analysisMode = 1
#
# Read-only. Re-running cancels previous run.
# =============================================================================

# ---- Tuning ----------------------------------------------------------------
THRESHOLDS_WORLD_UNITS   = [0.01, 0.05, 0.1, 0.5, 1.0]
TOP_N                    = 20
YIELD_EVERY              = 200
INCLUDE_INSIDE_INSTANCES = True
OUTPUT_CSV               = "/tmp/small_objects.csv"
STAGE_PATH               = None
ENABLE_USD_FALLBACK      = True
# ---------------------------------------------------------------------------

import asyncio
import csv
import traceback
from pxr import Usd, UsdGeom

import omni.usd
import omni.kit.app

_GLOBAL = globals()
_prev = _GLOBAL.get("_SMALL_TASK")
if _prev is not None and not _prev.done():
    print("[cancel] previous run is still active — cancelling it")
    _prev.cancel()


async def _yield():
    await omni.kit.app.get_app().next_update_async()


def _get_so_core():
    """Return (core, available_op_names_set) or (None, None)."""
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
    """Call SO op in analysisMode=1. Returns analysis payload or None."""
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


async def _small_main():
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

    # ---- 1) Primary: SO removeSmallGeometry, multi-threshold preview ------
    print("=" * 78)
    print("SO removeSmallGeometry — analysis preview at multiple thresholds")
    print("=" * 78)
    so_rows = []
    for t in THRESHOLDS_WORLD_UNITS:
        args = {"paths": [], "removeMethod": 1, "detectionMethod": 1,
                "threshold": float(t)}
        analysis = None
        if core is not None:
            analysis = _call_so(core, "removeSmallGeometry", args, stage, available_ops)
        await _yield()
        if analysis is None:
            print(f"  threshold={t}: analysis not available")
            continue
        if isinstance(analysis, dict):
            small = analysis.get("smallGeometry", [])
            if not isinstance(small, (list, tuple)):
                small = []
            print(f"  threshold={t:<6}  would_remove={len(small):,}")
            so_rows.append({"threshold": t, "would_remove": len(small),
                            "paths": list(small)})
        else:
            print(f"  threshold={t}: non-dict result ({type(analysis).__name__})")
    print()
    await _yield()

    # Show some example paths from the smallest non-empty threshold
    if so_rows:
        for row in so_rows:
            if row["would_remove"] > 0:
                print(f"  Sample paths at threshold={row['threshold']} "
                      f"(first {min(TOP_N, row['would_remove'])} of {row['would_remove']:,}):")
                for p in row["paths"][:TOP_N]:
                    print(f"    {p}")
                if row["would_remove"] > TOP_N:
                    print(f"    ... and {row['would_remove'] - TOP_N} more")
                print()
                break

    if core is None and not ENABLE_USD_FALLBACK:
        print("[exit] SO unavailable and ENABLE_USD_FALLBACK=False, stopping.")
        return

    # ---- 2) USD supplement: per-mesh diag distribution + Top-N smallest ---
    print("=" * 78)
    print("USD supplement — per-mesh bbox-diagonal distribution")
    print("=" * 78)
    bbox_cache = UsdGeom.BBoxCache(Usd.TimeCode.Default(),
                                   includedPurposes=[UsdGeom.Tokens.default_,
                                                     UsdGeom.Tokens.render],
                                   useExtentsHint=True)
    prim_iter = (Usd.PrimRange.Stage(stage, Usd.TraverseInstanceProxies())
                 if INCLUDE_INSIDE_INSTANCES else stage.Traverse())

    results = []
    n = 0
    for prim in prim_iter:
        if not prim.IsA(UsdGeom.Mesh): continue
        n += 1
        if n % YIELD_EVERY == 0: await _yield()
        if n % 5000 == 0:
            print(f"  ... {n} meshes scanned")
        if UsdGeom.Imageable(prim).ComputeVisibility() == UsdGeom.Tokens.invisible:
            continue
        mesh = UsdGeom.Mesh(prim)
        pts = mesh.GetPointsAttr().Get()
        if not pts: continue
        rng = bbox_cache.ComputeWorldBound(prim).ComputeAlignedRange()
        if rng.IsEmpty(): continue
        s = rng.GetSize()
        dx, dy, dz = float(s[0]), float(s[1]), float(s[2])
        diag = (dx*dx + dy*dy + dz*dz) ** 0.5
        results.append({
            "path": str(prim.GetPath()), "verts": len(pts),
            "diag": diag, "dx": dx, "dy": dy, "dz": dz,
        })

    await _yield()
    if not results:
        print("[result] no meshes to analyze.")
        return

    stage_rng = bbox_cache.ComputeWorldBound(stage.GetPseudoRoot()).ComputeAlignedRange()
    if not stage_rng.IsEmpty():
        s = stage_rng.GetSize()
        stage_diag = (float(s[0])**2 + float(s[1])**2 + float(s[2])**2) ** 0.5
    else:
        stage_diag = 0.0

    diags = sorted(r["diag"] for r in results)
    n_total = len(diags)
    print(f"\n  Total meshes (visible)       : {n_total:,}")
    print(f"  Stage bbox diag              : {stage_diag:.3f}")
    print(f"  Min mesh diag                : {diags[0]:.6f}")
    print(f"  Median mesh diag             : {diags[n_total//2]:.6f}")
    print(f"  Max mesh diag                : {diags[-1]:.6f}\n")

    print("=" * 78)
    print("USD threshold preview — how many meshes would be removed at threshold X")
    print("=" * 78)
    print(f"  {'threshold (world units)':<30}  {'remove':>10}  {'remove %':>10}  "
          f"{'remove % stage diag':>22}")
    for t in THRESHOLDS_WORLD_UNITS:
        kill = sum(1 for d in diags if d < t)
        pct = (kill / n_total) * 100.0
        pct_stage = (t / stage_diag * 100.0) if stage_diag > 0 else 0.0
        print(f"  {t:<30}  {kill:>10,}  {pct:>9.2f}%  {pct_stage:>21.4f}%")
    print()
    await _yield()

    smallest = sorted(results, key=lambda r: r["diag"])
    print("=" * 78)
    print(f"TOP {TOP_N} SMALLEST MESHES (by world bbox diagonal)")
    print("=" * 78)
    print(f"  {'#':>3}  {'diag':>12}  {'verts':>10}  "
          f"{'dx':>10}  {'dy':>10}  {'dz':>10}  path")
    for i, r in enumerate(smallest[:TOP_N], 1):
        print(f"  {i:>3}  {r['diag']:>12.6f}  {r['verts']:>10,}  "
              f"{r['dx']:>10.4f}  {r['dy']:>10.4f}  {r['dz']:>10.4f}  {r['path']}")
    print()
    await _yield()

    if OUTPUT_CSV:
        try:
            with open(OUTPUT_CSV, "w", newline="") as f:
                w = csv.writer(f)
                w.writerow(["path", "verts", "diag", "dx", "dy", "dz"])
                for r in smallest:
                    w.writerow([r["path"], r["verts"],
                                f"{r['diag']:.6f}", f"{r['dx']:.6f}",
                                f"{r['dy']:.6f}", f"{r['dz']:.6f}"])
            print(f"[csv] wrote {OUTPUT_CSV}")
        except Exception as e:
            print(f"[csv] FAILED: {e}")

    print("\n[done]")


async def _wrapped():
    try:
        await _small_main()
    except asyncio.CancelledError:
        print("[cancelled]")
        raise
    except Exception:
        print("[error] exception in async task:")
        traceback.print_exc()


def _on_done(t):
    try: t.result()
    except Exception: pass


_SMALL_TASK = asyncio.ensure_future(_wrapped())
_SMALL_TASK.add_done_callback(_on_done)
print("[started] async small-objects scan — cell returns now.")
print("           re-run this cell to cancel and restart.")
