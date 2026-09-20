#!/usr/bin/env python3
"""Compare pano detection at different downscale factors."""

from __future__ import annotations

import argparse
import time
from pathlib import Path

from e57_tags.pano_detector import detect_in_panorama, find_pano_image


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pano-dir", type=Path, required=True)
    parser.add_argument("--scans", type=str, default="13-17", help="e.g. 1-17 or 13-17 or 1,5,13")
    parser.add_argument("--scales", type=str, default="2,1")
    parser.add_argument("--known", type=str, default="108,197,297,364,472,502,538")
    args = parser.parse_args()

    known = {int(x) for x in args.known.split(",") if x.strip()}
    scales = [int(x) for x in args.scales.split(",")]

    if "-" in args.scans:
        a, b = args.scans.split("-", 1)
        scan_ids = list(range(int(a), int(b) + 1))
    else:
        scan_ids = [int(x) for x in args.scans.split(",") if x.strip()]

    totals: dict[int, set[int]] = {s: set() for s in scales}
    print(f"{'scan':14s}", end="")
    for sc in scales:
        print(f"  scale={sc:>2d} (uniq/known/time)", end="")
    print()
    print("-" * 70)

    for i in scan_ids:
        name = f"new_fasade_{i:02d}"
        path = find_pano_image(args.pano_dir, name)
        if path is None:
            print(f"{name:14s}  NO PANO")
            continue
        print(f"{name:14s}", end="")
        for sc in scales:
            t0 = time.perf_counter()
            dets = detect_in_panorama(path, families=["tag36h11"], detect_scale=sc)
            dt = time.perf_counter() - t0
            ids = {d.tag_id for d in dets}
            totals[sc] |= ids
            kn = sorted(ids & known)
            print(f"  {len(ids):3d}/{len(kn)} {kn} {dt:5.0f}s", end="")
        print()

    print("-" * 70)
    print("TOTAL unique:", {sc: len(totals[sc]) for sc in scales})
    for sc in scales:
        only = totals[sc] - totals[scales[0]] if sc != scales[0] else totals[sc] - totals[scales[1]]
        if sc == scales[0]:
            other = scales[1] if len(scales) > 1 else sc
            only = totals[sc] - totals.get(other, set())
        print(f"  scale={sc} only (not in other): {sorted(only)}")


if __name__ == "__main__":
    main()
