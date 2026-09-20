"""
Импорт 2D из apriltag_metashape_projections.csv (только если имена камер = JPG).

Для laser scan + cubemap (GUID) используйте import_metashape_projections.py
(3D Reference на все ракурсы).
"""

from __future__ import annotations

import os
import re

import Metashape

MATCH_BY_BASENAME = True
PRINT_DEBUG = True


def _norm(s: str) -> str:
    return s.strip().replace("\\", "/").lower()


def _image_keys(image_field: str) -> set[str]:
    s = image_field.strip().replace("\\", "/")
    base = os.path.basename(s) if MATCH_BY_BASENAME else s
    stem, _ = os.path.splitext(base)
    keys = {_norm(base), _norm(stem)}
    return {k for k in keys if k}


def _camera_keys(camera: Metashape.Camera) -> set[str]:
    keys: set[str] = set()
    try:
        path = camera.photo.path or ""
    except Exception:
        path = ""
    if path:
        keys.add(_norm(path))
        keys.add(_norm(os.path.basename(path)))
        stem, _ = os.path.splitext(os.path.basename(path))
        if stem:
            keys.add(_norm(stem))
    if camera.label:
        keys.add(_norm(camera.label))
        keys.add(_norm(os.path.basename(camera.label)))
    return {k for k in keys if k}


def _iter_cameras(chunk: Metashape.Chunk) -> list[Metashape.Camera]:
    cams: list[Metashape.Camera] = []
    seen: set[int] = set()

    def add(cam: Metashape.Camera) -> None:
        k = int(cam.key)
        if k not in seen:
            seen.add(k)
            cams.append(cam)

    for cam in chunk.cameras:
        add(cam)
    for frame in getattr(chunk, "frames", []) or []:
        for cam in frame.cameras:
            add(cam)
    return cams


def import_projections_csv(path: str) -> tuple[int, int, int]:
    chunk = Metashape.app.document.chunk
    if chunk is None:
        raise RuntimeError("Нет активного chunk")

    cams = _iter_cameras(chunk)
    created = updated = skipped = 0
    label_to_marker = {(m.label or "").lower(): m for m in chunk.markers}

    with open(path, "rt", encoding="utf-8") as f:
        f.readline()
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = [p.strip() for p in line.split(",")]
            if len(parts) < 4:
                skipped += 1
                continue

            img_keys = _image_keys(parts[0])
            marker_name = parts[1]
            x, y = float(parts[2]), float(parts[3])

            camera = None
            for cam in cams:
                if img_keys & _camera_keys(cam):
                    camera = cam
                    break
            if camera is None:
                skipped += 1
                continue

            mk = label_to_marker.get(marker_name.lower())
            if mk is None:
                mk = chunk.addMarker()
                mk.label = marker_name
                label_to_marker[marker_name.lower()] = mk
                created += 1

            mk.projections[camera] = Metashape.Marker.Projection(
                Metashape.Vector([x, y]), True
            )
            updated += 1

    return created, updated, skipped


def main() -> None:
    path = Metashape.app.getOpenFileName("apriltag_metashape_projections.csv")
    if not path:
        return
    c, u, s = import_projections_csv(path)
    print(f"Markers created: {c}")
    print(f"Projections set: {u}")
    print(f"Skipped (no camera match): {s}")


if __name__ == "__main__":
    main()
