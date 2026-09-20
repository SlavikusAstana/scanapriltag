"""
validate.py — сравнение apriltag_centers.csv с эталонами aprlth/

Формат aprlth: файл {tag_id}.txt, содержимое — строка "x,y,z" (активная СК).
Используется первая непустая строка.

Использование:
  python validate.py --refs aprlth/ --result apriltag_centers.csv [--threshold 10]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np


def load_refs(refs_dir: Path) -> dict[str, list[np.ndarray]]:
    refs: dict[str, list[np.ndarray]] = {}
    for f in sorted(refs_dir.glob("*.txt")):
        tag_id = f.stem
        points: list[np.ndarray] = []
        for line in f.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            parts = line.replace(" ", "").split(",")
            if len(parts) != 3:
                print(f"WARN: {f.name} — неверный формат: {line!r}")
                continue
            points.append(np.array([float(p) for p in parts]))
        if points:
            refs[tag_id] = points
            if len(points) > 1:
                print(f"INFO: {f.name} содержит {len(points)} эталонов — OK если любой в пределах порога")
    return refs


def load_results(csv_path: Path) -> dict[str, np.ndarray]:
    results: dict[str, np.ndarray] = {}
    lines = csv_path.read_text(encoding="utf-8").splitlines()
    if len(lines) < 2:
        return results
    for line in lines[1:]:
        if not line.strip():
            continue
        parts = line.split(";")
        if len(parts) < 5:
            continue
        tag_id = parts[1].strip()
        try:
            xyz = np.array([float(parts[2]), float(parts[3]), float(parts[4])])
        except (ValueError, IndexError):
            continue
        results[tag_id] = xyz
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate AprilTag CSV vs aprlth references")
    parser.add_argument("--refs", default="aprlth", type=Path)
    parser.add_argument("--result", default="apriltag_centers.csv", type=Path)
    parser.add_argument("--threshold", default=10.0, type=float, help="мм")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    if not args.refs.is_dir():
        print(f"ERROR: refs dir not found: {args.refs}", file=sys.stderr)
        sys.exit(2)
    if not args.result.is_file():
        print(f"ERROR: result csv not found: {args.result}", file=sys.stderr)
        sys.exit(2)

    refs = load_refs(args.refs)
    results = load_results(args.result)

    rows = []
    for tag_id, ref_list in sorted(refs.items(), key=lambda x: int(x[0]) if x[0].isdigit() else x[0]):
        if tag_id not in results:
            rows.append({"tag_id": tag_id, "error_mm": None, "status": "MISSING", "ref_index": None})
            continue
        errors = [float(np.linalg.norm(results[tag_id] - ref) * 1000) for ref in ref_list]
        best_i = int(np.argmin(errors))
        err_mm = errors[best_i]
        status = "OK" if err_mm <= args.threshold else "FAIL"
        rows.append({
            "tag_id": tag_id,
            "error_mm": round(err_mm, 1),
            "status": status,
            "ref_index": best_i + 1 if len(ref_list) > 1 else None,
        })

    if args.json:
        print(json.dumps(rows, indent=2, ensure_ascii=False))
    else:
        print(f"\n{'Tag':>6}  {'Error (mm)':>10}  {'Ref#':>4}  Status")
        print("-" * 38)
        for r in rows:
            err = f"{r['error_mm']:.1f}" if r["error_mm"] is not None else "---"
            ref_n = str(r["ref_index"]) if r["ref_index"] else "-"
            print(f"{r['tag_id']:>6}  {err:>10}  {ref_n:>4}  {r['status']}")

        ok = sum(1 for r in rows if r["status"] == "OK")
        fail = sum(1 for r in rows if r["status"] == "FAIL")
        missing = sum(1 for r in rows if r["status"] == "MISSING")
        print(f"\nИтого: {ok} OK / {fail} FAIL / {missing} MISSING (порог {args.threshold} мм)")

    sys.exit(0 if rows and all(r["status"] == "OK" for r in rows) else 1)


if __name__ == "__main__":
    main()
