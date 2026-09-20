"""AprilTag family IDs and shared ArUco detector settings."""

from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np


TAG_FAMILIES: dict[str, int] = {
    "tag36h11": cv2.aruco.DICT_APRILTAG_36h11,
    "tag25h9": cv2.aruco.DICT_APRILTAG_25h9,
    "tag16h5": cv2.aruco.DICT_APRILTAG_16h5,
    "tag36h10": cv2.aruco.DICT_APRILTAG_36h10,
}


@dataclass(frozen=True)
class TagDetection2D:
    family: str
    tag_id: int
    corners_full_res: np.ndarray  # (4, 2) float
    area_px: float
    image_index: int


def detector_params() -> cv2.aruco.DetectorParameters:
    params = cv2.aruco.DetectorParameters()
    params.adaptiveThreshWinSizeMin = 3
    params.adaptiveThreshWinSizeMax = 43
    params.adaptiveThreshWinSizeStep = 4
    params.minMarkerPerimeterRate = 0.004
    params.maxMarkerPerimeterRate = 4.0
    params.cornerRefinementMethod = cv2.aruco.CORNER_REFINE_SUBPIX
    return params
