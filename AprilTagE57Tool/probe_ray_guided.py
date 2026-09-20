#!/usr/bin/env python3
"""Probe ray-guided LiDAR re-observation on one scan."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

import numpy as np
from mye57 import E57

from e57_tags.fusion import FusedTag, fuse_observations
from e57_tags.ray_guided import RayGuidedConfig, reobserve_tags_in_scan


def load_fused_csv(path: Path) -> list[FusedTag]:
    tags: list[FusedTag] = []
    with path.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f, delimiter=";"):
            tags.append(
                FusedTag(
                    family=row["family"],
                    tag_id=int(row["tag_id"]),
                    center_e57=np.array([float(row["x"]), float(row["y"]), float(row["z"])]),
                    center_project=None,
                    sigma_m=float(row.get("sigma_m", 0)),
                )
            )
    return tags


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("e57", type=Path)
    parser.add_argument("--fused-csv", type=Path, required=True)
    parser.add_argument("--known", type=str, default="472,297,538,364,108,197,502")
    args = parser.parse_args()

    known = {int(x) for x in args.known.split(",") if x.strip()}
    fused = load_fused_csv(args.fused_csv)
    scan_name = args.e57.stem

    e57 = E57(str(args.e57))
    try:
        data = e57.read_scan(0, intensity=True, row_column=True, ignore_missing_fields=True)
        xyz = np.stack([data["cartesianX"], data["cartesianY"], data["cartesianZ"]], axis=1)
        rows, cols = data["rowIndex"], data["columnIndex"]
        scanner = np.array(e57.get_header(0).translation, dtype=np.float64)

        obs = reobserve_tags_in_scan(
            fused,
            scan_name=scan_name,
            xyz=xyz,
            rows=rows,
            cols=cols,
            scanner_pos=scanner,
            already_seen=set(),
            export_fn=lambda p: p,
            config=RayGuidedConfig(),
        )
        print(f"Scan {scan_name}: {len(obs)} ray-guided hits")
        for o in sorted(obs, key=lambda x: x.tag_id):
            mark = "*" if o.tag_id in known else " "
            c = o.center_e57
            miss = next(
                float(np.linalg.norm(c - t.center_e57) * 1000)
                for t in fused
                if t.tag_id == o.tag_id
            )
            print(
                f"{mark} id={o.tag_id:4d} miss={miss:5.1f}mm "
                f"d={o.distance:.1f}m ({c[0]:.2f},{c[1]:.2f},{c[2]:.2f})"
            )
        found_known = sorted({o.tag_id for o in obs} & known)
        print(f"Known refs: {found_known} / {len(known)}")
    finally:
        e57.close()


if __name__ == "__main__":
    main()
