"""Собрать apriltag_realityscan_measurements.csv из metashape_projections + centers (без полного pipeline)."""

from __future__ import annotations

import csv
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from e57_tags.fusion import FusedTag
from e57_tags.realityscan_export import export_realityscan_cp_measurements_from_pano

_LABEL_RE = re.compile(r"^(tag36h11)_(\d+)$", re.I)


def _load_fused(centers_path: Path) -> list[FusedTag]:
    import numpy as np

    tags: list[FusedTag] = []
    with centers_path.open("r", encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f, delimiter=";"):
            tags.append(
                FusedTag(
                    family=row["family"],
                    tag_id=int(row["tag_id"]),
                    center_e57=__import__("numpy").array(
                        [float(row["x"]), float(row["y"]), float(row["z"])]
                    ),
                    center_project=None,
                    sigma_m=float(row["sigma_m"]),
                )
            )
    return tags


def _load_pano_rows(ms_proj_path: Path) -> list[tuple[str, str, int, float, float]]:
    rows: list[tuple[str, str, int, float, float]] = []
    with ms_proj_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            label = row["label"].strip()
            m = _LABEL_RE.match(label)
            if not m:
                continue
            family = m.group(1).lower()
            if not family.startswith("tag"):
                family = f"tag{family}"
            tag_id = int(m.group(2))
            image = row["image"].strip()
            rows.append((image, family, tag_id, float(row["x"]), float(row["y"])))
    return rows


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit("Usage: regenerate_realityscan_measurements.py <e57-or-output-folder>")
    folder = Path(sys.argv[1])
    centers = folder / "apriltag_centers.csv"
    ms_proj = folder / "apriltag_metashape_projections.csv"
    out = folder / "apriltag_realityscan_measurements.csv"

    if not ms_proj.is_file():
        raise SystemExit(f"Нет {ms_proj}")

    pano_rows = _load_pano_rows(ms_proj)
    fused = _load_fused(centers) if centers.is_file() else None

    n = export_realityscan_cp_measurements_from_pano(
        pano_rows,
        out,
        fused_tags=fused,
    )
    print(f"Записано {n} строк -> {out}")


if __name__ == "__main__":
    main()
