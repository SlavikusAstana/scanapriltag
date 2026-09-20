"""3D tag center result and fusion weights (pano-ray + LiDAR row/col)."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class TagCenter3D:
    center: np.ndarray
    normal: np.ndarray
    distance: float
    plane_rms: float
    point_count: int
    view_ray: np.ndarray
    scanner_pos: np.ndarray
    row_col_center: tuple[float, float] | None = None


def plane_ray_intersect(
    points_xyz: np.ndarray,
    ray_origin: np.ndarray,
    ray_dir: np.ndarray,
) -> np.ndarray:
    """Fit plane (PCA/SVD), return ray-plane intersection."""
    if len(points_xyz) < 6:
        return points_xyz.mean(axis=0)

    centroid = points_xyz.mean(axis=0)
    _, _, vt = np.linalg.svd(points_xyz - centroid, full_matrices=False)
    normal = vt[-1]
    normal /= max(np.linalg.norm(normal), 1e-12)

    denom = float(np.dot(normal, ray_dir))
    if abs(denom) < 1e-6:
        return centroid

    t = float(np.dot(normal, centroid - ray_origin) / denom)
    return ray_origin + t * ray_dir


def nearest_surface_points(
    points: np.ndarray,
    scanner: np.ndarray,
    *,
    depth_band_m: float = 0.015,
) -> np.ndarray:
    if len(points) < 5:
        return points
    depths = np.linalg.norm(points - scanner, axis=1)
    d0 = float(np.min(depths))
    surf = points[depths <= d0 + depth_band_m]
    return surf if len(surf) >= 3 else points


def center_from_lidar_ray(
    xyz: np.ndarray,
    rows: np.ndarray,
    cols: np.ndarray,
    scanner_pos: np.ndarray,
    origin: np.ndarray,
    ray: np.ndarray,
    *,
    cone_deg: float,
    patch_cells: int = 18,
    expand_if_below: int = 20,
    min_after_expand: int = 10,
    min_patch: int = 10,
    min_surface_points: int = 0,
    depth_band_m: float = 0.012,
    max_distance_m: float | None = 40.0,
) -> TagCenter3D | None:
    """3D center: world ray → LiDAR angular cone → row/col patch → plane-ray."""
    rel = xyz - scanner_pos
    dist = np.linalg.norm(rel, axis=1)
    valid = dist > 0.4
    if not np.any(valid):
        return None

    rel_n = rel[valid] / dist[valid][:, None]
    cos_a = rel_n @ ray
    angle = np.arccos(np.clip(cos_a, -1.0, 1.0))
    cone = np.radians(cone_deg)
    idx_valid = np.where(valid)[0]
    in_cone = idx_valid[angle <= cone]
    if len(in_cone) < expand_if_below:
        in_cone = idx_valid[angle <= cone * 2.5]
    if len(in_cone) < min_after_expand:
        return None

    sub_rows = rows[in_cone]
    sub_cols = cols[in_cone]
    seed_row = float(np.median(sub_rows))
    seed_col = float(np.median(sub_cols))
    dr = np.abs(sub_rows.astype(np.float64) - seed_row)
    dc = np.abs(sub_cols.astype(np.float64) - seed_col)
    patch = in_cone[(dr <= patch_cells) & (dc <= patch_cells)]
    if len(patch) < min_patch:
        patch = in_cone

    points = nearest_surface_points(xyz[patch], scanner_pos, depth_band_m=depth_band_m)
    if min_surface_points and len(points) < min_surface_points:
        return None

    center = plane_ray_intersect(points, origin, ray)
    _, normal, rms = _fit_plane_svd(points)
    view = ray.copy()
    if view @ normal > 0:
        normal = -normal

    distance = float(np.linalg.norm(center - scanner_pos))
    if max_distance_m is not None and distance > max_distance_m:
        return None

    return TagCenter3D(
        center=center,
        normal=normal,
        distance=distance,
        plane_rms=rms,
        point_count=len(points),
        view_ray=view,
        scanner_pos=scanner_pos,
        row_col_center=(seed_row, seed_col),
    )


def _fit_plane_svd(points: np.ndarray) -> tuple[np.ndarray, np.ndarray, float]:
    centroid = points.mean(axis=0)
    _, _, vt = np.linalg.svd(points - centroid, full_matrices=False)
    normal = vt[2]
    normal /= np.linalg.norm(normal)
    rms = float(np.sqrt(np.mean(np.abs((points - centroid) @ normal) ** 2)))
    return centroid, normal, rms


def observation_weight(
    result: TagCenter3D,
    *,
    tag_area_px: float,
    distance_ref: float = 8.0,
) -> float:
    dist = max(result.distance, 0.5)
    w_dist = (distance_ref / dist) ** 2
    incidence = abs(float(-result.view_ray @ result.normal))
    w_angle = incidence**2
    w_size = min(4.0, max(0.25, np.sqrt(max(tag_area_px, 16.0)) / 20.0))
    w_quality = 1.0 / max(result.plane_rms, 0.002)
    return w_dist * w_angle * w_size * min(w_quality, 50.0)
