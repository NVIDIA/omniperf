# =============================================================================
# Slab Analyzer — ASYNC, USD-based (no direct SO op for slab detection)
# -----------------------------------------------------------------------------
# Detects single-mesh "slabs" — flat plates that span most of the stage.
# Classifies:
#   - Floor slab   : huge XY footprint, very thin Z
#   - Wall slab    : huge XZ or YZ footprint, very thin in the remaining axis
#   - Generic slab : aspect ratio max/min > THIN_ASPECT
#   - Coverage     : single mesh covers > COVERAGE_PCT of stage XY footprint
#
# Non-blocking. COUNT/DIMENSION only.
# Usage: paste, Ctrl+Enter. Re-running cancels previous.
# =============================================================================

# ---- Tuning ----------------------------------------------------------------
TOP_N                    = 20
YIELD_EVERY              = 200
THIN_ASPECT              = 20.0       # max-dim / min-dim ratio to flag as plate
COVERAGE_PCT             = 30.0       # % of stage XY footprint
INCLUDE_INSIDE_INSTANCES = True
OUTPUT_CSV               = "./slabs.csv"
STAGE_PATH               = None
# ---------------------------------------------------------------------------

import asyncio
import csv
import traceback
from pxr import Usd, UsdGeom

import omni.usd
import omni.kit.app

_GLOBAL = globals()
_prev = _GLOBAL.get("_SLAB_TASK")
if _prev is not None and not _prev.done():
    print("[cancel] previous run is still active — cancelling it")
    _prev.cancel()


async def _yield():
    await omni.kit.app.get_app().next_update_async()


def _classify_slab(dx, dy, dz):
    dims = sorted([dx, dy, dz])  # ascending
    min_d, mid_d, max_d = dims
    if min_d <= 0:
        return None
    aspect = max_d / min_d
    if aspect < THIN_ASPECT:
        return None
    # Find the "thin" axis
    if dz == min_d:
        return "Floor (thin Z)"
    if dy == min_d:
        return "Wall (thin Y)"
    if dx == min_d:
        return "Wall (thin X)"
    return "Slab"


