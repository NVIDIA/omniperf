# =============================================================================
# Standalone USD Disk Scanner — runs OUTSIDE Kit
# -----------------------------------------------------------------------------
# *** This is the ONLY script in this folder that does NOT run in Kit. ***
#     Run it from a regular Python shell (Windows: cmd / PowerShell ; Linux: bash).
#
# Why a standalone tool:
#   Before opening a heavy scene in Kit, customers often want to know how many
#   USD files are sitting in a folder and how big they are.  This walks a
#   directory tree with the OS only — no Kit, no USD libraries needed.
#
# What it answers:
#   - How many separate USD files (by extension: .usd / .usda / .usdc / .usdz)
#   - Total / per-file sizes on disk
#   - Top-N largest files
#   - Extension breakdown
#
# Dependencies:
#   Python 3.8+.  No pip install needed.
#
# Usage:
#   python standalone_usd_disk_scan.py <root_folder> [--csv out.csv] [--top 30]
#
#   Example:
#     python standalone_usd_disk_scan.py D:\customer\skt_factory
#     python standalone_usd_disk_scan.py /mnt/data/skt --csv ./skt_files.csv
# =============================================================================

import argparse
import csv
import os
import sys
from collections import Counter


USD_EXTS = (".usd", ".usda", ".usdc", ".usdz")


def main(argv=None):
    ap = argparse.ArgumentParser(description="Standalone USD file inventory (no Kit needed).")
    ap.add_argument("root", help="Root folder to scan (recursively).")
    ap.add_argument("--csv", default="./standalone_usd_disk_scan.csv",
                    help="Output CSV path (default: ./standalone_usd_disk_scan.csv).")
    ap.add_argument("--top", type=int, default=30,
                    help="Print Top-N largest files (default: 30).")
    args = ap.parse_args(argv)

    root = args.root
    if not os.path.isdir(root):
        print(f"[error] not a directory: {root}", file=sys.stderr)
        return 2

    print(f"[scanning] {os.path.abspath(root)}")

    rows = []
    ext_counter = Counter()
    total_bytes = 0
    errors = 0

    for dirpath, _dirnames, filenames in os.walk(root):
        for fn in filenames:
            ext = os.path.splitext(fn)[1].lower()
            if ext not in USD_EXTS:
                continue
            full = os.path.join(dirpath, fn)
            try:
                size = os.path.getsize(full)
            except OSError:
                errors += 1
                size = -1
            ext_counter[ext] += 1
            if size >= 0:
                total_bytes += size
            rows.append((full, ext, size))

    n = len(rows)
    print()
    print("=" * 78)
    print("USD FILES ON DISK")
    print("=" * 78)
    print(f"  Root                                : {os.path.abspath(root)}")
    print(f"  Total USD files                     : {n:,}")
    print(f"  Total size on disk                  : {total_bytes:,} bytes "
          f"({total_bytes / (1024 * 1024):.2f} MiB ; {total_bytes / (1024 ** 3):.3f} GiB)")
    print(f"  Read errors                         : {errors:,}")

    if ext_counter:
        print()
        print("EXTENSION BREAKDOWN")
        for ext, c in ext_counter.most_common():
            print(f"  {ext:<8}  {c:>6,}")

    # Top-N largest
    rows_sorted = sorted([r for r in rows if r[2] >= 0],
                         key=lambda r: r[2], reverse=True)
    if rows_sorted:
        print()
        print("=" * 78)
        print(f"TOP {args.top} LARGEST USD FILES")
        print("=" * 78)
        print(f"  {'#':>3}  {'size (MiB)':>12}  {'ext':>6}  path")
        for i, (path, ext, size) in enumerate(rows_sorted[: args.top], 1):
            mib = size / (1024 * 1024)
            print(f"  {i:>3}  {mib:>12.2f}  {ext:>6}  {path}")

    # CSV
    try:
        with open(args.csv, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["path", "ext", "size_bytes"])
            for path, ext, size in rows:
                w.writerow([path, ext, size])
        print(f"\n[csv] wrote {os.path.abspath(args.csv)} ({n} rows)")
    except Exception as e:
        print(f"\n[csv] write failed: {e}")

    print("\n[done]")
    return 0


if __name__ == "__main__":
    sys.exit(main())
