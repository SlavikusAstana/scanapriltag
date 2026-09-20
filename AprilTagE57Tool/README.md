# AprilTag E57 Tool

Извлечение 3D-координат центров AprilTag из structured E57 (Register360 / Leica RTC360).

**Документация:**
- [docs/IMPLEMENTATION.md](docs/IMPLEMENTATION.md) — формулы, трудности, история реализации, az calibration
- [docs/STATUS_AND_ANALYSIS.md](docs/STATUS_AND_ANALYSIS.md) — краткий статус

## Требования

- Python 3.10+
- E57-файлы (по одному скану на файл)
- **Растровые панорамы** из Register360: `{scan_name}.jpg` (20480×10240 equirectangular) в папке `pano/`
- Опционально: `project*.db` для экспорта в SetupRef

```bash
cd AprilTagE57Tool
pip install -r requirements.txt
```

## Запуск

```bash
python run_gui.py
```

или `run_gui.bat` (Windows).

## Pipeline

1. **Детекция 2D** — только ArUco на color JPG в `pano/` (Register360 equirectangular). Без pano скан пропускается.
2. **3D центр** — `center_from_pano_ray`:
   - equirectangular UV → луч в мировой СК
   - LiDAR точки в угловом конусе ~0.35°
   - row/col patch ±18 cells, ближняя поверхность 12 мм
   - **plane-ray intersect** (не centroid)
3. **Intensity refine** (опционально) — ArUco на intensity grid в ROI ±40 cells (на Smirnoff пока не срабатывает).
4. **Fusion** — sigma-clip, затем:
   - `best` (по умолчанию) — координаты с **одного** наблюдения с max весом (лучший ракурс: дистанция, угол, размер на pano, plane_rms);
   - `weighted` — взвешенное среднее.
   В CSV колонка `best_scan` — станция, с которой взята позиция (режим `best`).
5. **CSV** — **`apriltag_realityscan_gcp.csv`** (3D, GUI), **`apriltag_realityscan_measurements.csv`** (2D pano → RS Control Points), рядом `apriltag_centers.csv`, Metashape.

### mye57

`mye57.py` (из проекта `D:\code\rudenko`, только чтение оттуда) заменяет `pye57.E57` — корректно читает `intensity`, `rowIndex`, `columnIndex` для RTC360.

## Валидация

```bash
python validate.py --refs G:\path\to\aprlth --result apriltag_centers.csv --threshold 10
```

Формат эталонов: `{tag_id}.txt`, строки `x,y,z` в активной СК.  
Если в файле несколько строк — OK, если **любая** в пределах порога (см. `297.txt`).

## Параметры (GUI / PipelineConfig)

| Параметр | По умолчанию | Описание |
|----------|--------------|----------|
| `pano_folder` | `{e57}/pano` | Color JPG/PNG (не `*_scan.png`) |
| `pano_detect_scales` | `(2,)` | `2` / `1` / `(2,1)` — см. [docs/PERFORMANCE.md](docs/PERFORMANCE.md) |
| `ray_guided_pass` | true | LiDAR re-observation для станций без pano |
| `refine_intensity` | false | ROI ArUco на intensity grid |
| `fusion_mode` | `best` | `best` или `weighted` |
| `max_workers` | 4 | Параллельная обработка E57 |
| `use_cache` | true | Кеш облаков в `~/.apriltag_e57_cache/` |

Подробно: **[docs/PERFORMANCE.md](docs/PERFORMANCE.md)**.

## Координаты

По умолчанию — **активная СК** (совпадает с E57 и ручными отметками в Register360 viewer).

## Результаты Smirnoff (2026-05-31)

7/7 эталонных тегов < 10 мм, прогон 17 E57 ~4.4 мин.

| Tag | Error |
|-----|-------|
| 108 | 1.9 mm |
| 197 | 4.7 mm |
| 297 | 3.1 mm |
| 364 | 1.2 mm |
| 472 | 6.4 mm |
| 502 | 5.8 mm |
| 538 | 4.1 mm |

## Известные ограничения

- **az_offset = 0** фиксирован; auto-calibration реализована, но отключена (ломает точность) — см. IMPLEMENTATION.md §6
- Cubemap fallback — медленный, ~500+ мм; нужен pano export
- Intensity refine — код есть, ArUco на grid не находит теги на Smirnoff
- Перенос на другой проект может потребовать проверки az_offset / validate

## Критерий готовности

- `python validate.py` — все эталоны < 10 мм
- Полный прогон 17 E57 < 5 мин (parallel + cache)
