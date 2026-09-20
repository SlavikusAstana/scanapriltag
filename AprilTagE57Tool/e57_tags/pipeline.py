"""End-to-end processing pipeline for E57 AprilTag extraction."""

from __future__ import annotations

import multiprocessing
import traceback
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import numpy as np
from mye57 import E57
from pyquaternion import Quaternion

from .cloud_cache import get_cached_scan_data, save_scan_cache
from .detector import TAG_FAMILIES
from .exporter import export_compare_csv, export_csv
from .metashape_export import (
    export_metashape_markers_csv,
    export_metashape_projections_from_pano,
)
from .realityscan_export import (
    export_realityscan_cp_measurements_from_pano,
    export_realityscan_gcp_csv,
)
from .fusion import FusedTag, FusionMode, fuse_observations, make_observation
from .pipeline_options import (
    PANO_SCALE_FAST,
    PANO_SCALE_LABELS,
    PANO_SCALE_MAX,
    PANO_SCALE_FULL,
    pano_scales_from_preset,
)
from .intensity_grid import (
    center_from_pano_ray,
    refine_center_via_intensity_grid,
)
from .pano_detector import PanoDetection, detect_in_panorama, find_pano_image
from .ray_guided import RayGuidedConfig, reobserve_tags_in_scan
from .register360_db import CoordExportMode, ProjectDatabase, find_project_db, load_project_database


LogFn = Callable[[str], None]
ProgressFn = Callable[[float, str], None]
CancelFn = Callable[[], bool]


@dataclass
class PipelineConfig:
    e57_folder: Path
    db_path: Path | None = None
    output_csv: Path | None = None  # RealityScan GCP path; centers/metashape → same folder
    pano_folder: Path | None = None
    families: list[str] | None = None
    detect_scale: int = 2
    pano_detect_scales: tuple[int, ...] | None = (2,)
    coord_mode: CoordExportMode = CoordExportMode.ACTIVE
    prefer_pano: bool = True
    refine_intensity: bool = False
    max_workers: int = 4
    use_cache: bool = True
    ray_guided_pass: bool = True
    fusion_mode: FusionMode = FusionMode.BEST


@dataclass
class PipelineResult:
    fused_tags: list[FusedTag]
    output_csv: Path | None
    compare_csv: Path | None
    scans_processed: int
    detections_total: int


def _scan_name_from_e57(e57_path: Path, header) -> str:
    node = header.node
    if node.isDefined("name"):
        return str(node["name"].value())
    return e57_path.stem


def _load_scan_data(e57_path: Path, e57: E57, *, use_cache: bool) -> dict:
    if use_cache:
        cached = get_cached_scan_data(e57_path)
        if cached is not None:
            return cached

    data = e57.read_scan(
        0,
        intensity=True,
        row_column=True,
        ignore_missing_fields=True,
    )
    if use_cache:
        save_scan_cache(e57_path, data)
    return data


def _export_point(
    project_db: ProjectDatabase | None,
    point: np.ndarray,
    scan_name: str,
    coord_mode: CoordExportMode,
) -> np.ndarray:
    if project_db is None:
        return point.copy()
    return project_db.export_point(point, scan_name, coord_mode)


