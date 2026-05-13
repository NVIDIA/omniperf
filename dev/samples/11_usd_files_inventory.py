# =============================================================================
# USD Files Inventory — ASYNC version for Kit Script Editor
# -----------------------------------------------------------------------------
# Answers:
#   - How many separate USD files compose the current stage?
#   - How big is each individual USD file on disk?
#
# Method:
#   1) Use Sdf.Layer.GetLoadedLayers() to enumerate every loaded layer
#      (root layer + sublayers + reference/payload layers + session, etc.)
#   2) For each layer, resolve its real path via Layer.realPath
#   3) If the resolved path is a local file, os.path.getsize() it.
#      If it's a Nucleus/HTTP URL, mark size as "n/a (remote)".
#   4) Print summary + top-N largest files + extension breakdown
#   5) Write CSV to ./usd_files_inventory.csv
#
# IP-safe: file paths, sizes only. No geometry data leaves the stage.
# Re-running cancels previous run.
# =============================================================================

# ---- Tuning ----------------------------------------------------------------
TOP_N               = 30
OUTPUT_CSV          = "./usd_files_inventory.csv"
YIELD_EVERY         = 100
# ---------------------------------------------------------------------------

import asyncio
import csv
import os
import traceback
from collections import Counter

import omni.kit.app
import omni.usd
from pxr import Sdf

_GLOBAL = globals()
_prev = _GLOBAL.get("_USD_INVENTORY_TASK")
if _prev is not None and not _prev.done():
    print("[cancel] previous run is still active — cancelling it")
    _prev.cancel()


async def _yield():
    await omni.kit.app.get_app().next_update_async()


def _looks_remote(path):
    if not path:
        return False
    p = path.lower()
    return p.startswith(("omniverse://", "http://", "https://"))


async def _inventory_main():
    stage = omni.usd.get_context().get_stage()
    if stage is None:
        print("[error] no stage open")
        return

    root_id = stage.GetRootLayer().identifier if stage.GetRootLayer() else "?"
    print(f"[stage] {root_id}")

    # All loaded layers (process-wide).  Filter to those used by *this* stage
    # by intersecting with stage.GetUsedLayers().
    try:
        used = set(L.identifier for L in stage.GetUsedLayers())
    except Exception:
        used = None  # fall back to all loaded layers

    all_layers = Sdf.Layer.GetLoadedLayers()
    if used is not None:
        layers = [L for L in all_layers if L.identifier in used]
    else:
        layers = list(all_layers)

    print(f"[discovered] {len(layers)} loaded layers for this stage")
    await _yield()

    rows = []          # list of dict
    total_bytes = 0
    remote_count = 0
    missing_count = 0
    anon_count = 0
    ext_counter = Counter()

    for i, L in enumerate(layers):
        if i % YIELD_EVERY == 0 and i > 0:
            await _yield()

        ident = L.identifier
        real = L.realPath or ""
        is_anon = L.anonymous
        size = -1
        kind = "local"

        if is_anon:
            kind = "anonymous"
            anon_count += 1
        elif _looks_remote(real or ident):
            kind = "remote"
            remote_count += 1
        else:
            try:
                size = os.path.getsize(real) if real and os.path.exists(real) else -1
            except Exception:
                size = -1
            if size < 0:
                missing_count += 1
                kind = "missing_or_unresolved"
            else:
                total_bytes += size

        # File extension
        ext = os.path.splitext(real or ident)[1].lower()
        if ext.startswith("."):
            ext = ext[1:]
        ext_counter[ext or "(none)"] += 1

        rows.append({
            "identifier": ident,
            "real_path":  real,
            "kind":       kind,
            "ext":        ext or "",
            "size_bytes": size,
            "anonymous":  is_anon,
        })

    # ---- Summary ----------------------------------------------------------
    n_local = sum(1 for r in rows if r["kind"] == "local")
    print()
    print("=" * 78)
    print("USD FILES INVENTORY")
    print("=" * 78)
    print(f"  Total layers used by stage         : {len(rows):,}")
    print(f"    Local files (size measurable)    : {n_local:,}")
    print(f"    Remote (Nucleus/HTTP)            : {remote_count:,}")
    print(f"    Anonymous (in-memory only)       : {anon_count:,}")
    print(f"    Missing / unresolved             : {missing_count:,}")
    print(f"  Total size on disk (local only)    : {total_bytes:,} bytes "
          f"({total_bytes / (1024 * 1024):.2f} MiB)")

    # ---- Extension breakdown ---------------------------------------------
    if ext_counter:
        print()
        print("EXTENSION BREAKDOWN")
        for ext, n in ext_counter.most_common():
            print(f"  .{ext:<8}  {n:>6,}")

    await _yield()

    # ---- Top-N largest local files --------------------------------------
    local_sorted = sorted([r for r in rows if r["size_bytes"] >= 0],
                          key=lambda r: r["size_bytes"], reverse=True)
    if local_sorted:
        print()
        print("=" * 78)
        print(f"TOP {TOP_N} LARGEST LOCAL USD FILES")
        print("=" * 78)
        print(f"  {'#':>3}  {'size (MiB)':>12}  {'ext':>6}  path")
        for i, r in enumerate(local_sorted[:TOP_N], 1):
            mib = r["size_bytes"] / (1024 * 1024)
            shown = r["real_path"] or r["identifier"]
            print(f"  {i:>3}  {mib:>12.2f}  {r['ext']:>6}  {shown}")

    # ---- CSV --------------------------------------------------------------
    if OUTPUT_CSV:
        try:
            with open(OUTPUT_CSV, "w", newline="") as f:
                w = csv.writer(f)
                w.writerow(["identifier", "real_path", "kind", "ext",
                            "size_bytes", "anonymous"])
                for r in rows:
                    w.writerow([r["identifier"], r["real_path"], r["kind"],
                                r["ext"], r["size_bytes"], r["anonymous"]])
            print(f"\n[csv] wrote {OUTPUT_CSV} ({len(rows)} rows)")
        except Exception as e:
            print(f"\n[csv] write failed: {e}")

    print("\n[done]")


async def _wrapped():
    try:
        await _inventory_main()
    except asyncio.CancelledError:
        print("[cancelled]")
        raise
    except Exception:
        traceback.print_exc()


def _on_done(t):
    try: t.result()
    except Exception: pass


_USD_INVENTORY_TASK = asyncio.ensure_future(_wrapped())
_USD_INVENTORY_TASK.add_done_callback(_on_done)
print("[started] async USD inventory scan — cell returns now, work runs in background.")
print("           re-run this cell to cancel and restart.")
