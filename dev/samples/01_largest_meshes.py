# =============================================================================
# Largest Meshes Analyzer — ASYNC version for Kit Script Editor
# -----------------------------------------------------------------------------
# Non-blocking: yields back to Kit's event loop every YIELD_EVERY meshes,
# so the UI stays responsive on large stages.
#
# Usage:
#   1) Paste into Window > Script Editor
#   2) Tweak the TUNING constants if needed
#   3) Run (Ctrl+Enter)  → cell returns immediately; work happens in background
#   4) Watch the Script Editor output for progress and final report
#
# Re-running cancels the previous run automatically.
#
# Output: COUNT / DIMENSION only — no vertex data leaves the stage.
# =============================================================================

# ---- Tuning ----------------------------------------------------------------
TOP_N                    = 20
INCLUDE_INVISIBLE        = False
INCLUDE_INSIDE_INSTANCES = True
TIME_CODE                = None
YIELD_EVERY              = 100         # meshes processed between UI yields
PROGRESS_EVERY           = 500         # progress print interval
OUTPUT_CSV               = "/tmp/largest_meshes.csv"
STAGE_PATH               = None
# ---------------------------------------------------------------------------

import asyncio
import csv
import statistics
import traceback
from pxr import Usd, UsdGeom

import omni.usd
import omni.kit.app

# ---- Cancel any previous run -----------------------------------------------
_GLOBAL = globals()
_prev = _GLOBAL.get("_LARGEST_MESHES_TASK")
if _prev is not None and not _prev.done():
    print("[cancel] previous run is still active — cancelling it")
    _prev.cancel()


async def _yield_to_ui():
    """Yield one frame back to the Kit event loop."""
    await omni.kit.app.get_app().next_update_async()


