"""AprilTag detection on exported equirectangular panoramas."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

from .detector import TAG_FAMILIES, TagDetection2D, detector_params


@dataclass(frozen=True)
class PanoDetection(TagDetection2D):
    """Detection on a full equirectangular panorama (source='pano')."""
    pano_width: int
    pano_height: int


def find_pano_image(pano_dir: Path, scan_name: str) -> Path | None:
    """Locate color VIS panorama for a scan (Register360 export naming).

    Skips intensity exports (*_scan.png) — they are sparse and unsuitable for ArUco.
    """
    pano_dir = Path(pano_dir)
    if not pano_dir.is_dir():
        return None
    for ext in (".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp"):
        p = pano_dir / f"{scan_name}{ext}"
        if p.is_file() and "_scan" not in p.stem:
            return p
        p = pano_dir / f"{scan_name}_pano{ext}"
        if p.is_file():
            return p
    return None


def detect_in_panorama(
    image_path: Path,
    *,
    families: list[str] | None = None,
    detect_scale: int = 2,
    detect_scales: tuple[int, ...] | None = None,
    tile: int = 640,
    stride: int = 480,
) -> list[PanoDetection]:
    """
    Detect AprilTags on an equirectangular panorama.

    Uses tiled detection on a downscaled image for speed on large exports.
    When ``detect_scales`` is set, runs each scale and merges (keeps largest area).
    """
    scales = detect_scales if detect_scales else (detect_scale,)
    merged: dict[tuple[str, int], PanoDetection] = {}
    for scale in scales:
        for det in _detect_in_panorama_at_scale(
            image_path,
            families=families,
            detect_scale=scale,
            tile=tile,
            stride=stride,
        ):
            key = (det.family, det.tag_id)
            prev = merged.get(key)
            if prev is None or det.area_px > prev.area_px:
                merged[key] = det
    return list(merged.values())


def _detect_in_panorama_at_scale(
    image_path: Path,
    *,
    families: list[str] | None = None,
    detect_scale: int = 2,
    tile: int = 640,
    stride: int = 480,
) -> list[PanoDetection]:
    if families is None:
        families = ["tag36h11", "tag25h9", "tag16h5"]

    img = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
    if img is None:
        return []

    h, w = img.shape[:2]
    scale = max(1, int(detect_scale))
    if scale > 1:
        small = cv2.resize(img, (w // scale, h // scale), interpolation=cv2.INTER_AREA)
    else:
        small = img

    sh, sw = small.shape[:2]
    gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
    params = detector_params()
    found: list[PanoDetection] = []
    seen: set[tuple[str, int]] = set()

    tile_s = max(256, tile // scale)
    stride_s = max(192, stride // scale)

    for family in families:
        dic_id = TAG_FAMILIES.get(family)
        if dic_id is None:
            continue
        dictionary = cv2.aruco.getPredefinedDictionary(dic_id)
        detector = cv2.aruco.ArucoDetector(dictionary, params)

        for y in range(0, max(1, sh - tile_s), stride_s):
            for x in range(0, max(1, sw - tile_s), stride_s):
                patch = gray[y : y + tile_s, x : x + tile_s]
                if patch.size == 0 or patch.max() < 25:
                    continue
                corners, ids, _ = detector.detectMarkers(patch)
                if ids is None:
                    continue
                for c, tid in zip(corners, ids):
                    key = (family, int(tid[0]))
                    if key in seen:
                        continue
                    seen.add(key)
                    pts = c[0].copy()
                    pts[:, 0] = (pts[:, 0] + x) * scale
                    pts[:, 1] = (pts[:, 1] + y) * scale
                    area = float(cv2.contourArea(pts.astype(np.float32)))
                    found.append(
                        PanoDetection(
                            family=family,
                            tag_id=int(tid[0]),
                            corners_full_res=pts.astype(np.float64),
                            area_px=area,
                            image_index=-1,
                            pano_width=w,
                            pano_height=h,
                        )
                    )

    return found
