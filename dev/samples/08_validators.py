# =============================================================================
# SO Validators Analyzer — ASYNC, runs Find* ops in analysis mode
# -----------------------------------------------------------------------------
# Verified facts (read directly from omniverse-scene-optimizer C++ source):
#
#   findCoincidingGeometry (FindCoincidingGeometry.cpp):
#     - Operation ctor:    "findCoincidingGeometry"
#     - Args:              primPaths, tolerance, offset, fuzzy
#     - Analysis output:   {"coincidingGeometry": [<prim_paths>]}
#
#   findOccludedMeshes (FindOccludedMeshes.cpp):
#     - Operation ctor:    "findOccludedMeshes"
#     - Args:              paths, checkTransparency, action, useGpu
#     - Analysis output:   {"occludedMeshes": [<prim_paths>]}
#     - WARNING: slow op. Large stages may take minutes.
#
#   findOverlappingMeshes (FindOverlappingMeshes / FindOverlappingMeshesOperation.cpp):
#     - Operation ctor:    "findOverlappingMeshes"  (directory: findMeshOverlaps)
#     - Args:              paths, useGpu (most other args commented out in src)
#     - Analysis output:   {"suppressedOverlaps": uint, "overlappingMeshes": [<paths>]}
#
# All called with ctx.analysisMode = 1 (read-only).
# Re-running cancels previous run.
# =============================================================================

# ---- Tuning ----------------------------------------------------------------
RUN_COINCIDING           = True
RUN_OCCLUDED             = False   # set True if you have time — this op is SLOW
RUN_OVERLAPPING          = True

COINCIDING_TOLERANCE     = 0.001
COINCIDING_OFFSET        = 0.0
COINCIDING_FUZZY         = False

OCCLUDED_CHECK_TRANSPARENCY = False
OCCLUDED_USE_GPU            = True

OVERLAPPING_USE_GPU      = True

TOP_N                    = 20
OUTPUT_CSV               = "./validators.csv"

# ---------------------------------------------------------------------------
import asyncio
import csv
import traceback
import omni.kit.app
import omni.usd

# ---- Cancel any previous run -----------------------------------------------
_prev = globals().get("_VALIDATORS_TASK")
if _prev is not None and not _prev.done():
    _prev.cancel()


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
                if isinstance(name, str):
                    ops.add(name)
                elif isinstance(o, str):
                    ops.add(o)
                else:
                    ops.add(str(o))
        except Exception as e:
            print(f"[so] getOperations() failed: {e}")
        return core, ops
    except Exception as e:
        print(f"[so] failed to acquire SceneOptimizerCore: {e}")
        return None, None


def _call_so(core, op_name, args, stage, available_ops):
    if available_ops and op_name not in available_ops:
        print(f"[so] '{op_name}' NOT registered in this Kit — skipping.")
        return None
    try:
        from omni.scene.optimizer.core import ExecutionContext
        ctx = ExecutionContext()
        ctx.set_stage(stage)
        ctx.analysisMode = 1
        success, error, output = core.executeOperation(op_name, ctx, args)
        try:
            ctx.remove_stage()
        except Exception:
            pass
        if not success:
            print(f"[so] {op_name} returned failure: {error!r}")
            return None
        if isinstance(output, dict):
            return output.get("analysis", output)
        return output
    except Exception as e:
        print(f"[so] direct call failed for {op_name}: {e}")
        return None


def _print_paths(label, paths, limit=TOP_N):
    if not paths:
        print(f"  {label}: 0 entries")
        return
    print(f"  {label}: {len(paths):,} entries")
    for i, p in enumerate(paths[:limit], 1):
        print(f"    {i:>3}  {p}")
    if len(paths) > limit:
        print(f"    ... and {len(paths) - limit:,} more")


async def _validators_main():
    stage = omni.usd.get_context().get_stage()
    if not stage:
        print("[error] no stage open")
        return
    root = stage.GetRootLayer().identifier if stage.GetRootLayer() else "?"
    print(f"[stage] {root}")

    core, available_ops = _get_so_core()
    if core is None:
        print("[error] SO core not available")
        return

    print(f"[so] {len(available_ops)} ops registered")

    csv_rows = []

    # -------- findCoincidingGeometry --------
    if RUN_COINCIDING:
        print()
        print("=" * 78)
        print("SO findCoincidingGeometry — analysis mode")
        print("=" * 78)
        args = {
            "primPaths": [],
            "tolerance": float(COINCIDING_TOLERANCE),
            "offset":    float(COINCIDING_OFFSET),
            "fuzzy":     bool(COINCIDING_FUZZY),
        }
        print(f"  args: {args}")
        await omni.kit.app.get_app().next_update_async()
        analysis = _call_so(core, "findCoincidingGeometry", args, stage, available_ops)
        if isinstance(analysis, dict):
            coinc = analysis.get("coincidingGeometry", [])
            _print_paths("coincidingGeometry", list(coinc))
            for p in coinc:
                csv_rows.append({"validator": "coinciding", "path": str(p)})

    # -------- findOccludedMeshes --------
    if RUN_OCCLUDED:
        print()
        print("=" * 78)
        print("SO findOccludedMeshes — analysis mode  (WARNING: slow)")
        print("=" * 78)
        args = {
            "paths":             [],
            "checkTransparency": bool(OCCLUDED_CHECK_TRANSPARENCY),
            "action":            0,  # default action; analysis mode ignores anyway
            "useGpu":            bool(OCCLUDED_USE_GPU),
        }
        print(f"  args: {args}")
        await omni.kit.app.get_app().next_update_async()
        analysis = _call_so(core, "findOccludedMeshes", args, stage, available_ops)
        if isinstance(analysis, dict):
            occl = analysis.get("occludedMeshes", [])
            _print_paths("occludedMeshes", list(occl))
            for p in occl:
                csv_rows.append({"validator": "occluded", "path": str(p)})

    # -------- findOverlappingMeshes --------
    if RUN_OVERLAPPING:
        print()
        print("=" * 78)
        print("SO findOverlappingMeshes — analysis mode")
        print("=" * 78)
        args = {
            "paths":  [],
            "useGpu": bool(OVERLAPPING_USE_GPU),
        }
        print(f"  args: {args}")
        await omni.kit.app.get_app().next_update_async()
        analysis = _call_so(core, "findOverlappingMeshes", args, stage, available_ops)
        if isinstance(analysis, dict):
            ovr = analysis.get("overlappingMeshes", [])
            suppressed = analysis.get("suppressedOverlaps", 0)
            print(f"  suppressedOverlaps: {suppressed}")
            _print_paths("overlappingMeshes", list(ovr))
            for p in ovr:
                csv_rows.append({"validator": "overlapping", "path": str(p)})

    # -------- CSV --------
    if csv_rows:
        try:
            with open(OUTPUT_CSV, "w", newline="") as f:
                w = csv.DictWriter(f, fieldnames=["validator", "path"])
                w.writeheader()
                w.writerows(csv_rows)
            print(f"\n[csv] wrote {OUTPUT_CSV} ({len(csv_rows):,} rows)")
        except Exception as e:
            print(f"\n[csv] write failed: {e}")

    print("\n[done]")


async def _wrapped():
    try:
        await _validators_main()
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


_VALIDATORS_TASK = asyncio.ensure_future(_wrapped())
_VALIDATORS_TASK.add_done_callback(_on_done)
print("[started] async validators — cell returns now, work runs in background.")
print("          re-run this cell to cancel and restart.")