def _process_pano_detection(
    det: PanoDetection,
    *,
    data: dict,
    xyz: np.ndarray,
    rows: np.ndarray,
    cols: np.ndarray,
    scanner_pos: np.ndarray,
    scan_rotation: np.ndarray,
    az_offset: float,
    config: PipelineConfig,
    scan_name: str,
    project_db: ProjectDatabase | None,
    log: LogFn,
) -> list:
    result_pano = center_from_pano_ray(
        xyz,
        rows,
        cols,
        det.corners_full_res,
        det.pano_width,
        det.pano_height,
        scanner_pos,
        scan_rotation,
        az_offset=az_offset,
    )

    result_intensity = None
    if config.refine_intensity and result_pano is not None and "intensity" in data:
        result_intensity = refine_center_via_intensity_grid(
            family=det.family,
            tag_id=det.tag_id,
            scan_data=data,
            xyz=xyz,
            scanner_pos=scanner_pos,
            pano_ray_result=result_pano,
            families=config.families,
        )

    if result_pano is None and result_intensity is None:
        log(f"    id {det.tag_id} ({det.family}): нет 3D")
        return []

    if result_pano is not None and result_intensity is not None:
        delta_mm = float(np.linalg.norm(result_pano.center - result_intensity.center) * 1000)
        log(f"    id {det.tag_id}: pano_ray↔intensity {delta_mm:.1f} mm")

    if result_intensity is not None:
        result = result_intensity
        refine = "intensity_rowcol"
        alt = result_pano
        alt_method = "pano_ray" if alt is not None else None
        weight_mult = 1.5
    else:
        result = result_pano
        refine = "pano_ray"
        alt = None
        alt_method = None
        weight_mult = 1.0

    center_export = _export_point(project_db, result.center, scan_name, config.coord_mode)
    alt_export = None
    if alt is not None:
        alt_export = _export_point(project_db, alt.center, scan_name, config.coord_mode)

    obs = make_observation(
        det.family,
        det.tag_id,
        scan_name,
        result,
        det.area_px,
        center_project=center_export,
        detect_source="pano",
        refine_method=refine,
        center_alt_e57=alt.center if alt is not None else None,
        refine_method_alt=alt_method,
        weight_multiplier=weight_mult,
    )
    log(
        f"    {det.family} id={det.tag_id} [{refine}] "
        f"-> ({center_export[0]:.3f}, {center_export[1]:.3f}, {center_export[2]:.3f}) "
        f"d={result.distance:.2f}m w={obs.weight:.2f}"
    )
    return [obs]


def process_e57_file(
    e57_path: Path,
    *,
    config: PipelineConfig,
    project_db: ProjectDatabase | None,
    log: LogFn,
) -> tuple[list, list[tuple[str, str, int, float, float]]]:
    observations: list = []
    pano_projections: list[tuple[str, str, int, float, float]] = []
    scan_name = e57_path.stem

    if config.pano_folder is None or not config.prefer_pano:
        log(f"  [{scan_name}] пропуск: нужна папка pano/ с color JPG")
        return observations, pano_projections

    pano_path = find_pano_image(config.pano_folder, scan_name)
    if pano_path is None:
        log(f"  [{scan_name}] нет панорамы {scan_name}.jpg в {config.pano_folder}")
        return observations, pano_projections

    pano_dets = detect_in_panorama(
        pano_path,
        families=config.families,
        detect_scale=config.detect_scale,
        detect_scales=config.pano_detect_scales,
    )
    if not pano_dets:
        log(f"  [{scan_name}] панорама {pano_path.name}: теги не найдены")
        return observations, pano_projections

    log(f"  [{scan_name}] панорама {pano_path.name}: {len(pano_dets)} детекций, загрузка облака...")

    e57 = E57(str(e57_path))
    try:
        header = e57.get_header(0)
        scan_name = _scan_name_from_e57(e57_path, header)

        data = _load_scan_data(e57_path, e57, use_cache=config.use_cache)
        xyz = np.stack([data["cartesianX"], data["cartesianY"], data["cartesianZ"]], axis=1)
        rows = data["rowIndex"]
        cols = data["columnIndex"]
        scanner_pos = np.array(header.translation, dtype=np.float64)
        rot = header.rotation
        scan_rotation = Quaternion(rot[0], rot[1], rot[2], rot[3]).rotation_matrix

        az_offset = 0.0

        for det in pano_dets:
            if pano_path is not None:
                center_uv = det.corners_full_res.mean(axis=0)
                pano_projections.append(
                    (
                        str(pano_path.resolve()),
                        det.family,
                        det.tag_id,
                        float(center_uv[0]),
                        float(center_uv[1]),
                    )
                )
            observations.extend(
                _process_pano_detection(
                    det,
                    data=data,
                    xyz=xyz,
                    rows=rows,
                    cols=cols,
                    scanner_pos=scanner_pos,
                    scan_rotation=scan_rotation,
                    az_offset=az_offset,
                    config=config,
                    scan_name=scan_name,
                    project_db=project_db,
                    log=log,
                )
            )

    finally:
        e57.close()

    return observations, pano_projections


def _process_e57_worker(
    args: tuple,
) -> tuple[str, list, list[tuple[str, str, int, float, float]], list[str], str | None]:
    """Pickle-safe worker for ProcessPoolExecutor."""
    e57_path_str, config, db_path_str = args
    e57_path = Path(e57_path_str)
    db_path = Path(db_path_str) if db_path_str else None
    project_db = load_project_database(db_path) if db_path and db_path.is_file() else None
    logs: list[str] = []

    try:
        obs, pano_proj = process_e57_file(
            e57_path,
            config=config,
            project_db=project_db,
            log=logs.append,
        )
        return e57_path.name, obs, pano_proj, logs, None
    except Exception as exc:
        logs.append(f"  ОШИБКА: {exc}")
        return e57_path.name, [], [], logs, traceback.format_exc()
    finally:
        if project_db is not None:
            project_db.close()


