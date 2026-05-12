# =============================================================================
# Instancing Analyzer — ASYNC version for Kit Script Editor
# -----------------------------------------------------------------------------
# Reports:
#   - UsdGeomPointInstancer count + total drawn instances
#   - Scene Graph Instances (prim.IsInstance / IsInstanceable) + prototype usage
#   - Instancing ratio: drawn meshes / unique mesh prototypes
#   - Unused prototypes (zero instances)
#   - Top prototypes by instance count
#
# Non-blocking, COUNT-only output (no geometry data leaves the stage).
# Usage: paste, Ctrl+Enter. Re-run cancels previous.
# =============================================================================

# ---- Tuning ----------------------------------------------------------------
TOP_N                    = 20
YIELD_EVERY              = 200
OUTPUT_CSV               = "/tmp/instancing.csv"
STAGE_PATH               = None
# ---------------------------------------------------------------------------

import asyncio
import csv
import traceback
from collections import defaultdict, Counter
from pxr import Usd, UsdGeom

import omni.usd
import omni.kit.app

_GLOBAL = globals()
_prev = _GLOBAL.get("_INSTANCING_TASK")
if _prev is not None and not _prev.done():
    print("[cancel] previous run is still active — cancelling it")
    _prev.cancel()


async def _yield():
    await omni.kit.app.get_app().next_update_async()


