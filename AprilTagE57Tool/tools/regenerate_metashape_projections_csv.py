"""Пересобрать apriltag_metashape_projections.csv только с именами файлов (без пути)."""

from __future__ import annotations

import csv
import sys
from pathlib import Path


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit("Usage: regenerate_metashape_projections_csv.py <projections.csv>")
    src = Path(sys.argv[1])
    dst = src.with_name("apriltag_metashape_projections_basename.csv")

    rows_out: list[list[str]] = []
    with src.open("r", encoding="utf-8", newline="") as f:
        reader = csv.reader(f)
        header = next(reader, None)
        if not header:
            raise SystemExit("Пустой CSV")
        rows_out.append(header)
        for row in reader:
            if len(row) < 4:
                continue
            row[0] = Path(row[0].strip()).name
            rows_out.append(row)

    with dst.open("w", encoding="utf-8", newline="") as f:
        csv.writer(f).writerows(rows_out)

    print(f"Записано {len(rows_out) - 1} строк -> {dst}")


if __name__ == "__main__":
    main()