def run_pipeline(
    config: PipelineConfig,
    *,
    log: LogFn | None = None,
    progress: ProgressFn | None = None,
    cancel: CancelFn | None = None,
) -> PipelineResult:
    log = log or (lambda _msg: None)
    progress = progress or (lambda _p, _msg: None)
    cancel = cancel or (lambda: False)

    folder = Path(config.e57_folder)
    e57_files = sorted(folder.glob("*.e57"))
    if not e57_files:
        raise FileNotFoundError(f"E57 файлы не найдены в {folder}")

    if config.pano_folder is None:
        default_pano = folder / "pano"
        if default_pano.is_dir():
            config.pano_folder = default_pano

    db_path = config.db_path or find_project_db(folder)
    project_db: ProjectDatabase | None = None
    if db_path and db_path.is_file():
        project_db = load_project_database(db_path)
        log(f"DB: {db_path} ({project_db.setup_count} станций)")
    else:
        log("DB не найдена")
        db_path = None

    mode_label = (
        "активная СК (E57)"
        if config.coord_mode == CoordExportMode.ACTIVE
        else "глобальная SetupRef"
    )
    log(f"Экспорт координат: {mode_label}")

    log(f"Fusion: {config.fusion_mode.value}")
    scales = config.pano_detect_scales or (config.detect_scale,)
    log(f"Pano ArUco scales: {scales}")
    log(f"Ray-guided pass: {'да' if config.ray_guided_pass else 'нет'}")
    log(f"Intensity refine: {'да' if config.refine_intensity else 'нет'}")

    if config.pano_folder and config.pano_folder.is_dir():
        log(f"Панорамы (обязательно): {config.pano_folder}")
    else:
        log("Панорамы: папка pano/ не найдена — обработка невозможна")

    families = config.families or list(TAG_FAMILIES.keys())[:3]
    log(f"Семейства: {', '.join(families)}")
    log(f"E57 файлов: {len(e57_files)}")

    n_workers = min(config.max_workers, multiprocessing.cpu_count(), len(e57_files))
    log(f"Параллельность: {n_workers} процесс(ов), кеш: {'да' if config.use_cache else 'нет'}")

    all_observations: list = []
    pano_projections_all: list[tuple[str, str, int, float, float]] = []
    detections_total = 0
    db_path_str = str(db_path) if db_path else None

    try:
        if n_workers <= 1:
            for idx, e57_path in enumerate(e57_files):
                if cancel():
                    log("Остановлено пользователем")
                    break
                pct = idx / max(len(e57_files), 1)
                progress(pct, f"Обработка {e57_path.name}...")
                log(f"\n{e57_path.name}")
                try:
                    obs, pano_proj = process_e57_file(
                        e57_path,
                        config=config,
                        project_db=project_db,
                        log=log,
                    )
                    detections_total += len(obs)
                    all_observations.extend(obs)
                    pano_projections_all.extend(pano_proj)
                except Exception as exc:
                    log(f"  ОШИБКА: {exc}")
                    log(traceback.format_exc())
        else:
            worker_args = [(str(p), config, db_path_str) for p in e57_files]
            done = 0
            with ProcessPoolExecutor(max_workers=n_workers) as pool:
                futures = {pool.submit(_process_e57_worker, a): a[0] for a in worker_args}
                for future in as_completed(futures):
                    if cancel():
                        log("Остановлено пользователем")
                        pool.shutdown(wait=False, cancel_futures=True)
                        break
                    name, obs, pano_proj, worker_logs, err = future.result()
                    done += 1
                    progress(done / len(e57_files), f"Готово {name}...")
                    log(f"\n{name}")
                    for line in worker_logs:
                        log(line)
                    if err:
                        log(err)
                    detections_total += len(obs)
                    all_observations.extend(obs)
                    pano_projections_all.extend(pano_proj)

        progress(0.95, "Усреднение...")
        fused = fuse_observations(all_observations, mode=config.fusion_mode)
        rejected_total = sum(t.rejected_count for t in fused)
        if rejected_total:
            log(f"\nFusion: отброшено {rejected_total} outlier-наблюдений")
        log(f"Итого (pass 1): {detections_total} наблюдений -> {len(fused)} уникальных тегов")

        if config.ray_guided_pass and fused:
            log("\n--- Ray-guided pass (LiDAR re-observation) ---")
            ray_cfg = RayGuidedConfig()
            seen_by_scan: dict[str, set[tuple[str, int]]] = {}
            for obs in all_observations:
                seen_by_scan.setdefault(obs.scan_name, set()).add((obs.family, obs.tag_id))

            ray_obs: list = []
            n_files = max(len(e57_files), 1)
            for idx, e57_path in enumerate(e57_files):
                if cancel():
                    break
                progress(
                    0.95 + 0.04 * idx / n_files,
                    f"Ray-guided {idx + 1}/{len(e57_files)}",
                )
                e57 = E57(str(e57_path))
                try:
                    header = e57.get_header(0)
                    scan_name = _scan_name_from_e57(e57_path, header)
                    already = seen_by_scan.get(scan_name, set())
                    if len(already) >= len(fused):
                        continue

                    data = _load_scan_data(e57_path, e57, use_cache=config.use_cache)
                    xyz = np.stack(
                        [data["cartesianX"], data["cartesianY"], data["cartesianZ"]], axis=1
                    )
                    rows = data["rowIndex"]
                    cols = data["columnIndex"]
                    scanner_pos = np.array(header.translation, dtype=np.float64)

                    def _export(pt: np.ndarray, _sn=scan_name) -> np.ndarray:
                        return _export_point(project_db, pt, _sn, config.coord_mode)

                    new_obs = reobserve_tags_in_scan(
                        fused,
                        scan_name=scan_name,
                        xyz=xyz,
                        rows=rows,
                        cols=cols,
                        scanner_pos=scanner_pos,
                        already_seen=already,
                        export_fn=_export,
                        config=ray_cfg,
                    )
                    if new_obs:
                        log(f"  [{scan_name}] ray-guided: +{len(new_obs)} наблюдений")
                        ray_obs.extend(new_obs)
                finally:
                    e57.close()

            if ray_obs:
                all_observations.extend(ray_obs)
                detections_total += len(ray_obs)
                fused = fuse_observations(all_observations, mode=config.fusion_mode)
                log(
                    f"После ray-guided: {detections_total} наблюдений -> {len(fused)} уникальных тегов"
                )
            else:
                log("Ray-guided: новых наблюдений нет")

        log(f"Итого: {detections_total} наблюдений -> {len(fused)} уникальных тегов")

        rs_gcp_path = config.output_csv
        if rs_gcp_path is None:
            rs_gcp_path = folder / "apriltag_realityscan_gcp.csv"

        export_realityscan_gcp_csv(fused, rs_gcp_path)
        log(f"RealityScan GCP: {rs_gcp_path}")

        centers_path = rs_gcp_path.with_name("apriltag_centers.csv")
        export_csv(fused, centers_path, coord_mode=config.coord_mode)
        log(f"Внутренний отчёт: {centers_path}")

        metashape_path = rs_gcp_path.with_name("apriltag_metashape_markers.csv")
        export_metashape_markers_csv(fused, metashape_path)
        log(f"Metashape markers: {metashape_path}")
        metashape_proj_path = rs_gcp_path.with_name("apriltag_metashape_projections.csv")
        export_metashape_projections_from_pano(pano_projections_all, metashape_proj_path)
        log(f"Metashape projections: {metashape_proj_path}")

        rs_meas_path = rs_gcp_path.with_name("apriltag_realityscan_measurements.csv")
        n_meas = export_realityscan_cp_measurements_from_pano(
            pano_projections_all,
            rs_meas_path,
            fused_tags=fused,
        )
        log(f"RealityScan 2D measurements: {rs_meas_path} ({n_meas} строк)")

        compare_path = rs_gcp_path.with_name("apriltag_compare.csv")
        export_compare_csv(all_observations, compare_path, coord_mode=config.coord_mode)
        if any(o.center_alt_e57 is not None for o in all_observations):
            log(f"Сравнение pano/intensity: {compare_path}")

        progress(1.0, "Готово")
        return PipelineResult(
            fused_tags=fused,
            output_csv=rs_gcp_path,
            compare_csv=compare_path,
            scans_processed=len(e57_files),
            detections_total=detections_total,
        )
    finally:
        if project_db is not None:
            project_db.close()