async def _largest_meshes_main():
    # ---- 1) Resolve stage --------------------------------------------------
    if STAGE_PATH:
        stage = Usd.Stage.Open(STAGE_PATH)
        print(f"[opened] {STAGE_PATH}")
    else:
        stage = omni.usd.get_context().get_stage()
        if stage is None:
            print("[error] No stage open. Open a USD file or set STAGE_PATH.")
            return
        print(f"[using current stage] {stage.GetRootLayer().identifier}")

    time_code = Usd.TimeCode.Default() if TIME_CODE is None else Usd.TimeCode(TIME_CODE)

    # ---- 2) BBoxCache ------------------------------------------------------
    purposes = [UsdGeom.Tokens.default_, UsdGeom.Tokens.render]
    if INCLUDE_INVISIBLE:
        purposes += [UsdGeom.Tokens.guide, UsdGeom.Tokens.proxy]
    bbox_cache = UsdGeom.BBoxCache(time_code, includedPurposes=purposes,
                                   useExtentsHint=True)

    # ---- 3) Traverse + collect --------------------------------------------
    if INCLUDE_INSIDE_INSTANCES:
        prim_iter = Usd.PrimRange.Stage(stage, Usd.TraverseInstanceProxies())
    else:
        prim_iter = stage.Traverse()

    results, skipped_empty, skipped_invis, mesh_count = [], 0, 0, 0
    await _yield_to_ui()

    for prim in prim_iter:
        if not prim.IsA(UsdGeom.Mesh):
            continue

        mesh_count += 1

        # Periodic yield to keep UI responsive
        if mesh_count % YIELD_EVERY == 0:
            await _yield_to_ui()
        if mesh_count % PROGRESS_EVERY == 0:
            print(f"  ... {mesh_count} meshes scanned (kept {len(results)})")

        # Visibility filter
        if not INCLUDE_INVISIBLE:
            if UsdGeom.Imageable(prim).ComputeVisibility(time_code) == UsdGeom.Tokens.invisible:
                skipped_invis += 1
                continue

        mesh = UsdGeom.Mesh(prim)
        pts = mesh.GetPointsAttr().Get(time_code)
        vert_count = len(pts) if pts else 0
        if vert_count == 0:
            skipped_empty += 1
            continue

        fvc = mesh.GetFaceVertexCountsAttr().Get(time_code)
        face_count = len(fvc) if fvc else 0

        rng = bbox_cache.ComputeWorldBound(prim).ComputeAlignedRange()
        if rng.IsEmpty():
            dx = dy = dz = diag = vol = 0.0
        else:
            s = rng.GetSize()
            dx, dy, dz = float(s[0]), float(s[1]), float(s[2])
            diag = (dx * dx + dy * dy + dz * dz) ** 0.5
            vol = abs(dx * dy * dz)

        results.append({
            "path": str(prim.GetPath()),
            "instance_proxy": bool(prim.IsInstanceProxy()),
            "verts": vert_count, "faces": face_count,
            "dx": dx, "dy": dy, "dz": dz,
            "diag": diag, "vol": vol,
        })

    print(f"\n[scan complete] {mesh_count} meshes seen | "
          f"kept {len(results)} | empty {skipped_empty} | "
          f"invisible {skipped_invis}\n")
    await _yield_to_ui()

    if not results:
        print("No meshes to analyze.")
        return

    # ---- 4) Stage stats ----------------------------------------------------
    verts = [r["verts"] for r in results]
    stage_rng = bbox_cache.ComputeWorldBound(stage.GetPseudoRoot()).ComputeAlignedRange()
    if not stage_rng.IsEmpty():
        s = stage_rng.GetSize()
        stage_diag = (float(s[0])**2 + float(s[1])**2 + float(s[2])**2) ** 0.5
        stage_vol = abs(float(s[0]) * float(s[1]) * float(s[2]))
    else:
        stage_diag = stage_vol = 0.0

    print("=" * 78)
    print("STAGE STATS")
    print("=" * 78)
    print(f"  Total meshes (analyzed)  : {len(results):,}")
    print(f"  Total vertices           : {sum(verts):,}")
    print(f"  Median verts/mesh        : {int(statistics.median(verts)):,}")
    print(f"  p95 verts/mesh           : "
          f"{int(sorted(verts)[int(0.95 * (len(verts)-1))]):,}")
    print(f"  Max verts/mesh           : {max(verts):,}")
    print(f"  Stage bbox diag (world)  : {stage_diag:.3f}")
    print(f"  Stage bbox volume        : {stage_vol:.3f}\n")
    await _yield_to_ui()

    # ---- 5) Ranking print helper ------------------------------------------
    def _print_top(title, sr):
        print("=" * 78); print(title); print("=" * 78)
        print(f"  {'#':>3}  {'verts':>10}  {'faces':>10}  "
              f"{'dx':>10}  {'dy':>10}  {'dz':>10}  {'diag':>10}  "
              f"{'%stg':>6}  {'inst':>4}  path")
        for i, r in enumerate(sr[:TOP_N], 1):
            pct = (r["diag"] / stage_diag * 100.0) if stage_diag > 0 else 0.0
            print(f"  {i:>3}  {r['verts']:>10,}  {r['faces']:>10,}  "
                  f"{r['dx']:>10.2f}  {r['dy']:>10.2f}  {r['dz']:>10.2f}  "
                  f"{r['diag']:>10.2f}  {pct:>5.1f}%  "
                  f"{'I' if r['instance_proxy'] else '-':>4}  {r['path']}")
        print()

    by_verts = sorted(results, key=lambda r: r["verts"], reverse=True)
    await _yield_to_ui()
    by_diag = sorted(results, key=lambda r: r["diag"], reverse=True)
    await _yield_to_ui()
    by_vol = sorted(results, key=lambda r: r["vol"], reverse=True)
    await _yield_to_ui()

    _print_top(f"TOP {TOP_N} BY VERTEX COUNT", by_verts)
    _print_top(f"TOP {TOP_N} BY WORLD BBOX DIAGONAL (largest physical meshes)", by_diag)
    _print_top(f"TOP {TOP_N} BY WORLD BBOX VOLUME", by_vol)
    await _yield_to_ui()

    # ---- 6) Slab candidates -----------------------------------------------
    if stage_diag > 0:
        slabs = sorted([r for r in results if r["diag"] / stage_diag > 0.5],
                       key=lambda r: r["diag"], reverse=True)
        print("=" * 78)
        print("SLAB CANDIDATES (single mesh diag > 50% of stage diag)")
        print("=" * 78)
        if not slabs:
            print("  (none — no single mesh spans more than half the stage)")
        else:
            for r in slabs:
                pct = r["diag"] / stage_diag * 100.0
                print(f"  {pct:>6.1f}% stage | verts={r['verts']:>10,} | "
                      f"diag={r['diag']:>10.2f} | path={r['path']}")
        print()
    await _yield_to_ui()

    # ---- 7) CSV ------------------------------------------------------------
    if OUTPUT_CSV:
        try:
            with open(OUTPUT_CSV, "w", newline="") as f:
                w = csv.writer(f)
                w.writerow(["path", "instance_proxy", "verts", "faces",
                            "dx", "dy", "dz", "diag", "vol"])
                for r in by_verts:
                    w.writerow([r["path"], r["instance_proxy"],
                                r["verts"], r["faces"],
                                f"{r['dx']:.4f}", f"{r['dy']:.4f}",
                                f"{r['dz']:.4f}", f"{r['diag']:.4f}",
                                f"{r['vol']:.4f}"])
            print(f"[csv] wrote {OUTPUT_CSV} ({len(results)} rows)")
        except Exception as e:
            print(f"[csv] FAILED: {e}")

    print("\n[done]")


# ---- Wrap to surface exceptions (async tasks otherwise swallow them) ------
async def _wrapped():
    try:
        await _largest_meshes_main()
    except asyncio.CancelledError:
        print("[cancelled]")
        raise
    except Exception:
        print("[error] exception in async task:")
        traceback.print_exc()


def _on_done(t: asyncio.Task):
    try:
        t.result()
    except asyncio.CancelledError:
        pass
    except Exception:
        # Already printed inside _wrapped, but keep this for safety
        pass


# ---- Start --------------------------------------------------------------
_LARGEST_MESHES_TASK = asyncio.ensure_future(_wrapped())
_LARGEST_MESHES_TASK.add_done_callback(_on_done)
print("[started] async largest-meshes scan — cell returns now, work runs in background.")
print("           re-run this cell to cancel and restart.")
