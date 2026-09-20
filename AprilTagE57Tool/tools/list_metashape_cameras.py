"""Показать подписи камер и лазерных сканов в активном chunk (Tools -> Run Script)."""

import Metashape


def main() -> None:
    chunk = Metashape.app.document.chunk
    if chunk is None:
        print("Нет активного chunk")
        return

    cams = list(chunk.cameras)
    print(f"chunk.cameras: {len(cams)}")
    for i, cam in enumerate(cams):
        path = ""
        try:
            path = cam.photo.path or ""
        except Exception:
            pass
        print(f"  [{i}] label={cam.label!r} path={path!r}")

    frames = getattr(chunk, "frames", None) or []
    print(f"chunk.frames: {len(frames)}")
    for fi, frame in enumerate(frames[:5]):
        fc = list(frame.cameras)
        print(f"  frame[{fi}] cameras={len(fc)} label={getattr(frame, 'label', '')!r}")
        for cam in fc[:3]:
            print(f"    label={cam.label!r}")

    for attr in ("laser_scans", "point_clouds"):
        items = getattr(chunk, attr, None) or []
        if items:
            print(f"chunk.{attr}: {len(items)}")
            for i, pc in enumerate(items[:20]):
                print(f"  [{i}] label={getattr(pc, 'label', '')!r}")
            if len(items) > 20:
                print(f"  ... ещё {len(items) - 20}")


if __name__ == "__main__":
    main()
