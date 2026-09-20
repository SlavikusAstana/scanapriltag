"""CSV export for fused AprilTag centers."""

from __future__ import annotations

import csv
from pathlib import Path

import numpy as np

from .fusion import FusedTag, TagObservation
from .register360_db import CoordExportMode


def export_csv(
    tags: list[FusedTag],
    path: Path,
    *,
    coord_mode: CoordExportMode = CoordExportMode.ACTIVE,
) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    if coord_mode == CoordExportMode.GLOBAL:
        headers = [
            "family", "tag_id", "x_global", "y_global", "z_global", "sigma_m",
            "observations", "weight_sum", "min_distance_m", "max_distance_m", "scans", "best_scan",
        ]
    else:
        headers = [
            "family", "tag_id", "x", "y", "z", "sigma_m",
            "observations", "weight_sum", "min_distance_m", "max_distance_m", "scans", "best_scan",
        ]

    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, delimiter=";")
        writer.writerow(headers)
        for tag in tags:
            center = tag.center_project if tag.center_project is not None else tag.center_e57
            dists = [o.distance for o in tag.observations]
            scans = ",".join(sorted({o.scan_name for o in tag.observations}))
            writer.writerow(
                [
                    tag.family,
                    tag.tag_id,
                    f"{center[0]:.6f}",
                    f"{center[1]:.6f}",
                    f"{center[2]:.6f}",
                    f"{tag.sigma_m:.6f}",
                    tag.observation_count,
                    f"{tag.weight_sum:.4f}",
                    f"{min(dists):.3f}",
                    f"{max(dists):.3f}",
                    scans,
                    tag.best_scan or "",
                ]
            )


def export_compare_csv(
    observations: list[TagObservation],
    path: Path,
    *,
    coord_mode: CoordExportMode = CoordExportMode.ACTIVE,
) -> None:
    """Per-observation comparison when pano and intensity methods both succeeded."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    headers = [
        "family",
        "tag_id",
        "scan",
        "detect_source",
        "refine_method",
        "x",
        "y",
        "z",
        "refine_method_alt",
        "x_alt",
        "y_alt",
        "z_alt",
        "delta_mm",
    ]

    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, delimiter=";")
        writer.writerow(headers)
        for obs in observations:
            if obs.center_alt_e57 is None:
                continue
            primary = obs.center_project if obs.center_project is not None else obs.center_e57
            alt = obs.center_alt_e57
            delta_mm = float(np.linalg.norm(obs.center_e57 - obs.center_alt_e57) * 1000)
            writer.writerow(
                [
                    obs.family,
                    obs.tag_id,
                    obs.scan_name,
                    obs.detect_source,
                    obs.refine_method,
                    f"{primary[0]:.6f}",
                    f"{primary[1]:.6f}",
                    f"{primary[2]:.6f}",
                    obs.refine_method_alt or "",
                    f"{alt[0]:.6f}",
                    f"{alt[1]:.6f}",
                    f"{alt[2]:.6f}",
                    f"{delta_mm:.2f}",
                ]
            )
