# =============================================================================
# Pipe Geometry Detail — ASYNC, USD-only, HEURISTIC
# -----------------------------------------------------------------------------
# Builds on 10_pipe_density.py — answers the follow-up questions:
#
#   (A) How many pipes are there?
#   (B) How many triangles are in the pipes (total + per-pipe avg/median)?
#   (C) Are the pipes instanced?
#         - count pipe meshes that are inside instance prototypes
#         - count pipe meshes that have IsInstanceable() / IsInstance()
#   (D) Are they named in a way that makes them easy to identify as pipes?
#         - scan prim names + their ancestors for naming patterns:
#           "pipe", "tube", "conduit", "duct", "cylinder", "pipework"
#         - case-insensitive
#         - reports % of pipe-like meshes that have an identifiable name
#
# IMPORTANT — same caveat as 10_pipe_density.py:
# USD has no semantic "pipe". This uses the same bbox/elongation heuristic
# as script 10 to *classify* a mesh as cylinder-like, then computes the
# additional details on that subset.
#
# IP-safe: count / dimensions / names only. Read-only.
# Re-running cancels previous run.
# =============================================================================

# ---- Tuning (kept identical to 10_pipe_density.py for consistency) ---------
ELONGATION_RATIO         = 5.0
MIN_VERTS                = 6
MAX_VERTS                = 5000
TOP_N                    = 20
YIELD_EVERY              = 200
OUTPUT_CSV               = "./pipe_geometry_detail.csv"

# Naming heuristic — case-insensitive substring match against prim name +
# ancestor names. Add/remove tokens as needed for the customer's data.
NAME_TOKENS = ("pipe", "tube", "conduit", "duct", "pipework", "piping",
               "cylinder", "tubing")
# ---------------------------------------------------------------------------

import asyncio
import csv
import statistics
import traceback

import omni.kit.app
import omni.usd
from pxr import Usd, UsdGeom

_GLOBAL = globals()
_prev = _GLOBAL.get("_PIPE_DETAIL_TASK")
if _prev is not None and not _prev.done():
    print("[cancel] previous run is still active — cancelling it")
    _prev.cancel()


async def _yield():
    await omni.kit.app.get_app().next_update_async()


def _classify(dx, dy, dz):
    dims = sorted([dx, dy, dz], reverse=True)
    long_len, second_len, short_len = dims
    if long_len <= 0 or second_len <= 0:
        return False, long_len, second_len, short_len
    if (long_len / max(second_len, 1e-9)) < ELONGATION_RATIO:
        return False, long_len, second_len, short_len
    if second_len > 0 and short_len / second_len < 0.5:
        return False, long_len, second_len, short_len
    return True, long_len, second_len, short_len


def _triangles_from_facevertex_counts(fvc):
    """Approximate triangle count from face-vertex-counts:
       each face with N verts -> (N-2) triangles."""
    if not fvc:
        return 0
    tri = 0
    for n in fvc:
        if n >= 3:
            tri += (n - 2)
    return tri


def _name_match(prim):
    """Return matched-token or None.  Checks prim name and ancestors."""
    cur = prim
    while cur and cur.GetPath() != cur.GetPath().GetParentPath():
        name = cur.GetName().lower()
        for tok in NAME_TOKENS:
            if tok in name:
                return tok
        cur = cur.GetParent()
    return None


