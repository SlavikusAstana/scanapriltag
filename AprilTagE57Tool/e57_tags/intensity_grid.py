"""Intensity row/col grid: pano ray 3D, intensity refine, az calibration."""

from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np

from .detector import TAG_FAMILIES, detector_params
from .geometry import (
    TagCenter3D,
    _fit_plane_svd,
    center_from_lidar_ray,
    nearest_surface_points,
    plane_ray_intersect,
)

_plane_ray_intersect = plane_ray_intersect
_nearest_surface_points = nearest_surface_points


@dataclass(frozen=True)
class RowColBounds:
    row_min: int
    row_max: int
    col_min: int
    col_max: int


def rowcol_bounds_from_cloud(rows: np.ndarray, cols: np.ndarray) -> RowColBounds:
    return RowColBounds(
        row_min=int(rows.min()),
        row_max=int(rows.max()),
        col_min=int(cols.min()),
        col_max=int(cols.max()),
    )


def calibrate_az_offset(
    xyz: np.ndarray,
    rows: np.ndarray,
    cols: np.ndarray,
    scanner_pos: np.ndarray,
    rotation_matrix: np.ndarray,
    pano_w: int,
    bounds: RowColBounds,
) -> float:
    """
    Grid-search azimuth offset aligning pano equirectangular with LiDAR row/col.

    Uses random cloud sample: columnIndex → pano u vs local azimuth from XYZ.
    """
    rel = xyz - scanner_pos
    r = np.linalg.norm(rel, axis=1)
    mask = (r > 1.0) & (r < 25.0)
    if int(mask.sum()) < 50:
        return 0.0

    idx = np.where(mask)[0]
    step = max(1, len(idx) // 150)
    idx = idx[::step]

    local = (rotation_matrix.T @ rel[idx].T).T
    local_n = local / np.linalg.norm(local, axis=1, keepdims=True)
    true_az = np.arctan2(local_n[:, 0], local_n[:, 1])

    span_c = max(bounds.col_max - bounds.col_min, 1)
    u_from_col = (cols[idx].astype(np.float64) - bounds.col_min) / span_c * max(pano_w - 1, 1)

    best_offset = 0.0
    best_err = np.inf
    for offset in np.arange(-0.5, 0.5, 0.005):
        az_pano = 2.0 * np.pi * (u_from_col / max(pano_w - 1, 1)) - np.pi + offset
        diff = np.arctan2(np.sin(az_pano - true_az), np.cos(az_pano - true_az))
        err = float(np.mean(np.abs(diff)))
        if err < best_err:
            best_err = err
            best_offset = float(offset)

    return best_offset


def pano_uv_to_world_ray(
    u: float,
    v: float,
    pano_w: int,
    pano_h: int,
    scanner_pos: np.ndarray,
    rotation_matrix: np.ndarray,
    *,
    az_offset: float = 0.0,
) -> tuple[np.ndarray, np.ndarray]:
    """Unit view ray in world coordinates from equirectangular panorama pixel."""
    az = 2.0 * np.pi * (u / max(pano_w - 1, 1)) - np.pi + az_offset
    el = np.pi * (0.5 - v / max(pano_h - 1, 1))
    dx = np.cos(el) * np.sin(az)
    dy = np.cos(el) * np.cos(az)
    dz = np.sin(el)
    d_local = np.array([dx, dy, dz], dtype=np.float64)
    d_world = rotation_matrix @ d_local
    d_world /= max(np.linalg.norm(d_world), 1e-12)
    return scanner_pos, d_world


def center_from_pano_ray(
    xyz: np.ndarray,
    rows: np.ndarray,
    cols: np.ndarray,
    corners_uv: np.ndarray,
    pano_w: int,
    pano_h: int,
    scanner_pos: np.ndarray,
    rotation_matrix: np.ndarray,
    *,
    az_offset: float = 0.0,
    cone_deg: float = 0.35,
) -> TagCenter3D | None:
    """3D center: pano view ray → LiDAR cone → plane-ray intersection."""
    center_uv = corners_uv.mean(axis=0)
    origin, ray = pano_uv_to_world_ray(
        float(center_uv[0]),
        float(center_uv[1]),
        pano_w,
        pano_h,
        scanner_pos,
        rotation_matrix,
        az_offset=az_offset,
    )
    return center_from_lidar_ray(
        xyz,
        rows,
        cols,
        scanner_pos,
        origin,
        ray,
        cone_deg=cone_deg,
        patch_cells=18,
        expand_if_below=20,
        min_after_expand=10,
        min_patch=10,
        depth_band_m=0.012,
        max_distance_m=40.0,
    )


def refine_center_via_intensity_grid(
    *,
    family: str,
    tag_id: int,
    scan_data: dict,
    xyz: np.ndarray,
    scanner_pos: np.ndarray,
    pano_ray_result: TagCenter3D,
    families: list[str] | None = None,
    roi_cells: int = 40,
) -> TagCenter3D | None:
    """
    Re-detect AprilTag on intensity row/col grid around pano ray seed; plane-ray 3D.
    """
    if "intensity" not in scan_data or pano_ray_result.row_col_center is None:
        return None

    rows = scan_data["rowIndex"]
    cols = scan_data["columnIndex"]
    intensity = scan_data["intensity"]
    row_c, col_c = pano_ray_result.row_col_center

    mask = (
        (rows >= row_c - roi_cells)
        & (rows <= row_c + roi_cells)
        & (cols >= col_c - roi_cells)
        & (cols <= col_c + roi_cells)
    )
    if not np.any(mask):
        return None

    r_rows = rows[mask].astype(np.int32)
    r_cols = cols[mask].astype(np.int32)
    r_int = intensity[mask].astype(np.float64)
    r_xyz = xyz[mask]

    i_min, i_max = float(r_int.min()), float(r_int.max())
    if i_max - i_min < 1e-9:
        return None
    grid_vals = ((r_int - i_min) / (i_max - i_min) * 255.0).astype(np.uint8)

    r_off = int(r_rows.min())
    c_off = int(r_cols.min())
    h = int(r_rows.max()) - r_off + 1
    w = int(r_cols.max()) - c_off + 1
    img = np.zeros((h, w), dtype=np.uint8)
    ranges = np.linalg.norm(r_xyz - scanner_pos, axis=1)
    order = np.argsort(ranges)[::-1]
    ri = r_rows - r_off
    ci = r_cols - c_off
    for j in order:
        img[int(ri[j]), int(ci[j])] = grid_vals[j]

    if img.max() < 20:
        return None

    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(4, 4))
    img = clahe.apply(img)

    if families is None:
        families = [family]

    params = detector_params()
    origin = pano_ray_result.scanner_pos
    ray = pano_ray_result.view_ray

    for fam in families:
        dic_id = TAG_FAMILIES.get(fam)
        if dic_id is None:
            continue
        detector = cv2.aruco.ArucoDetector(
            cv2.aruco.getPredefinedDictionary(dic_id), params
        )
        corners, ids, _ = detector.detectMarkers(img)
        if ids is None:
            continue
        for c, tid in zip(corners, ids):
            if int(tid[0]) != tag_id or fam != family:
                continue
            pts = c[0].mean(axis=0)
            det_row = float(pts[1]) + r_off
            det_col = float(pts[0]) + c_off

            pt_mask = (
                (rows >= det_row - 3)
                & (rows <= det_row + 3)
                & (cols >= det_col - 3)
                & (cols <= det_col + 3)
            )
            if not np.any(pt_mask):
                continue
            points = _nearest_surface_points(xyz[pt_mask], scanner_pos, depth_band_m=0.012)
            if len(points) < 5:
                continue

            center = _plane_ray_intersect(points, origin, ray)
            _, normal, rms = _fit_plane_svd(points)
            view = ray.copy()
            if view @ normal > 0:
                normal = -normal

            return TagCenter3D(
                center=center,
                normal=normal,
                distance=float(np.linalg.norm(center - scanner_pos)),
                plane_rms=rms,
                point_count=len(points),
                view_ray=view,
                scanner_pos=scanner_pos,
                row_col_center=(det_row, det_col),
            )

    return None