async def _slab_main():
    # ---- Stage -------------------------------------------------------------
    if STAGE_PATH:
        stage = Usd.Stage.Open(STAGE_PATH)
        print(f"[opened] {STAGE_PATH}")
    else:
        stage = omni.usd.get_context().get_stage()
        if stage is None:
            print("[error] No stage open.")
            return
        print(f"[using current stage] {stage.GetRootLayer().identifier}\n")

    bbox_cache = UsdGeom.BBoxCache(Usd.TimeCode.Default(),
                                   includedPurposes=[UsdGeom.Tokens.default_,
                                                     UsdGeom.Tokens.render],
                                   useExtentsHint=True)

    # Stage bbox
    stage_rng = bbox_cache.ComputeWorldBound(stage.GetPseudoRoot()).ComputeAlignedRange()
    if stage_rng.IsEmpty():
        print("[error] Stage bbox is empty.")
        return
    s = stage_rng.GetSize()
    stage_dx, stage_dy, stage_dz = float(s[0]), float(s[1]), float(s[2])
    stage_diag = (stage_dx**2 + stage_dy**2 + stage_dz**2) ** 0.5
    stage_xy_footprint = stage_dx * stage_dy
    stage_xz_footprint = stage_dx * stage_dz
    stage_yz_footprint = stage_dy * stage_dz

    print("=" * 78)
    print("STAGE BBOX")
    print("=" * 78)
    print(f"  dx={stage_dx:.3f}  dy={stage_dy:.3f}  dz={stage_dz:.3f}")
    print(f"  diag={stage_diag:.3f}")
    print(f"  XY footprint={stage_xy_footprint:.3f}  "
          f"XZ={stage_xz_footprint:.3f}  YZ={stage_yz_footprint:.3f}\n")

    # ---- Traverse ----------------------------------------------------------
    prim_iter = (Usd.PrimRange.Stage(stage, Usd.TraverseInstanceProxies())
                 if INCLUDE_INSIDE_INSTANCES else stage.Traverse())

    slabs = []
    n = 0
    for prim in prim_iter:
        if not prim.IsA(UsdGeom.Mesh): continue
        n += 1
        if n % YIELD_EVERY == 0: await _yield()
        if n % 5000 == 0:
            print(f"  ... {n} meshes scanned (slabs so far={len(slabs):,})")

        if UsdGeom.Imageable(prim).ComputeVisibility() == UsdGeom.Tokens.invisible:
            continue

        mesh = UsdGeom.Mesh(prim)
        pts = mesh.GetPointsAttr().Get()
        if not pts: continue
        verts = len(pts)

        rng = bbox_cache.ComputeWorldBound(prim).ComputeAlignedRange()
        if rng.IsEmpty(): continue
        m = rng.GetSize()
        dx, dy, dz = float(m[0]), float(m[1]), float(m[2])
        if dx <= 0 or dy <= 0 or dz <= 0: continue

        classification = _classify_slab(dx, dy, dz)
        if classification is None: continue

        # Footprint coverage (depending on slab orientation)
        if classification == "Floor (thin Z)":
            coverage = (dx * dy / stage_xy_footprint * 100.0) if stage_xy_footprint > 0 else 0
            coverage_label = "%XY"
        elif classification == "Wall (thin Y)":
            coverage = (dx * dz / stage_xz_footprint * 100.0) if stage_xz_footprint > 0 else 0
            coverage_label = "%XZ"
        elif classification == "Wall (thin X)":
            coverage = (dy * dz / stage_yz_footprint * 100.0) if stage_yz_footprint > 0 else 0
            coverage_label = "%YZ"
        else:
            coverage = 0
            coverage_label = "n/a"

        dims = sorted([dx, dy, dz])
        aspect = dims[2] / dims[0]

        slabs.append({
            "path": str(prim.GetPath()),
            "instance_proxy": bool(prim.IsInstanceProxy()),
            "class": classification,
            "verts": verts,
            "dx": dx, "dy": dy, "dz": dz,
            "aspect": aspect,
            "coverage_pct": coverage,
            "coverage_label": coverage_label,
        })

    await _yield()
    print(f"\n  Total meshes scanned         : {n:,}")
    print(f"  Slab candidates (aspect>{THIN_ASPECT:.0f}x): {len(slabs):,}\n")

    if not slabs:
        print("[result] No slab candidates found.")
        return

    # ---- Strong coverage candidates ---------------------------------------
    strong = sorted([r for r in slabs if r["coverage_pct"] > COVERAGE_PCT],
                    key=lambda r: r["coverage_pct"], reverse=True)
    print("=" * 78)
    print(f"STRONG SLAB CANDIDATES (footprint coverage > {COVERAGE_PCT:.0f}%)")
    print("=" * 78)
    if not strong:
        print(f"  (none — no slab covers more than {COVERAGE_PCT:.0f}% of its footprint)")
    else:
        for i, r in enumerate(strong[:TOP_N], 1):
            print(f"  {i:>3}  coverage={r['coverage_pct']:>6.1f}{r['coverage_label']}  "
                  f"class={r['class']:<20}  verts={r['verts']:>10,}  "
                  f"aspect={r['aspect']:>8.1f}x  path={r['path']}")
        if len(strong) > TOP_N:
            print(f"  ... and {len(strong) - TOP_N} more")
    print()
    await _yield()

    # ---- All slabs by aspect ---------------------------------------------
    by_aspect = sorted(slabs, key=lambda r: r["aspect"], reverse=True)
    print("=" * 78)
    print(f"TOP {TOP_N} SLAB CANDIDATES BY ASPECT RATIO")
    print("=" * 78)
    print(f"  {'#':>3}  {'aspect':>10}  {'class':<20}  "
          f"{'verts':>10}  {'cover':>8}  "
          f"{'dx':>8}  {'dy':>8}  {'dz':>8}  path")
    for i, r in enumerate(by_aspect[:TOP_N], 1):
        print(f"  {i:>3}  {r['aspect']:>9.1f}x  {r['class']:<20}  "
              f"{r['verts']:>10,}  {r['coverage_pct']:>6.1f}{r['coverage_label']}  "
              f"{r['dx']:>8.2f}  {r['dy']:>8.2f}  {r['dz']:>8.2f}  {r['path']}")
    print()
    await _yield()

    # ---- Dead-memory flag (huge bbox + low verts) -------------------------
    dead = [r for r in slabs if r["verts"] < 100 and r["aspect"] > THIN_ASPECT]
    dead.sort(key=lambda r: r["coverage_pct"], reverse=True)
    if dead:
        print("=" * 78)
        print("DEAD-MEMORY CANDIDATES (huge slab but <100 verts — likely placeholder)")
        print("=" * 78)
        for r in dead[:TOP_N]:
            print(f"  verts={r['verts']:>6,}  cover={r['coverage_pct']:>6.1f}{r['coverage_label']}  "
                  f"class={r['class']:<20}  path={r['path']}")
        if len(dead) > TOP_N:
            print(f"  ... and {len(dead) - TOP_N} more")
        print()
    await _yield()

    if OUTPUT_CSV:
        try:
            with open(OUTPUT_CSV, "w", newline="") as f:
                w = csv.writer(f)
                w.writerow(["path", "instance_proxy", "class", "verts",
                            "dx", "dy", "dz", "aspect",
                            "coverage_pct", "coverage_label"])
                for r in by_aspect:
                    w.writerow([r["path"], r["instance_proxy"], r["class"],
                                r["verts"],
                                f"{r['dx']:.4f}", f"{r['dy']:.4f}", f"{r['dz']:.4f}",
                                f"{r['aspect']:.2f}", f"{r['coverage_pct']:.4f}",
                                r["coverage_label"]])
            print(f"[csv] wrote {OUTPUT_CSV}")
        except Exception as e:
            print(f"[csv] FAILED: {e}")

    print("\n[done]")


async def _wrapped():
    try:
        await _slab_main()
    except asyncio.CancelledError:
        print("[cancelled]")
        raise
    except Exception:
        print("[error] exception in async task:")
        traceback.print_exc()


def _on_done(t):
    try: t.result()
    except Exception: pass


_SLAB_TASK = asyncio.ensure_future(_wrapped())
_SLAB_TASK.add_done_callback(_on_done)
print("[started] async slab scan — cell returns now.")
print("           re-run this cell to cancel and restart.")
