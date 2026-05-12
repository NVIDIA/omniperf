# =============================================================================
# SO printStats Analyzer — ASYNC, uses Scene Optimizer's printStats op
# -----------------------------------------------------------------------------
# Verified facts (read directly from omniverse-scene-optimizer C++ source):
#   - Op name (Operation ctor):  "printStats" (in stats/PrintStats.cpp)
#                                Operation("printStats", "Stats", ...)
#   - Module import path:        omni.scene.optimizer.core
#   - Args (PrintStats.cpp):     countPrimvars, splitCollocatedPoints, time
#   - Analysis output:           dict (nested) with full stats payload
#                                (lines 385-386: analysis["analysis"] = payload)
#   - analysisMode:              ctx.analysisMode = 1 (int, not bool)
#
# Comparison with dev/samples/export_stage_stats.py:
#   - That script reads CACHED stats via omni.stats.get_stats_interface()
#     filtered by scope "Scene Optimizer". Requires the op to have run earlier.
#   - This script INVOKES the printStats op directly (analysis mode) and prints
#     its raw analysis payload. Self-contained, no scope-cache dependency.
#
# Read-only. Re-running cancels previous run.
# =============================================================================

# ---- Tuning ----------------------------------------------------------------
COUNT_PRIMVARS           = True
SPLIT_COLLOCATED_POINTS  = False
TIME                     = 0.0
OUTPUT_JSON              = "./so_printstats.json"

# ---------------------------------------------------------------------------
import asyncio
import json
import traceback
import omni.kit.app
import omni.usd

# ---- Cancel any previous run -----------------------------------------------
_prev = globals().get("_SO_PRINTSTATS_TASK")
if _prev is not None and not _prev.done():
    _prev.cancel()


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


def _walk_print(d, indent=0):
    """Pretty-print nested dict / list result."""
    pad = "  " * indent
    if isinstance(d, dict):
        for k, v in d.items():
            if isinstance(v, (dict, list)) and v:
                print(f"{pad}{k}:")
                _walk_print(v, indent + 1)
            else:
                print(f"{pad}{k}: {v}")
    elif isinstance(d, list):
        if len(d) > 10:
            for x in d[:10]:
                _walk_print(x, indent)
            print(f"{pad}... and {len(d) - 10} more")
        else:
            for x in d:
                _walk_print(x, indent)
    else:
        print(f"{pad}{d}")


async def _printstats_main():
    stage = omni.usd.get_context().get_stage()
    if not stage:
        print("[error] no stage open")
        return
    root = stage.GetRootLayer().identifier if stage.GetRootLayer() else "?"
    print(f"[stage] {root}")

    core, available_ops = _get_so_core()
    if core is None:
        print("[error] SO core not available — cannot run printStats")
        return

    print(f"[so] {len(available_ops)} ops registered in this Kit")
    if "printStats" not in available_ops:
        print("[so] 'printStats' NOT registered — likely missing extension.")
        print("[so] Available ops sample:")
        for op in sorted(list(available_ops))[:30]:
            print(f"      {op}")
        return

    args = {
        "countPrimvars":          bool(COUNT_PRIMVARS),
        "splitCollocatedPoints":  bool(SPLIT_COLLOCATED_POINTS),
        "time":                   float(TIME),
    }

    print("=" * 78)
    print("SO printStats — analysis mode")
    print("=" * 78)
    print(f"  args: {args}")
    print()

    await omni.kit.app.get_app().next_update_async()

    analysis = _call_so(core, "printStats", args, stage, available_ops)
    if analysis is None:
        print("  (no analysis returned — see [so] log above)")
        return

    print("Analysis payload (full):")
    print("-" * 78)
    _walk_print(analysis)
    print("-" * 78)

    # Also dump JSON to file
    try:
        with open(OUTPUT_JSON, "w") as f:
            json.dump(analysis, f, indent=2, default=str)
        print(f"\n[json] wrote {OUTPUT_JSON}")
    except Exception as e:
        print(f"\n[json] write failed: {e}")

    print("\n[done]")


async def _wrapped():
    try:
        await _printstats_main()
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


_SO_PRINTSTATS_TASK = asyncio.ensure_future(_wrapped())
_SO_PRINTSTATS_TASK.add_done_callback(_on_done)
print("[started] async SO printStats — cell returns now, work runs in background.")
print("          re-run this cell to cancel and restart.")
