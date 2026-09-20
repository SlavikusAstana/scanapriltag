"""Export AprilTag centers for RealityScan import (official CSV layouts).

References:
- Ground control (3D): groundcontrol.xml, reader RealityScan.Import.CSVGroundControl
  https://rshelp.capturingreality.com/en-US/tools/defineimportformat.htm
- Control point measurements (2D in images): measurementsimport.xml,
  reader RealityScan.Import.CSVControlPointsMeasurements
"""

from __future__ import annotations

import csv
from pathlib import Path

from .fusion import FusedTag

# Built-in format description in RealityScan import dialog (groundcontrol.xml).
RS_GCP_FORMAT_DESC = (
    "Name, X (East), Y (North), Alt, X Accuracy, Y Accuracy, Alt Accuracy (character-separated)"
)
RS_GCP_HEADERS = [
    "Name",
    "X (East)",
    "Y (North)",
    "Alt",
    "X Accuracy",
    "Y Accuracy",
    "Alt Accuracy",
]

RS_CP_MEASUREMENTS_FORMAT_DESC = "Image, Point, X, Y (character-separated)"
RS_CP_MEASUREMENTS_HEADERS = ["Image", "Point", "X", "Y"]


def realityscan_family_short(family: str) -> str:
    """RealityScan / RealityCapture label prefix (e.g. tag36h11 -> 36h11)."""
    f = family.strip().lower()
    if f.startswith("tag"):
        f = f[3:]
    return f


def realityscan_gcp_point_name(family: str, tag_id: int) -> str:
    """
    GCP name as RealityScan names auto-detected AprilTags.

    Format: ``36h11:052`` — family short name + colon + tag id in lowercase hex
    (3 digits, OpenCV/apriltag dictionary index). Not ``tag36h11_82`` decimal.
    """
    short = realityscan_family_short(family)
    return f"{short}:{tag_id:03x}"


def _accuracy_m(sigma_m: float, *, floor_m: float = 0.005) -> float:
    """Per-axis accuracy in metres for RealityScan (use fusion scatter as prior)."""
    if sigma_m > 0:
        return max(sigma_m, floor_m)
    return floor_m


def export_realityscan_gcp_csv(
    tags: list[FusedTag],
    path: Path,
    *,
    delimiter: str = ",",
) -> None:
    """
  Export ground control points for WORKFLOW → Ground Control.

  Import in RealityScan:
  - File format: «Name, X (East), Y (North), Alt, X Accuracy, Y Accuracy, Alt Accuracy»
  - Values separator: comma (or semicolon if delimiter changed)
  - Ignore first line: yes
  - Coordinate system: same as project / Register360 active CS (local Euclidean)
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, delimiter=delimiter)
        writer.writerow(RS_GCP_HEADERS)
        for tag in sorted(tags, key=lambda t: (t.family, t.tag_id)):
            center = tag.center_project if tag.center_project is not None else tag.center_e57
            acc = _accuracy_m(tag.sigma_m)
            writer.writerow(
                [
                    realityscan_gcp_point_name(tag.family, tag.tag_id),
                    f"{center[0]:.6f}",
                    f"{center[1]:.6f}",
                    f"{center[2]:.6f}",
                    f"{acc:.6f}",
                    f"{acc:.6f}",
                    f"{acc:.6f}",
                ]
            )


def export_realityscan_cp_measurements_csv(
    rows: list[tuple[str, str, float, float]],
    path: Path,
    *,
    delimiter: str = ",",
) -> None:
    """
    Export 2D control point measurements for WORKFLOW → Import Metadata → Control Points.

    Each row: (image_path, point_name, x_px, y_px) — pixel coords from image top-left.

    rows: list of (full_image_path, point_name, x, y)
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, delimiter=delimiter)
        writer.writerow(RS_CP_MEASUREMENTS_HEADERS)
        for image_path, point_name, x_px, y_px in rows:
            writer.writerow(
                [
                    image_path,
                    point_name,
                    f"{x_px:.4f}",
                    f"{y_px:.4f}",
                ]
            )


def export_realityscan_cp_measurements_from_pano(
    pano_rows: list[tuple[str, str, int, float, float]],
    path: Path,
    *,
    fused_tags: list[FusedTag] | None = None,
    delimiter: str = ",",
) -> int:
    """
    Export pano detections as RS 2D measurements.

    pano_rows: (image_path, family, tag_id, x_px, y_px)
    fused_tags: if set, only export tags present in fusion result (matches GCP file).
    """
    allowed: set[tuple[str, int]] | None = None
    if fused_tags is not None:
        allowed = {(t.family, t.tag_id) for t in fused_tags}

    out_rows: list[tuple[str, str, float, float]] = []
    for image_path, family, tag_id, x_px, y_px in pano_rows:
        if allowed is not None and (family, tag_id) not in allowed:
            continue
        out_rows.append(
            (
                image_path,
                realityscan_gcp_point_name(family, tag_id),
                x_px,
                y_px,
            )
        )

    export_realityscan_cp_measurements_csv(out_rows, path, delimiter=delimiter)
    return len(out_rows)
