"""Ray-guided LiDAR re-observation of known 3D tag positions."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .fusion import FusedTag, TagObservation, make_observation
from .geometry import TagCenter3D, center_from_lidar_ray


@dataclass(frozen=True)
class RayGuidedConfig:
    cone_deg: float = 0.25
    max_miss_mm: float = 80.0
    min_points: int = 8
    max_distance_m: float = 45.0
    min_distance_m: float = 0.5
    weight_multiplier: float = 0.65


def center_from_target_ray(
    target_e57: np.ndarray,
    xyz: np.ndarray,
    rows: np.ndarray,
    cols: np.ndarray,
    scanner_pos: np.ndarray,
    *,
    cone_deg: float = 0.25,
    patch_cells: int = 18,
) -> TagCenter3D | None:
    """
    3D center by casting a ray from scanner toward a known tag position.

    Uses LiDAR points in an angular cone around the ray (same logic as pano_ray).
    """
    rel = target_e57 - scanner_pos
    dist_target = float(np.linalg.norm(rel))
    if dist_target < 0.5 or dist_target > 45.0:
        return None

    ray = rel / dist_target
    origin = scanner_pos
    return center_from_lidar_ray(
        xyz,
        rows,
        cols,
        scanner_pos,
        origin,
        ray,
        cone_deg=cone_deg,
        patch_cells=patch_cells,
        expand_if_below=20,
        min_after_expand=8,
        min_patch=8,
        min_surface_points=3,
        depth_band_m=0.012,
        max_distance_m=None,
    )


def reobserve_tags_in_scan(
    fused_tags: list[FusedTag],
    *,
    scan_name: str,
    xyz: np.ndarray,
    rows: np.ndarray,
    cols: np.ndarray,
    scanner_pos: np.ndarray,
    already_seen: set[tuple[str, int]],
    export_fn,
    config: RayGuidedConfig | None = None,
) -> list[TagObservation]:
    """
    For tags not yet seen in this scan, try LiDAR ray cast to fused 3D center.
    """
    cfg = config or RayGuidedConfig()
    observations: list[TagObservation] = []

    for tag in fused_tags:
        key = (tag.family, tag.tag_id)
        if key in already_seen:
            continue

        target = tag.center_e57
        result = center_from_target_ray(
            target,
            xyz,
            rows,
            cols,
            scanner_pos,
            cone_deg=cfg.cone_deg,
        )
        if result is None:
            continue

        if result.distance < cfg.min_distance_m or result.distance > cfg.max_distance_m:
            continue

        miss_mm = float(np.linalg.norm(result.center - target) * 1000.0)
        if miss_mm > cfg.max_miss_mm:
            continue

        center_export = export_fn(result.center)
        obs = make_observation(
            tag.family,
            tag.tag_id,
            scan_name,
            result,
            area_px=0.0,
            center_project=center_export,
            detect_source="ray_guided",
            refine_method="lidar_ray",
            weight_multiplier=cfg.weight_multiplier,
        )
        observations.append(obs)

    return observations
