"""Register360 project.db: setup poses and active coordinate system (from krpanomodule)."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

import numpy as np


class CoordExportMode(str, Enum):
    """Which coordinate system to write to CSV."""

    ACTIVE = "active"  # E57 / active CS (default, matches Register360 viewer picks)
    GLOBAL = "global"  # raw SetupRef global project coordinates


@dataclass(frozen=True)
class SetupRecord:
    label: str
    sitemap_id: int
    global_position: np.ndarray  # SetupRef mPositionX/Y/Z
    global_rotation_wxyz: tuple[float, float, float, float]


# --- Ported from D:/code/krpanomodule/scriptemall_py.py (export_stations logic) ---


def _quaternion_multiply(q1, q2):
    x1, y1, z1, w1 = q1
    x2, y2, z2, w2 = q2
    w = w1 * w2 - x1 * x2 - y1 * y2 - z1 * z2
    x = w1 * x2 + x1 * w2 + y1 * z2 - z1 * y2
    y = w1 * y2 - x1 * z2 + y1 * w2 + z1 * x2
    z = w1 * z2 + x1 * y2 - y1 * x2 + z1 * w2
    return (x, y, z, w)


def _quaternion_conjugate(quaternion):
    x, y, z, w = quaternion
    return (-x, -y, -z, w)


def _apply_quaternion_rotation(quaternion, vector):
    qx, qy, qz, qw = quaternion
    vx, vy, vz = vector
    m00 = 1 - 2 * (qy * qy + qz * qz)
    m01 = 2 * (qx * qy - qz * qw)
    m02 = 2 * (qx * qz + qy * qw)
    m10 = 2 * (qx * qy + qz * qw)
    m11 = 1 - 2 * (qx * qx + qz * qz)
    m12 = 2 * (qy * qz - qx * qw)
    m20 = 2 * (qx * qz - qy * qw)
    m21 = 2 * (qy * qz + qx * qw)
    m22 = 1 - 2 * (qx * qx + qy * qy)
    rx = m00 * vx + m01 * vy + m02 * vz
    ry = m10 * vx + m11 * vy + m12 * vz
    rz = m20 * vx + m21 * vy + m22 * vz
    return (rx, ry, rz)


def get_coordinate_system_transform(cur, sitemap_id: int | None = None) -> dict | None:
    """Active CS transform params for a sitemap (krpanomodule-compatible)."""
    try:
        if sitemap_id is not None:
            result = cur.execute(
                "SELECT mpActiveCoordSystem FROM Hds_OdbSitemap WHERE mId = ?",
                (int(sitemap_id),),
            ).fetchone()
        else:
            result = cur.execute(
                "SELECT mpActiveCoordSystem FROM Hds_OdbSitemap ORDER BY mId LIMIT 1"
            ).fetchone()
        if not result or not result[0]:
            return None

        coord_system_id = result[0]
        result = cur.execute(
            "SELECT mpSetup FROM Hds_OdbControlCoordSystem WHERE mId = ?",
            (coord_system_id,),
        ).fetchone()
        if not result or not result[0]:
            return None
        setup_id = result[0]

        result = cur.execute(
            "SELECT mRotation0, mRotation1, mRotation2, mRotation3, "
            "mPosition0, mPosition1, mPosition2 "
            "FROM Hds_OdbSetup WHERE mId = ?",
            (setup_id,),
        ).fetchone()
        if not result:
            return None
        station_quat = (result[0], result[1], result[2], result[3])
        station_pos = (result[4], result[5], result[6])

        result = cur.execute(
            "SELECT mRotationX, mRotationY, mRotationZ, mRotationW, "
            "mPositionX, mPositionY, mPositionZ "
            "FROM Hds_OdbControlCoordSystem WHERE mId = ?",
            (coord_system_id,),
        ).fetchone()
        if not result:
            return None
        coord_system_quat = (result[0], result[1], result[2], result[3])
        coord_system_pos = (result[4], result[5], result[6])

        rotated_pos = _apply_quaternion_rotation(station_quat, coord_system_pos)
        psk_origin = (
            station_pos[0] + rotated_pos[0],
            station_pos[1] + rotated_pos[1],
            station_pos[2] + rotated_pos[2],
        )
        combined_quat = _quaternion_multiply(coord_system_quat, station_quat)
        inverse_quat = _quaternion_conjugate(combined_quat)

        return {
            "psk_origin": psk_origin,
            "inverse_quat": inverse_quat,
            "combined_quat": combined_quat,
        }
    except Exception:
        return None


def global_to_active_cs(x: float, y: float, z: float, transform: dict | None) -> tuple[float, float, float]:
    """SetupRef global -> active CS (same as krpanomodule transform_coordinates)."""
    if transform is None:
        return x, y, z
    psk_origin = transform["psk_origin"]
    vector_from_psk = (x - psk_origin[0], y - psk_origin[1], z - psk_origin[2])
    rotated = _apply_quaternion_rotation(transform["inverse_quat"], vector_from_psk)
    return rotated[0], rotated[1], rotated[2]


def active_cs_to_global(x: float, y: float, z: float, transform: dict | None) -> tuple[float, float, float]:
    """Active CS -> SetupRef global (inverse of transform_coordinates)."""
    if transform is None:
        return x, y, z
    psk_origin = transform["psk_origin"]
    rotated = _apply_quaternion_rotation(transform["combined_quat"], (x, y, z))
    return (
        rotated[0] + psk_origin[0],
        rotated[1] + psk_origin[1],
        rotated[2] + psk_origin[2],
    )


def find_project_db(folder: Path) -> Path | None:
    """Search E57 folder and sibling ``pano/`` (Register360 export layout)."""
    folder = Path(folder)
    for search in (folder, folder / "pano"):
        if not search.is_dir():
            continue
        direct = search / "project.db"
        if direct.is_file():
            return direct
        candidates = sorted(search.glob("project*.db"))
        if candidates:
            return candidates[0]
    return None


class ProjectDatabase:
    """Cached access to setup records and per-sitemap active CS transforms."""

    def __init__(self, db_path: Path) -> None:
        self.db_path = Path(db_path)
        self._setups: dict[str, SetupRecord] = {}
        self._cs_cache: dict[int, dict | None] = {}
        self._load()

    def _load(self) -> None:
        conn = sqlite3.connect(str(self.db_path))
        try:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT s.mLabel, r.mSitemapId,
                       r.mPositionX, r.mPositionY, r.mPositionZ,
                       r.mRotationW, r.mRotationX, r.mRotationY, r.mRotationZ
                FROM Hds_OdbSetupRef r
                JOIN Hds_OdbSetup s ON s.mId = r.mSetupId
                """
            )
            for label, sid, px, py, pz, rw, rx, ry, rz in cur.fetchall():
                self._setups[str(label)] = SetupRecord(
                    label=str(label),
                    sitemap_id=int(sid) if sid is not None else -1,
                    global_position=np.array([px, py, pz], dtype=np.float64),
                    global_rotation_wxyz=(rw, rx, ry, rz),
                )
            self._conn_cur = cur
            self._conn = conn
        except Exception:
            conn.close()
            raise

    def close(self) -> None:
        if hasattr(self, "_conn"):
            self._conn.close()
            del self._conn
            del self._conn_cur

    def __enter__(self) -> ProjectDatabase:
        return self

    def __exit__(self, *args) -> None:
        self.close()

    def get_setup(self, label: str) -> SetupRecord | None:
        return self._setups.get(label)

    def cs_transform(self, sitemap_id: int) -> dict | None:
        if sitemap_id not in self._cs_cache:
            self._cs_cache[sitemap_id] = get_coordinate_system_transform(
                self._conn_cur, sitemap_id=sitemap_id if sitemap_id >= 0 else None
            )
        return self._cs_cache[sitemap_id]

    def export_point(self, active_point: np.ndarray, setup_label: str, mode: CoordExportMode) -> np.ndarray:
        """
        Convert E57/active-CS point to export coordinates.

        E57 export from Register360 is already in active CS (verified: SetupRef
        transformed via transform_coordinates matches E57 scan pose).
        """
        p = np.asarray(active_point, dtype=np.float64)
        if mode == CoordExportMode.ACTIVE:
            return p
        setup = self.get_setup(setup_label)
        if setup is None:
            return p
        tr = self.cs_transform(setup.sitemap_id)
        gx, gy, gz = active_cs_to_global(float(p[0]), float(p[1]), float(p[2]), tr)
        return np.array([gx, gy, gz], dtype=np.float64)

    @property
    def setup_count(self) -> int:
        return len(self._setups)


def load_project_database(db_path: Path) -> ProjectDatabase:
    return ProjectDatabase(db_path)
