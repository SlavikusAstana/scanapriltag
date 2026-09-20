# AprilTagE57Tool — реализация: формулы, трудности, история

Дата обновления: 2026-05-31 (финальная версия v5, валидирована на Smirnoff).

---

## 1. Цель и результат

**Задача:** автоматически найти 3D-центры AprilTag в экспортах Register360 / RTC360 (E57), точность **< 10 мм**, время **< 5 мин** на 17 станций.

**Достигнуто на датасете Smirnoff (2026-05-31):**

| Tag | Ошибка vs aprlth | Станции |
|-----|------------------|---------|
| 108 | 1.9 мм | new_fasade_08 |
| 197 | 4.7 мм | new_fasade_08 |
| 297 | 3.1 мм | new_fasade_01, 02 (ref #2 в 297.txt) |
| 364 | 1.2 мм | new_fasade_02 |
| 472 | 6.4 мм | new_fasade_01, 02 |
| 502 | 5.8 мм | new_fasade_09, 10 |
| 538 | 4.1 мм | new_fasade_01, 02 |

Полный прогон 17 E57: **~4.4 мин** (4 процесса, кеш облаков).  
37 уникальных тегов найдено, 50 наблюдений до fusion.

---

## 2. Архитектура (финальная)

```
Register360 pano JPG (20480×10240)
        │  ArUco detect (тайлы, downscale ×2)
        ▼
   tag_id + corners (u,v)
        │
E57 point cloud (mye57)          ← intensity + rowIndex + columnIndex + XYZ
        │
        ▼
center_from_pano_ray             ← основной mm-метод
        │  (опционально)
        ▼
refine_center_via_intensity_grid ← ROI ArUco на intensity grid (если сработает)
        │
        ▼
fuse_observations (sigma-clip) → apriltag_centers.csv
```

**Требование:** color JPG в `pano/`; без pano скан пропускается (cubemap fallback удалён).

---

## 3. Формулы

### 3.1. Система координат

Экспорт по умолчанию — **активная СК** (совпадает с E57 и ручными отметками в viewer).

Преобразование active → global SetupRef (из `register360_db.py`, порт krpanomodule):

```
P_global = R_cs · P_active + T_cs
```

где `(R_cs, T_cs)` — из `project.db`, таблица coordinate systems.

### 3.2. Cubemap VIS (RTC360, legacy fallback)

Для каждой грани cubemap в `images2D/pinholeRepresentation`:

**Intrinsics:**
```
fx = focalLength / pixelWidth
fy = focalLength / pixelHeight
cx = principalPointX
cy = principalPointY
```

**Луч из пикселя (исправленная модель, без неё dot ≪ 1):**
```
x_cam = -(u - cx) / fx
y_cam =  (v - cy) / fy
d_cam = normalize([x_cam, y_cam, 1])
d_world = -R_pose @ d_cam
origin = translation_pose
```

Знак минус у `R @ d_cam` критичен для RTC360.

### 3.3. Equirectangular pano → луч (основной метод)

Register360 export: JPG **20480 × 10240** (W × H).

**Углы из пикселя (u, v):**
```
az = 2π · u/(W-1) - π + az_offset
el = π · (0.5 - v/(H-1))
```

**Луч в локальной СК сканера:**
```
d_local = [ cos(el)·sin(az),  cos(el)·cos(az),  sin(el) ]
```

**Луч в мировой СК (активная):**
```
d_world = R_scan @ d_local / |R_scan @ d_local|
origin  = translation_scan   (из E57 scan header, wxyz quaternion)
```

Для Smirnoff: **`az_offset = 0`** (см. §6 про неудачную калибровку).

### 3.4. Выбор точек LiDAR по лучу

Для каждой точки облака `p`:
```
r = p - origin
θ = arccos( (r/|r|) · d_world )
```

Отбор: `θ ≤ cone_deg` (по умолчанию **0.35°**; если точек < 20, расширить до **0.875°**).

### 3.5. Row/col patch внутри конуса

```
seed_row = median(rowIndex[in_cone])
seed_col = median(columnIndex[in_cone])
patch = { i : |row_i - seed_row| ≤ 18  AND  |col_i - seed_col| ≤ 18 }
```

### 3.6. Ближняя поверхность

```
depths = |points - origin|
d₀ = min(depths)
surface = { p : depth(p) ≤ d₀ + 12 мм }
```

### 3.7. Пересечение луча с плоскостью (финальный 3D-центр)

Вместо centroid используется **plane-ray intersection** (устойчивее при наклоне тега):

```
centroid = mean(surface_points)
[SVD] points - centroid → Vt
normal = Vt[-1]   (наименьшее singular value)

t = normal · (centroid - origin) / (normal · d_world)
center = origin + t · d_world
```

Fallback: если `|normal · d_world| < 1e-6` → centroid.

### 3.8. Fusion — веса наблюдения

```
w = w_dist · w_angle · w_size · w_quality

w_dist    = (8 / distance)²
w_angle   = |(-view_ray · normal)|²
w_size    = clamp(sqrt(area_px)/20, 0.25, 4)
w_quality = 1 / max(plane_rms, 2 мм)
```

Intensity refine: `weight × 1.5` если метод `intensity_rowcol`.

### 3.9. Fusion — sigma-clip (outlier rejection)

2 итерации:
```
centroid = weighted_mean(centers[keep])
dists_mm = |centers - centroid| · 1000
σ = max(std(dists_mm[keep]), 5 мм)
threshold = max(2σ, 20 мм)
keep = dists_mm < threshold
```

Если все отфильтрованы — оставить все наблюдения.

### 3.10. Intensity grid refine (реализован, на Smirnoff не сработал)

ROI ±40 cells вокруг `(seed_row, seed_col)` из pano ray.

Построение grayscale:
```
mask: row ∈ [r_c±40], col ∈ [c_c±40]
img[row - r_min, col - c_min] = normalize(intensity) → [0,255]
         (дальние точки перезаписывают ближние — front-to-back)
CLAHE(clipLimit=3, tile 4×4)
ArUco detect → центр маркера → ±3 cells → plane-ray intersect
```

---

## 4. Что реализовано (хронология)

| Версия | Изменение | Точность tag 472 |
|--------|-----------|------------------|
| v0 | Naive pinhole + plane fit по VIS | метры |
| v1 | Fix pinhole signs, active CS export | метры |
| v2 | Row/col search от VIS cubemap | ~500–1000 мм |
| v3 | Pano JPG detect + linear pano→row/col | ~1320 мм |
| v4 | `center_from_pano_ray` + az−π эмпирика | ~6 мм |
| **v5** | mye57, plane-intersect, fusion clip, parallel, cache, az_offset=0 | **~6 мм**, все 7 ref OK |

### v5 — полный список изменений

1. **`mye57.py`** — скопирован из `D:\code\rudenko` (read-only). Читает `intensity`, `rowIndex`, `columnIndex` через `header.point_fields`.
2. **`center_from_pano_ray`** — луч + конус + plane-ray intersect.
3. **`refine_center_via_intensity_grid`** — ROI intensity + ArUco (готов, но ArUco не находит теги на grid Smirnoff).
4. **`fusion.py`** — sigma-clip outlier rejection.
5. **`cloud_cache.py`** — кеш `.npz` в `~/.apriltag_e57_cache/`.
6. **`pipeline.py`** — ProcessPoolExecutor (4 workers), pano-first, mye57.
7. **`validate.py`** — сверка с aprlth, поддержка нескольких строк в файле.
8. Удалён **`center_from_rowcol_polygon`** из пайплайна (linear pano→row/col давал метры).
9. **`calibrate_az_offset`** — реализована, но **отключена** в pipeline (см. §6).

---

## 5. Трудности при реализации

### 5.1. VIS ≠ LiDAR (главная проблема)

Cubemap JPEG — камера VIS. `rowIndex`/`columnIndex` — нативная сетка LiDAR. Они **не совпадают пиксель-в-пиксель**.

Пример tag 472 на `new_fasade_01`:
- проекция эталонной 3D-точки на cubemap: uv ≈ (3644, 2322)
- ArUco центр на cubemap: uv ≈ (3751, 2277) — **~107 px сдвиг**

**Вывод:** VIS corners нельзя напрямую переводить в row/col для мм-точности. Pano ray обходит это: VIS даёт только **направление**, метрика — из LiDAR.

### 5.2. pye57 не читает intensity

`pye57.E57.read_scan(intensity=True)` для RTC360 Smirnoff **не возвращает** поле `intensity`, хотя оно есть в файле (`header.point_fields` содержит `intensity`).

**Решение:** `mye57.E57.read_scan_raw()` / `read_scan(intensity=True, ignore_missing_fields=True)` — проверяет `point_fields` перед чтением.

### 5.3. Linear pano → row/col

```
col = col_min + u/W · (col_max - col_min)
row = row_min + v/H · (row_max - row_min)
```

Для tag 472: true row/col = (2278, 1401), mapped ≈ (2142, 1892) — **~500 px ошибка**.  
Метод удалён из production pipeline.

### 5.4. Cubemap fallback — медленный и неточный

`estimate_tag_center`: nested loop ±60 px, step 6, connected components на ~10M точек → **2–3 мин/тег**, ошибка **~592 мм** (tag 472, fasade_02).  
Оставлен только как аварийный fallback без pano export.

### 5.5. Intensity grid — ArUco не детектирует

На Smirnoff intensity grid в ROI ±40 cells ArUco **не нашёл ни одного тега** (низкий контраст, разрешение ~1 cell = 1 px, размер маркера ~10–20 cells).  
Код refine готов; на этом датасете все результаты — `pano_ray`.

### 5.6. Эталон aprlth/297.txt

Файл содержит **две строки**:
```
27.943882,11.189103,2.290101   ← координаты tag 472 (ошибочно в файле 297)
26.087545,10.136762,2.235400   ← правильные координаты tag 297
```

`validate.py` обновлён: OK если **любая** строка в пределах порога.

### 5.7. Параллельная обработка

`ProcessPoolExecutor` на Windows: worker не может писать в tkinter log напрямую — логи собираются в worker и передаются в main thread.  
`project.db` открывается отдельно в каждом worker (read-only SQLite).

---

## 6. Неудачная авто-калибровка az_offset

### 6.1. Зачем нужна

Pano equirectangular → луч содержит неизвестный **az_offset** (сдвиг yaw между системой Register360 pano export и ориентацией сканера).  
Изначально эмпирически использовался `az -= π` (ошибочно интерпретированный как `az_offset = -π`).

### 6.2. Как реализована `calibrate_az_offset`

Файл: `e57_tags/intensity_grid.py` (функция сохранена, **в pipeline не вызывается**).

**Алгоритм:**

1. Выбрать ~150 точек облака на дистанции 1–25 м от сканера.
2. Перевести в локальную СК сканера: `p_local = R_scan^T · (p_world - origin)`.
3. Истинный azimuth LiDAR: `true_az = atan2(p_local.x, p_local.y)`.
4. Apriori u из columnIndex (линейная модель):
   ```
   u = (columnIndex - col_min) / (col_max - col_min) · (W - 1)
   ```
5. Grid search `offset ∈ [-0.5, +0.5]` rad, шаг 0.005:
   ```
   az_pano = 2π · u/(W-1) - π + offset
   err = mean(|wrap(az_pano - true_az)|)
   ```
6. Вернуть `offset` с минимальным `err`.

Ранняя версия искала в `[-π, +π]` — давала offset ≈ **+0.28 rad (+16°)**.

### 6.3. Почему неудачна

| Проблема | Объяснение |
|----------|------------|
| **Неверная модель col → u** | Linear map columnIndex → pano u не соответствует реальной геометрии RTC360 (wrap, нелинейность, разный zero-point pano vs LiDAR grid) |
| **Оптимизация «облако vs pano» ≠ «тег vs pano»** | Минимизация средней angular error по случайным точкам не гарантирует правильный луч для конкретного AprilTag |
| **Ложный минимум** | Offset +0.28 rad минимизирует ошибку linear col→u модели, но **ломает** геометрию pano ray для тегов |
| **Путаница с −π** | Формула уже содержит `-π`: `az = 2π·u/W - π + offset`. Правильный offset для Smirnoff = **0**, а не −π |

### 6.4. Экспериментальные цифры (tag 472, fasade_01)

| az_offset | Ошибка vs aprlth |
|-----------|------------------|
| 0 (текущий) | **~6 мм** |
| −π (ранняя эмпирика) | ~6 мм (случайно, т.к. −π+π=0 в другой формулировке) |
| +0.28 rad (auto-calibrate) | **~1240 мм** |

### 6.5. Текущее решение

В `pipeline.py`: **`az_offset = 0`**, вызов `calibrate_az_offset` **отключён**.

Функция оставлена в коде для будущей доработки. Возможные пути:
- калибровка по одному эталонному тегу (если известен ref XYZ)
- использование `sphericalAzimuth`/`sphericalElevation` из E57 (если доступны)
- документированный offset из Register360 / SetupInfo.csv
- narrow search ±0.1 rad вокруг 0 с метрикой по detected tags, а не random cloud

---

## 7. mye57 (из D:\code\rudenko)

Проект rudenko **не модифицировался**. Скопирован только `mye57.py`.

Ключевое отличие от pye57:

```python
# read_scan_raw — читает только поля из header.point_fields
for field in ['intensity', 'cartesianX', ...]:
    if field in header.point_fields:
        read(field)

# read_scan — + transform to world + filter invalid
data = e57.read_scan(0, intensity=True, row_column=True, ignore_missing_fields=True)
# → cartesianX/Y/Z, rowIndex, columnIndex, intensity (float 0..1)
```

Проверено на `new_fasade_01.e57`: 10 704 989 точек, intensity 0.004–1.0.

---

## 8. Структура файлов (актуальная)

```
AprilTagE57Tool/
  mye57.py                  # из rudenko
  validate.py               # CLI валидация aprlth
  run_gui.py, run_gui.bat
  e57_tags/
    pipeline.py             # оркестрация, parallel, cache
    pano_detector.py        # ArUco на equirectangular JPG
    intensity_grid.py       # pano ray, intensity refine, calibrate_az_offset (disabled)
    geometry.py             # cubemap fallback (estimate_tag_center)
    detector.py             # ArUco cubemap
    fusion.py               # weighted + sigma-clip
    cloud_cache.py          # ~/.apriltag_e57_cache/
    register360_db.py       # active CS ↔ SetupRef
    exporter.py             # CSV + compare CSV
    gui.py
  docs/
    IMPLEMENTATION.md       # этот файл
    STATUS_AND_ANALYSIS.md  # краткий статус для ревью
```

---

## 9. Запуск и валидация

```bash
cd AprilTagE57Tool
pip install -r requirements.txt

# GUI
python run_gui.py

# CLI pipeline (программно)
python -c "
from pathlib import Path
from e57_tags.pipeline import PipelineConfig, run_pipeline
run_pipeline(PipelineConfig(
    e57_folder=Path(r'G:\work\A495\Smirnoff\e57\new'),
    pano_folder=Path(r'G:\work\A495\Smirnoff\e57\new\pano'),
    max_workers=4, use_cache=True,
))
"

# Валидация
python validate.py \
  --refs G:\work\A495\Smirnoff\e57\new\aprlth \
  --result G:\work\A495\Smirnoff\e57\new\apriltag_centers.csv \
  --threshold 10
```

---

## 10. Открытые задачи

| Задача | Статус |
|--------|--------|
| Intensity refine — заставить ArUco работать на grid | Не работает на Smirnoff |
| Auto az calibration — надёжный метод | Отключена, нужна доработка |
| Cubemap fallback — ускорить или убрать | Низкий приоритет (есть pano) |
| Per-project az_offset config file | Не реализовано |
| Документация Register360 pano export spec | Не найдена |

---

## 11. Ключевой вывод для разработчиков

> **Identification** (где какой tag_id) — pano/cubemap/intensity, всё подходит.  
> **Metrology** (мм-координаты) — только LiDAR row/col через angular cone + plane-ray intersect.  
> VIS pixels (cubemap или linear pano→row/col) **не дают мм** из-за parallax VIS–LiDAR.
