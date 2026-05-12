# =============================================================================
# Animation Trait Analyzer — ASYNC, uses Scene Optimizer's optimizeTimeSamples
# -----------------------------------------------------------------------------
# Verified facts (read directly from omniverse-scene-optimizer C++ source):
#   - Op name (Operation ctor):      "optimizeTimeSamples"
#   - Module import path:            omni.scene.optimizer.core
#   - Available op introspection:    SceneOptimizerCore.getInstance().getOperations()
#   - analysisMode:                  ctx.analysisMode = 1
#   - Analysis output (per source):  { <attribute_path>: [redundant_count, total_count] }
#     (OptimizeTimeSamples.cpp lines 667-683: resultJson["analysis"] = analysisResult)
#
# Read-only. Re-running cancels previous run.
# =============================================================================

# ---- Tuning ----------------------------------------------------------------
TOP_N                    = 20
YIELD_EVERY              = 200
INCLUDE_INSIDE_INSTANCES = True
OUTPUT_CSV               = "/tmp/animation.csv"
STAGE_PATH               = None
ENABLE_USD_FALLBACK      = True
# ---------------------------------------------------------------------------

import asyncio
import csv
import traceback
from collections import Counter
from pxr import Usd, UsdGeom, UsdSkel

import omni.usd
import omni.kit.app

_GLOBAL = globals()
_prev = _GLOBAL.get("_ANIM_TASK")
if _prev is not None and not _prev.done():
    print("[cancel] previous run is still active — cancelling it")
    _prev.cancel()


async def _yield():
    await omni.kit.app.get_app().next_update_async()


def _get_so_core():
    """Return (core, available_op_names_set) or (None, None) if SO unavailable."""
    try:
        from omni.scene.optimizer.core import SceneOptimizerCore
    except ImportError as e:
        print(f"[so] omni.scene.optimizer.core not loadable: {e}")
        return None, None
    try:
        core = SceneOptimizerCore.getInstance()
        ops = set()
        try:
            ops_obj = core.getOperations()
            for o in ops_obj:
                # ops may be op-objects with a name attr, or plain strings
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
    """Call SO op in analysisMode=1. Returns analysis payload or None."""
    if available_ops and op_name not in available_ops:
        print(f"[so] '{op_name}' NOT registered in this Kit ({len(available_ops)} ops available).")
        print(f"[so] (likely SO extension version too old for this op — using USD fallback)")
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


def _classify_attr(prim, attr):
    name = attr.GetName()
    if name == "visibility":             return "Visibility"
    if name.startswith("xformOp:"):      return "Xform"
    if name == "points":                 return "Mesh.points (deformation)"
    if name == "normals":                return "Mesh.normals"
    if name.startswith("primvars:displayColor") or name.startswith("primvars:displayOpacity"):
        return "DisplayColor/Opacity"
    if prim.IsA(UsdSkel.Animation):      return "Skel.Animation"
    if name.startswith("skel:") or name.startswith("primvars:skel:"):
        return "Skel.attr"
    if prim.GetTypeName() in ("Shader", "Material"): return "Material/Shader"
    if prim.IsA(UsdGeom.Camera):         return "Camera"
    return f"Other ({name})"


