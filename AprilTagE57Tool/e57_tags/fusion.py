"""Fuse multiple 3D observations of the same AprilTag."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

import numpy as np

from .geometry import TagCenter3D, observation_weight


class FusionMode(str, Enum):
    """How to combine multiple scan observations of the same tag."""

    WEIGHTED = "weighted"  # sigma-clip + weighted average
    BEST = "best"  # default: position from the observation with max weight


@dataclass
class TagObservation:
    family: str
    tag_id: int
    scan_name: str
    center_e57: np.ndarray
    center_project: np.ndarray | None
    weight: float
    distance: float
    plane_rms: float
    normal: np.ndarray
    area_px: float
    detect_source: str = "pano"
    refine_method: str = "pano_ray"
    center_alt_e57: np.ndarray | None = None
    refine_method_alt: str | None = None


@dataclass
class FusedTag:
    family: str
    tag_id: int
    center_e57: np.ndarray
    center_project: np.ndarray | None
    sigma_m: float
    observations: list[TagObservation] = field(default_factory=list)
    weight_sum: float = 0.0
    rejected_count: int = 0
    best_scan: str | None = None  # scan used for center in BEST mode (or sole observation)

    @property
    def observation_count(self) -> int:
        return len(self.observations)


def _sigma_clip_mask(
    centers: np.ndarray,
    weights: np.ndarray,
    *,
    iterations: int = 2,
) -> np.ndarray:
    keep = np.ones(len(centers), dtype=bool)
    if len(centers) <= 1:
        return keep

    for _ in range(iterations):
        centroid = np.average(centers[keep], axis=0, weights=weights[keep])
        dists_mm = np.linalg.norm(centers - centroid, axis=1) * 1000.0
        sigma = max(float(dists_mm[keep].std()), 5.0)
        threshold = max(2.0 * sigma, 20.0)
        keep = dists_mm < threshold
        if keep.sum() < 1:
            return np.ones(len(centers), dtype=bool)

    return keep


def fuse_observations(
    observations: list[TagObservation],
    *,
    mode: FusionMode = FusionMode.WEIGHTED,
) -> list[FusedTag]:
    """Fuse observations per (family, tag_id).

    WEIGHTED: sigma-clip outliers, then weighted average of centers.
    BEST: sigma-clip, then center = observation with maximum weight (best view).
    """
    groups: dict[tuple[str, int], list[TagObservation]] = {}
    for obs in observations:
        groups.setdefault((obs.family, obs.tag_id), []).append(obs)

    fused: list[FusedTag] = []
    for (family, tag_id), items in sorted(groups.items()):
        weights = np.array([o.weight for o in items], dtype=np.float64)
        if weights.sum() <= 0:
            weights = np.ones(len(items))

        centers_e57 = np.array([o.center_e57 for o in items])
        keep = _sigma_clip_mask(centers_e57, weights)
        rejected = int((~keep).sum())

        w_kept = weights[keep]
        c_kept = centers_e57[keep]
        wsum = float(w_kept.sum())
        kept_items = [o for o, k in zip(items, keep) if k]

        if mode == FusionMode.BEST:
            best_i = int(np.argmax(w_kept))
            center_e57 = c_kept[best_i].copy()
            best_obs = kept_items[best_i]
            wsum = float(w_kept[best_i])
            if len(c_kept) > 1:
                others = np.delete(c_kept, best_i, axis=0)
                sigma = float(np.linalg.norm(others - center_e57, axis=1).max())
            else:
                sigma = 0.0
            best_scan = best_obs.scan_name
        else:
            center_e57 = np.average(c_kept, axis=0, weights=w_kept)
            diffs = np.linalg.norm(c_kept - center_e57, axis=1)
            sigma = float(np.sqrt(np.average(diffs**2, weights=w_kept)))
            best_scan = None

        project_items = [o for o in kept_items if o.center_project is not None]
        center_project = None
        if mode == FusionMode.BEST:
            if best_obs.center_project is not None:
                center_project = best_obs.center_project.copy()
        elif project_items:
            pw = np.array([o.weight for o in project_items], dtype=np.float64)
            cp = np.array([o.center_project for o in project_items])
            center_project = np.average(cp, axis=0, weights=pw)

        fused.append(
            FusedTag(
                family=family,
                tag_id=tag_id,
                center_e57=center_e57,
                center_project=center_project,
                sigma_m=sigma,
                observations=kept_items,
                weight_sum=wsum,
                rejected_count=rejected,
                best_scan=best_scan,
            )
        )

    return fused


def make_observation(
    family: str,
    tag_id: int,
    scan_name: str,
    result: TagCenter3D,
    area_px: float,
    center_project: np.ndarray | None = None,
    *,
    detect_source: str = "pano",
    refine_method: str = "vis_rowcol",
    center_alt_e57: np.ndarray | None = None,
    refine_method_alt: str | None = None,
    center_alt_project: np.ndarray | None = None,
    weight_multiplier: float = 1.0,
) -> TagObservation:
    w = observation_weight(result, tag_area_px=area_px) * weight_multiplier
    return TagObservation(
        family=family,
        tag_id=tag_id,
        scan_name=scan_name,
        center_e57=result.center.copy(),
        center_project=center_project.copy() if center_project is not None else None,
        weight=w,
        distance=result.distance,
        plane_rms=result.plane_rms,
        normal=result.normal.copy(),
        area_px=area_px,
        detect_source=detect_source,
        refine_method=refine_method,
        center_alt_e57=center_alt_e57.copy() if center_alt_e57 is not None else None,
        refine_method_alt=refine_method_alt,
    )
