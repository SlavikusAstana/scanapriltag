"""Unit tests for fusion and export naming (no E57 / OpenCV required)."""

from __future__ import annotations

import numpy as np
import pytest

from e57_tags.fusion import FusionMode, TagObservation, fuse_observations
from e57_tags.metashape_export import metashape_point_name
from e57_tags.realityscan_export import realityscan_gcp_point_name


def _obs(
    tag_id: int,
    *,
    scan: str,
    center: tuple[float, float, float],
    weight: float,
    family: str = "tag36h11",
) -> TagObservation:
    return TagObservation(
        family=family,
        tag_id=tag_id,
        scan_name=scan,
        center_e57=np.array(center, dtype=np.float64),
        center_project=None,
        weight=weight,
        distance=5.0,
        plane_rms=0.001,
        normal=np.array([0.0, 0.0, 1.0]),
        area_px=100.0,
    )


def test_fuse_best_picks_highest_weight():
    obs = [
        _obs(10, scan="s1", center=(1.0, 0.0, 0.0), weight=1.0),
        _obs(10, scan="s2", center=(1.05, 0.0, 0.0), weight=5.0),
        _obs(10, scan="s3", center=(0.95, 0.0, 0.0), weight=2.0),
    ]
    fused = fuse_observations(obs, mode=FusionMode.BEST)
    assert len(fused) == 1
    assert fused[0].best_scan == "s2"
    np.testing.assert_allclose(fused[0].center_e57, [1.05, 0.0, 0.0])


def test_fuse_weighted_averages():
    obs = [
        _obs(1, scan="a", center=(0.0, 0.0, 0.0), weight=1.0),
        _obs(1, scan="b", center=(2.0, 0.0, 0.0), weight=1.0),
    ]
    fused = fuse_observations(obs, mode=FusionMode.WEIGHTED)
    np.testing.assert_allclose(fused[0].center_e57, [1.0, 0.0, 0.0])
    assert fused[0].best_scan is None


def test_fuse_sigma_clip_rejects_outlier():
    # Tight cluster + far outlier — threshold is max(2σ, 20 mm).
    obs = [
        _obs(2, scan="a", center=(0.0, 0.0, 0.0), weight=1.0),
        _obs(2, scan="b", center=(0.002, 0.0, 0.0), weight=1.0),
        _obs(2, scan="c", center=(0.0, 0.002, 0.0), weight=1.0),
        _obs(2, scan="d", center=(0.002, 0.002, 0.0), weight=1.0),
        _obs(2, scan="e", center=(5.0, 0.0, 0.0), weight=1.0),
    ]
    fused = fuse_observations(obs, mode=FusionMode.WEIGHTED)
    assert fused[0].rejected_count >= 1
    assert abs(fused[0].center_e57[0]) < 0.1


def test_export_names():
    assert metashape_point_name("tag36h11", 472) == "tag36h11_472"
    assert realityscan_gcp_point_name("tag36h11", 472) == "36h11:1d8"
    assert realityscan_gcp_point_name("tag25h9", 82) == "25h9:052"