async def _anim_main():
    if STAGE_PATH:
        stage = Usd.Stage.Open(STAGE_PATH)
        print(f"[opened] {STAGE_PATH}")
    else:
        stage = omni.usd.get_context().get_stage()
        if stage is None:
            print("[error] No stage open.")
            return
        print(f"[using current stage] {stage.GetRootLayer().identifier}")

    print(f"[stage timecode] start={stage.GetStartTimeCode()} "
          f"end={stage.GetEndTimeCode()} fps={stage.GetTimeCodesPerSecond()}\n")

    # ---- SO introspection --------------------------------------------------
    core, available_ops = _get_so_core()
    if core is not None and available_ops is not None:
        print(f"[so] SO available — {len(available_ops)} registered operations.")

    # ---- 1) Primary: SO optimizeTimeSamples (analysis mode) ---------------
    print("=" * 78)
    print("SO optimizeTimeSamples — analysis mode")
    print("=" * 78)
    analysis = None
    if core is not None:
        so_args = {"paths": [], "removeInterpolated": False,
                   "epsilonD": 1e-12, "epsilonF": 1e-6}
        analysis = _call_so(core, "optimizeTimeSamples", so_args, stage, available_ops)
    else:
        print("[so] SO not loaded — USD fallback only.")
    await _yield()

    if analysis is None:
        pass
    elif isinstance(analysis, dict):
        # analysis = { attr_path: [redundant_count, total_count] }
        so_attrs = len(analysis)
        so_redundant_total = 0
        so_sample_total = 0
        per_attr_rows = []
        for ap, v in analysis.items():
            try:
                r = int(v[0]); t = int(v[1])
            except Exception:
                continue
            so_redundant_total += r
            so_sample_total += t
            per_attr_rows.append((ap, r, t))
        print(f"  Attributes with time samples : {so_attrs:,}")
        print(f"  Total time samples           : {so_sample_total:,}")
        print(f"  Redundant samples (removable): {so_redundant_total:,}")
        if so_sample_total > 0:
            pct = so_redundant_total / so_sample_total * 100.0
            print(f"  Redundancy ratio             : {pct:.2f}%")
        print()
        per_attr_rows.sort(key=lambda r: r[1], reverse=True)
        if per_attr_rows:
            print(f"  TOP {TOP_N} attributes by redundant-sample count:")
            print(f"  {'#':>3}  {'redundant':>10}  {'total':>10}  attr-path")
            for i, (ap, r, t) in enumerate(per_attr_rows[:TOP_N], 1):
                print(f"  {i:>3}  {r:>10,}  {t:>10,}  {ap}")
        print()
    else:
        print(f"  (non-dict analysis: {type(analysis).__name__})")
    await _yield()

    if not ENABLE_USD_FALLBACK:
        print("[done]")
        return

    # ---- 2) USD supplement: per-prim breakdown ----------------------------
    print("=" * 78)
    print("USD supplement — per-prim animation breakdown")
    print("=" * 78)

    prim_iter = (Usd.PrimRange.Stage(stage, Usd.TraverseInstanceProxies())
                 if INCLUDE_INSIDE_INSTANCES else stage.Traverse())

    category_count = Counter()
    category_samples = Counter()
    animated_prims = set()
    heaviest = []
    skel_anims = []
    n = 0
    n_anim_attrs = 0
    min_t = float("inf"); max_t = float("-inf")

    for prim in prim_iter:
        n += 1
        if n % YIELD_EVERY == 0: await _yield()
        if n % 5000 == 0:
            print(f"  ... {n} prims scanned (animated={len(animated_prims):,})")

        if prim.IsA(UsdSkel.Animation):
            skel_anims.append(str(prim.GetPath()))

        for attr in prim.GetAuthoredAttributes():
            ts = attr.GetTimeSamples()
            if not ts: continue
            n_anim_attrs += 1
            animated_prims.add(str(prim.GetPath()))
            cat = _classify_attr(prim, attr)
            category_count[cat] += 1
            category_samples[cat] += len(ts)
            t0, t1 = ts[0], ts[-1]
            if t0 < min_t: min_t = t0
            if t1 > max_t: max_t = t1

            verts = 0
            if attr.GetName() == "points" and prim.IsA(UsdGeom.Mesh):
                try:
                    pts = attr.Get(Usd.TimeCode(t0))
                    verts = len(pts) if pts else 0
                except Exception:
                    verts = 0
            heaviness = len(ts) * max(verts, 1)
            heaviest.append({
                "heaviness": heaviness, "samples": len(ts), "verts": verts,
                "path": str(prim.GetPath()), "attr": attr.GetName(), "category": cat,
            })

    await _yield()

    if not animated_prims:
        print("[result] No time-sampled attributes found.")
        return

    print(f"\n  Prims scanned                : {n:,}")
    print(f"  Animated prims (unique)      : {len(animated_prims):,}")
    print(f"  Animated attributes (total)  : {n_anim_attrs:,}")
    print(f"  Earliest sample time         : {min_t}")
    print(f"  Latest sample time           : {max_t}")
    print(f"  UsdSkel.Animation prims      : {len(skel_anims):,}\n")

    print(f"  {'category':<45}  {'attrs':>10}  {'samples':>14}")
    for cat, count in category_count.most_common():
        print(f"  {cat:<45}  {count:>10,}  {category_samples[cat]:>14,}")
    print()
    await _yield()

    pts_heavy = [h for h in heaviest if h["attr"] == "points"]
    pts_heavy.sort(key=lambda h: h["heaviness"], reverse=True)
    if pts_heavy:
        print("=" * 78)
        print(f"TOP {TOP_N} MESH DEFORMATION HOTSPOTS (animated points)")
        print("=" * 78)
        print(f"  {'#':>3}  {'samples':>10}  {'verts':>10}  {'heaviness':>14}  path")
        for i, h in enumerate(pts_heavy[:TOP_N], 1):
            print(f"  {i:>3}  {h['samples']:>10,}  {h['verts']:>10,}  "
                  f"{h['heaviness']:>14,}  {h['path']}")
        print()
    await _yield()

    by_samples = sorted(heaviest, key=lambda h: h["samples"], reverse=True)
    print("=" * 78)
    print(f"TOP {TOP_N} ANIMATED ATTRIBUTES BY SAMPLE COUNT")
    print("=" * 78)
    print(f"  {'#':>3}  {'samples':>10}  {'category':<35}  attr  path")
    for i, h in enumerate(by_samples[:TOP_N], 1):
        print(f"  {i:>3}  {h['samples']:>10,}  {h['category']:<35}  "
              f"{h['attr']}  {h['path']}")
    print()
    await _yield()

    if OUTPUT_CSV:
        try:
            with open(OUTPUT_CSV, "w", newline="") as f:
                w = csv.writer(f)
                w.writerow(["path", "attr", "category", "samples", "verts", "heaviness"])
                for h in by_samples:
                    w.writerow([h["path"], h["attr"], h["category"],
                                h["samples"], h["verts"], h["heaviness"]])
            print(f"[csv] wrote {OUTPUT_CSV}")
        except Exception as e:
            print(f"[csv] FAILED: {e}")

    print("\n[done]")


async def _wrapped():
    try:
        await _anim_main()
    except asyncio.CancelledError:
        print("[cancelled]")
        raise
    except Exception:
        print("[error] exception in async task:")
        traceback.print_exc()


def _on_done(t):
    try: t.result()
    except Exception: pass


_ANIM_TASK = asyncio.ensure_future(_wrapped())
_ANIM_TASK.add_done_callback(_on_done)
print("[started] async animation scan — cell returns now.")
print("           re-run this cell to cancel and restart.")
