"""Disk cache for E57 point clouds (XYZ + row/col + intensity)."""

from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np

CACHE_DIR = Path.home() / ".apriltag_e57_cache"

_CACHE_KEYS = (
    "cartesianX",
    "cartesianY",
    "cartesianZ",
    "rowIndex",
    "columnIndex",
    "intensity",
)


def _cache_path(e57_path: Path) -> Path:
    h = hashlib.md5(str(e57_path.resolve()).encode()).hexdigest()[:8]
    return CACHE_DIR / f"{e57_path.stem}_{h}.npz"


def get_cached_scan_data(e57_path: Path) -> dict | None:
    cache_path = _cache_path(e57_path)
    if not cache_path.is_file():
        return None
    if cache_path.stat().st_mtime < e57_path.stat().st_mtime:
        cache_path.unlink(missing_ok=True)
        return None
    loaded = np.load(cache_path, allow_pickle=False)
    return {k: loaded[k] for k in loaded.files}


def save_scan_cache(e57_path: Path, scan_data: dict) -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        k: scan_data[k]
        for k in _CACHE_KEYS
        if k in scan_data and scan_data[k] is not None
    }
    if not payload:
        return
    np.savez_compressed(_cache_path(e57_path), **payload)
