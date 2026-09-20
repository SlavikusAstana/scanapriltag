"""Export AprilTag centers for Agisoft Metashape marker reference CSV."""

from __future__ import annotations

import csv
from pathlib import Path

from .fusion import FusedTag

MS_MARKER_HEADERS = [
    "label",
    "x",
    "y",
    "z",
    "accuracy_x",
    "accuracy_y",
    "accuracy_z",
]

MS_PROJECTIONS_HEADERS = [
    "image",
    "label",
    "x",
    "y",
]


def metashape_point_name(family: str, tag_id: int) -> str:
    safe = "".join(c if c.isalnum() or c == "_" else "_" for c in family)
    return f"{safe}_{tag_id}"


def _accuracy_m(sigma_m: float, *, floor_m: float = 0.005) -> float:
    if sigma_m > 0:
        return max(sigma_m, floor_m)
    return floor_m


def export_metashape_markers_csv(
    tags: list[FusedTag],
    path: Path,
    *,
    delimiter: str = ",",
) -> None:
    """
    Export marker reference for Metashape import.

    Metashape Import Reference mapping:
    - label, x, y, z, accuracy_x, accuracy_y, accuracy_z
    - Python columns string: nxyzXYZ
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, delimiter=delimiter)
        writer.writerow(MS_MARKER_HEADERS)
        for tag in sorted(tags, key=lambda t: (t.family, t.tag_id)):
            center = tag.center_project if tag.center_project is not None else tag.center_e57
            acc = _accuracy_m(tag.sigma_m)
            writer.writerow(
                [
                    metashape_point_name(tag.family, tag.tag_id),
                    f"{center[0]:.6f}",
                    f"{center[1]:.6f}",
                    f"{center[2]:.6f}",
                    f"{acc:.6f}",
                    f"{acc:.6f}",
                    f"{acc:.6f}",
                ]
            )


def export_metashape_projections_csv(
    rows: list[tuple[str, str, float, float]],
    path: Path,
    *,
    delimiter: str = ",",
    use_basename: bool = True,
) -> None:
    """
    Export marker projections for Metashape (script or manual entry).

    Each row: (image_path, marker_label, x_px, y_px).
    use_basename=True matches chunk cameras by filename only (recommended for laser+pano).
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, delimiter=delimiter)
        writer.writerow(MS_PROJECTIONS_HEADERS)
        for image_path, label, x_px, y_px in rows:
            img = Path(image_path).name if use_basename else str(image_path)
            writer.writerow([img, label, f"{x_px:.4f}", f"{y_px:.4f}"])


def export_metashape_projections_from_pano(
    pano_rows: list[tuple[str, str, int, float, float]],
    path: Path,
    *,
    delimiter: str = ",",
    use_basename: bool = True,
) -> None:
    """pano_rows: (image_path, family, tag_id, x_px, y_px)."""
    rows = [
        (
            image_path,
            metashape_point_name(family, tag_id),
            x_px,
            y_px,
        )
        for image_path, family, tag_id, x_px, y_px in pano_rows
    ]
    export_metashape_projections_csv(rows, path, delimiter=delimiter, use_basename=use_basename)
