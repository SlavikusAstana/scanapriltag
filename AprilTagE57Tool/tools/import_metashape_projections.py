"""
Спроецировать маркеры с 3D Reference на все камеры chunk (все ракурсы).

Использование (после Reference -> Import apriltag_metashape_markers.csv):
  Tools -> Run Script... -> этот файл

Metashape сам ставит маркер на каждый вид, где точка видна из 3D —
как при «старом» импорте только координат.
"""

from __future__ import annotations

import Metashape

# Сбросить старые 2D-проекции перед пересчётом из 3D
CLEAR_PROJECTIONS_FIRST = True

# Не ставить проекцию, если пиксель далеко за кадром (с запасом)
MARGIN_PX = 50


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


def _marker_point(marker: Metashape.Marker) -> Metashape.Vector | None:
    ref = marker.reference
    if ref is not None and ref.enabled:
        return ref.location
    return marker.position


def _in_image(cam: Metashape.Camera, x: float, y: float) -> bool:
    w = int(cam.width or 0)
    h = int(cam.height or 0)
    if w <= 0 or h <= 0:
        return True
    m = MARGIN_PX
    return -m <= x <= w + m and -m <= y <= h + m


def reproject_markers_all_views(chunk: Metashape.Chunk) -> tuple[int, int, int]:
    """
    Returns (markers_processed, projections_set, cameras_total).
    """
    cams = _iter_cameras(chunk)
    if not cams:
        print("Нет камер в chunk — нечего проецировать.")
        return 0, 0, 0

    markers_done = 0
    projections_set = 0

    for mk in chunk.markers:
        pt = _marker_point(mk)
        if pt is None:
            continue

        if CLEAR_PROJECTIONS_FIRST:
            for cam in list(mk.projections.keys()):
                del mk.projections[cam]

        markers_done += 1
        for cam in cams:
            try:
                if not cam.transform:
                    continue
                uv = cam.project(pt)
            except Exception:
                continue
            if uv is None:
                continue
            x, y = float(uv.x), float(uv.y)
            if not _in_image(cam, x, y):
                continue
            mk.projections[cam] = Metashape.Marker.Projection(
                Metashape.Vector([x, y]), True
            )
            projections_set += 1

    return markers_done, projections_set, len(cams)


def main() -> None:
    chunk = Metashape.app.document.chunk
    if chunk is None:
        print("Нет активного chunk")
        return

    n_markers = len(chunk.markers)
    with_ref = sum(
        1
        for m in chunk.markers
        if m.reference is not None and m.reference.enabled
    )
    print(f"Маркеров в chunk: {n_markers}, с включённым Reference: {with_ref}")

    if with_ref == 0:
        print(
            "Сначала импортируйте apriltag_metashape_markers.csv через "
            "Reference -> Import и включите Reference у маркеров."
        )
        return

    done, proj, ncams = reproject_markers_all_views(chunk)
    print(f"Камер (все ракурсы): {ncams}")
    print(f"Маркеров обработано: {done}")
    print(f"Проекций установлено: {proj}")


if __name__ == "__main__":
    main()