async def _instancing_main():
    # ---- Stage -------------------------------------------------------------
    if STAGE_PATH:
        stage = Usd.Stage.Open(STAGE_PATH)
        print(f"[opened] {STAGE_PATH}")
    else:
        stage = omni.usd.get_context().get_stage()
        if stage is None:
            print("[error] No stage open.")
            return
        print(f"[using current stage] {stage.GetRootLayer().identifier}")

    # ---- Pass 1: PointInstancer + Scene Graph Instance discovery ----------
    point_instancers = []         # (path, proto_count, total_indices)
    sgi_instance_prims = []       # prims where IsInstance() == True
    instanceable_prims = []       # prims with instanceable=true attr
    total_meshes_authored = 0     # Mesh prim count in the stage (NOT counting instance proxies)
    mesh_prims_total = 0
    n = 0

    # NOTE: Default traversal does NOT descend into instance prototypes.
    for prim in stage.Traverse():
        n += 1
        if n % YIELD_EVERY == 0:
            await _yield()
        if n % 2000 == 0:
            print(f"  ... pass1: {n} prims scanned")

        if prim.IsA(UsdGeom.PointInstancer):
            pi = UsdGeom.PointInstancer(prim)
            proto_paths = pi.GetPrototypesRel().GetTargets()
            proto_count = len(proto_paths)
            idx = pi.GetProtoIndicesAttr().Get()
            n_idx = len(idx) if idx else 0
            point_instancers.append({
                "path": str(prim.GetPath()),
                "proto_count": proto_count,
                "instances": n_idx,
                "protos": [str(p) for p in proto_paths],
                "proto_index_dist": dict(Counter(idx)) if idx else {},
            })

        if prim.IsInstance():
            # Scene-graph instance — points at a prototype root
            proto_root = prim.GetPrototype()
            sgi_instance_prims.append({
                "path": str(prim.GetPath()),
                "prototype": str(proto_root.GetPath()) if proto_root else "",
            })

        if prim.IsInstanceable():
            instanceable_prims.append(str(prim.GetPath()))

        if prim.IsA(UsdGeom.Mesh):
            mesh_prims_total += 1

    await _yield()

    # ---- Pass 2: count meshes inside instance prototypes -------------------
    # Walk the stage's master prims (instance prototypes).
    prototype_mesh_count = defaultdict(int)
    prototype_paths = set()
    for proto in stage.GetPrototypes():
        ppath = str(proto.GetPath())
        prototype_paths.add(ppath)
        cnt = 0
        sub_n = 0
        for sub in Usd.PrimRange(proto):
            sub_n += 1
            if sub_n % YIELD_EVERY == 0:
                await _yield()
            if sub.IsA(UsdGeom.Mesh):
                cnt += 1
        prototype_mesh_count[ppath] = cnt

    await _yield()

    # ---- Pass 3: traverse INTO instance proxies to count drawn meshes -----
    drawn_mesh_total = 0
    n2 = 0
    for prim in Usd.PrimRange.Stage(stage, Usd.TraverseInstanceProxies()):
        n2 += 1
        if n2 % YIELD_EVERY == 0:
            await _yield()
        if n2 % 5000 == 0:
            print(f"  ... pass3: {n2} prims scanned")
        if prim.IsA(UsdGeom.Mesh):
            drawn_mesh_total += 1

    await _yield()

    # ---- Summary -----------------------------------------------------------
    # Sum PointInstancer instances
    pi_total_instances = sum(p["instances"] for p in point_instancers)

    # Count SGI usage per prototype
    proto_usage = Counter(p["prototype"] for p in sgi_instance_prims if p["prototype"])

    unused_protos = [p for p in prototype_paths if proto_usage.get(p, 0) == 0]
    instancing_ratio = (drawn_mesh_total / mesh_prims_total) if mesh_prims_total else 0.0

    print("\n" + "=" * 78)
    print("INSTANCING SUMMARY")
    print("=" * 78)
    print(f"  Mesh prims (authored, no proxies)         : {mesh_prims_total:,}")
    print(f"  Mesh prims (drawn, including proxies)     : {drawn_mesh_total:,}")
    if mesh_prims_total > 0:
        print(f"  Instancing multiplier (drawn / authored)  : {instancing_ratio:.2f}x")
        if instancing_ratio < 1.05:
            print(f"    -> very LITTLE benefit from instancing in this stage")
        elif instancing_ratio < 2.0:
            print(f"    -> mild instancing")
        else:
            print(f"    -> strong instancing in use")
    print()
    print(f"  UsdGeomPointInstancer prims               : {len(point_instancers):,}")
    print(f"  Total points (instances) across them      : {pi_total_instances:,}")
    print()
    print(f"  Scene Graph Instance prims                : {len(sgi_instance_prims):,}")
    print(f"  Authored instanceable=true prims          : {len(instanceable_prims):,}")
    print(f"  Unique stage prototypes                   : {len(prototype_paths):,}")
    print(f"    of which unused (0 instances pointing)  : {len(unused_protos):,}")
    print()
    await _yield()

    # ---- Top PointInstancers ----------------------------------------------
    if point_instancers:
        print("=" * 78)
        print(f"TOP {TOP_N} POINT INSTANCERS BY INSTANCE COUNT")
        print("=" * 78)
        sorted_pi = sorted(point_instancers, key=lambda p: p["instances"], reverse=True)
        for i, p in enumerate(sorted_pi[:TOP_N], 1):
            print(f"  {i:>3}  instances={p['instances']:>10,}  "
                  f"protos={p['proto_count']:>4}  path={p['path']}")
        print()
    await _yield()

    # ---- Top prototypes by SGI usage --------------------------------------
    if proto_usage:
        print("=" * 78)
        print(f"TOP {TOP_N} SCENE GRAPH INSTANCE PROTOTYPES BY USAGE")
        print("=" * 78)
        for i, (proto, count) in enumerate(proto_usage.most_common(TOP_N), 1):
            meshes_in_proto = prototype_mesh_count.get(proto, 0)
            print(f"  {i:>3}  instances={count:>8,}  proto_meshes={meshes_in_proto:>6,}  "
                  f"prototype={proto}")
        print()
    await _yield()

    # ---- Unused prototypes -------------------------------------------------
    if unused_protos:
        print("=" * 78)
        print(f"UNUSED PROTOTYPES (no instances point here — dead memory)")
        print("=" * 78)
        for i, p in enumerate(sorted(unused_protos)[:TOP_N], 1):
            meshes_in_proto = prototype_mesh_count.get(p, 0)
            print(f"  {i:>3}  proto_meshes={meshes_in_proto:>6,}  prototype={p}")
        if len(unused_protos) > TOP_N:
            print(f"  ... and {len(unused_protos) - TOP_N} more")
        print()
    await _yield()

    # ---- CSV ---------------------------------------------------------------
    if OUTPUT_CSV:
        try:
            with open(OUTPUT_CSV, "w", newline="") as f:
                w = csv.writer(f)
                w.writerow(["category", "path", "instances_or_count",
                            "proto_count_or_meshes", "extra"])
                for p in point_instancers:
                    w.writerow(["PointInstancer", p["path"], p["instances"],
                                p["proto_count"], ""])
                for proto, count in proto_usage.most_common():
                    w.writerow(["SGI_Prototype", proto, count,
                                prototype_mesh_count.get(proto, 0), ""])
                for p in unused_protos:
                    w.writerow(["UnusedPrototype", p, 0,
                                prototype_mesh_count.get(p, 0), ""])
            print(f"[csv] wrote {OUTPUT_CSV}")
        except Exception as e:
            print(f"[csv] FAILED: {e}")

    print("\n[done]")


async def _wrapped():
    try:
        await _instancing_main()
    except asyncio.CancelledError:
        print("[cancelled]")
        raise
    except Exception:
        print("[error] exception in async task:")
        traceback.print_exc()


def _on_done(t):
    try: t.result()
    except Exception: pass


_INSTANCING_TASK = asyncio.ensure_future(_wrapped())
_INSTANCING_TASK.add_done_callback(_on_done)
print("[started] async instancing scan — cell returns now, work runs in background.")
print("           re-run this cell to cancel and restart.")