async def _pipe_detail_main():
    stage = omni.usd.get_context().get_stage()
    if stage is None:
        print("[error] no stage open")
        return
    print(f"[stage] {stage.GetRootLayer().identifier}")

    bbox_cache = UsdGeom.BBoxCache(Usd.TimeCode.Default(),
                                   [UsdGeom.Tokens.default_, UsdGeom.Tokens.render])

    # Collected per pipe-like mesh
    pipes = []           # list of dict (path, verts, tris, long, short1, short2,
                         #               instanced, instance_proxy, name_match)

    total_meshes = 0
    n_yield = 0

    # IMPORTANT: descend into instance proxies so we count instanced pipes too.
    prim_iter = Usd.PrimRange.Stage(stage, Usd.TraverseInstanceProxies())

    for prim in prim_iter:
        if not prim.IsA(UsdGeom.Mesh):
            continue
        total_meshes += 1

        try:
            mesh = UsdGeom.Mesh(prim)
            pts = mesh.GetPointsAttr().Get()
            n_verts = len(pts) if pts else 0
        except Exception:
            n_verts = 0
        if n_verts < MIN_VERTS or n_verts > MAX_VERTS:
            n_yield += 1
            if n_yield >= YIELD_EVERY:
                n_yield = 0
                await _yield()
            continue

        try:
            bbox = bbox_cache.ComputeWorldBound(prim).ComputeAlignedBox()
            mn, mx = bbox.GetMin(), bbox.GetMax()
            dx = float(mx[0] - mn[0]); dy = float(mx[1] - mn[1]); dz = float(mx[2] - mn[2])
        except Exception:
            continue

        is_pipe, L, S2, S3 = _classify(dx, dy, dz)
        if not is_pipe:
            n_yield += 1
            if n_yield >= YIELD_EVERY:
                n_yield = 0
                await _yield()
            continue

        # Triangle count
        try:
            fvc = mesh.GetFaceVertexCountsAttr().Get()
            tris = _triangles_from_facevertex_counts(fvc)
        except Exception:
            tris = 0

        # Instancing
        is_proxy   = bool(prim.IsInstanceProxy())
        is_inst    = bool(prim.IsInstance())
        is_instable = bool(prim.IsInstanceable())
        # Any of these → effectively benefits from instancing
        instanced = is_proxy or is_inst or is_instable

        # Naming
        name_tok = _name_match(prim)

        pipes.append({
            "path":        str(prim.GetPath()),
            "verts":       n_verts,
            "tris":        tris,
            "long":        L,
            "short1":      S2,
            "short2":      S3,
            "instanced":   instanced,
            "is_proxy":    is_proxy,
            "is_inst":     is_inst,
            "is_instable": is_instable,
            "name_token":  name_tok or "",
        })

        n_yield += 1
        if n_yield >= YIELD_EVERY:
            n_yield = 0
            await _yield()
            if (total_meshes % (YIELD_EVERY * 25)) == 0:
                print(f"  ... {total_meshes:,} meshes scanned (pipes so far={len(pipes):,})")

    n_pipes = len(pipes)
    print()
    print("=" * 78)
    print("PIPE GEOMETRY DETAIL (heuristic)")
    print("=" * 78)
    print(f"  Total meshes scanned                 : {total_meshes:,}")
    print(f"  Pipe-like meshes (heuristic)         : {n_pipes:,}  "
          f"({100.0 * n_pipes / max(total_meshes, 1):.1f}%)")
    if n_pipes == 0:
        print("  (no pipe-like meshes — nothing else to report)")
        return

    # ---- (B) Triangle counts ---------------------------------------------
    tris_list = [p["tris"] for p in pipes if p["tris"] > 0]
    total_tris = sum(tris_list)
    print()
    print("TRIANGLE COUNTS IN PIPES")
    print(f"  Total triangles in pipes             : {total_tris:,}")
    if tris_list:
        print(f"  Mean tris/pipe                       : {total_tris / len(tris_list):.1f}")
        print(f"  Median tris/pipe                     : {int(statistics.median(tris_list)):,}")
        print(f"  Min / Max tris per pipe              : {min(tris_list):,} / {max(tris_list):,}")
        if len(tris_list) >= 20:
            sl = sorted(tris_list)
            p95 = sl[int(0.95 * (len(sl) - 1))]
            print(f"  p95 tris/pipe                        : {p95:,}")

    # ---- (C) Instancing on pipes -----------------------------------------
    n_inst = sum(1 for p in pipes if p["instanced"])
    n_proxy = sum(1 for p in pipes if p["is_proxy"])
    n_isinst = sum(1 for p in pipes if p["is_inst"])
    n_instable = sum(1 for p in pipes if p["is_instable"])
    print()
    print("INSTANCING ON PIPES")
    print(f"  Pipes that are instanced (any form)  : {n_inst:,}  "
          f"({100.0 * n_inst / n_pipes:.1f}%)")
    print(f"    of which IsInstanceProxy()         : {n_proxy:,}")
    print(f"    of which IsInstance()              : {n_isinst:,}")
    print(f"    of which IsInstanceable()          : {n_instable:,}")
    if n_inst == 0:
        print("  -> pipes are NOT instanced — deduplicateGeometry "
              "(method=Instanceable Reference) is a strong candidate")
    elif n_inst / n_pipes < 0.5:
        print("  -> only some pipes are instanced — partial benefit, "
              "dedup may still help")

    # ---- (D) Naming identifiability --------------------------------------
    n_named = sum(1 for p in pipes if p["name_token"])
    print()
    print("PIPE NAMING IDENTIFIABILITY")
    print(f"  Pipes whose name/ancestor matches    : {n_named:,}  "
          f"({100.0 * n_named / n_pipes:.1f}%)")
    if n_named > 0:
        tok_counter = {}
        for p in pipes:
            t = p["name_token"]
            if t:
                tok_counter[t] = tok_counter.get(t, 0) + 1
        print("  Token breakdown:")
        for t, c in sorted(tok_counter.items(), key=lambda x: x[1], reverse=True):
            print(f"    {t:<10}  {c:>6,}")
    else:
        print("  -> pipe prims do NOT have identifying names — selection "
              "for SO ops needs path-based or heuristic filtering")
    print(f"  Tokens checked: {', '.join(NAME_TOKENS)}")

    # ---- Top-N -----------------------------------------------------------
    print()
    print("=" * 78)
    print(f"TOP {TOP_N} PIPE-LIKE MESHES BY TRIANGLE COUNT")
    print("=" * 78)
    pipes_by_tris = sorted(pipes, key=lambda p: p["tris"], reverse=True)
    for i, p in enumerate(pipes_by_tris[:TOP_N], 1):
        inst = "I" if p["instanced"] else "-"
        nm = p["name_token"] if p["name_token"] else "?"
        print(f"  {i:>3}  tris={p['tris']:>8,}  verts={p['verts']:>6,}  "
              f"long={p['long']:>8.2f}  inst={inst}  name={nm:<8}  {p['path']}")

    # ---- CSV -------------------------------------------------------------
    if OUTPUT_CSV:
        try:
            with open(OUTPUT_CSV, "w", newline="") as f:
                w = csv.writer(f)
                w.writerow(["path", "verts", "tris", "long", "short1", "short2",
                            "instanced", "is_proxy", "is_inst", "is_instable",
                            "name_token"])
                for p in pipes_by_tris:
                    w.writerow([p["path"], p["verts"], p["tris"],
                                f"{p['long']:.4f}", f"{p['short1']:.4f}",
                                f"{p['short2']:.4f}",
                                p["instanced"], p["is_proxy"], p["is_inst"],
                                p["is_instable"], p["name_token"]])
            print(f"\n[csv] wrote {OUTPUT_CSV} ({len(pipes)} rows)")
        except Exception as e:
            print(f"\n[csv] write failed: {e}")

    print("\n[done]")


async def _wrapped():
    try:
        await _pipe_detail_main()
    except asyncio.CancelledError:
        print("[cancelled]")
        raise
    except Exception:
        traceback.print_exc()


def _on_done(t):
    try: t.result()
    except Exception: pass


_PIPE_DETAIL_TASK = asyncio.ensure_future(_wrapped())
_PIPE_DETAIL_TASK.add_done_callback(_on_done)
print("[started] async pipe-geometry-detail scan — cell returns now, work runs in background.")
print("           re-run this cell to cancel and restart.")
