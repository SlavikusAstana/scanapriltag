# AprilTagE57Tool — статус проекта

Краткий обзор. Полная техническая документация: **[IMPLEMENTATION.md](IMPLEMENTATION.md)**.

Дата: 2026-05-31 | Версия: **v5** (валидирована на Smirnoff)

---

## Статус: готово для Smirnoff

| Критерий | Цель | Факт |
|----------|------|------|
| Точность 7 эталонов | < 10 мм | **7/7 OK** (1.2–6.4 мм) |
| Время 17 E57 | < 5 мин | **~4.4 мин** |
| Воспроизводимость | CSV + validate | `validate.py` exit 0 |

---

## Что сделано (v5)

- **Pano-first pipeline:** ArUco на JPG 20480×10240 → `center_from_pano_ray` → plane-ray intersect
- **mye57** (из `D:\code\rudenko`): чтение intensity + row/col
- **Fusion:** weighted average + sigma-clip outlier rejection
- **Parallel:** 4 workers + disk cache `~/.apriltag_e57_cache/`
- **validate.py:** сверка с `aprlth/` (несколько строк в файле — OK если любая в пороге)
- **GUI:** папка pano, все параметры

---

## Основной алгоритм (одной строкой)

Pano UV → equirectangular ray → LiDAR angular cone → row/col patch → plane-ray intersect → 3D center.

Формулы: см. [IMPLEMENTATION.md §3](IMPLEMENTATION.md#3-формулы).

---

## Главные трудности (решенные и нет)

| Проблема | Решение / статус |
|----------|------------------|
| VIS–LiDAR parallax | Pano ray + LiDAR, не VIS pixels |
| pye57 без intensity | mye57 |
| Linear pano→row/col (~1 м) | Удалён из pipeline |
| Cubemap fallback | **Удалён** — только pano JPG |
| Auto az calibration | **Неудачна, отключена** — см. ниже |
| Intensity ArUco refine | Код есть, на Smirnoff не сработал |
| aprlth/297.txt две строки | validate берёт лучшее совпадение |

---

## Неудачная калибровка az_offset (кратко)

**Цель:** автоматически найти yaw-offset между Register360 pano и LiDAR grid.

**Метод:** grid search offset по ~150 точкам облака; `true_az` из локальных XYZ vs `az_pano` из linear `columnIndex → u`.

**Результат:** offset ≈ +0.28 rad (+16°) — минимизирует ошибку **неверной** linear модели, но ломает pano ray: tag 472 **1240 мм** вместо **6 мм**.

**Причина:** linear col→u не описывает RTC360; оптимизация по random cloud ≠ точность по тегам.

**Сейчас:** `az_offset = 0` (формула уже содержит `-π` в az). Функция `calibrate_az_offset` в коде, вызов отключён.

Подробно: [IMPLEMENTATION.md §6](IMPLEMENTATION.md#6-неудачная-авто-калибровка-az_offset).

---

## Результаты validate (Smirnoff)

```
Tag   Error   Ref#
108    1.9mm   -
197    4.7mm   -
297    3.1mm   2
364    1.2mm   -
472    6.4mm   -
502    5.8mm   -
538    4.1mm   -
```

---

## Структура

```
AprilTagE57Tool/
  mye57.py, validate.py
  e57_tags/  (pipeline, pano_detector, intensity_grid, fusion, cloud_cache, ...)
  docs/IMPLEMENTATION.md   ← формулы, история, трудности
  docs/STATUS_AND_ANALYSIS.md  ← этот файл
```

---

## Открыто

- Больше ID на pano (scale 1+2, ~90 на здании, сейчас ~37)
- Intensity refine (ArUco на grid)
- Надёжная az auto-calibration
- Register360 pano spec (официальная)

---

## Point-cloud detection (прототип 2026-05-31)

На всех 17 E57 теги есть (~90 на здании), pano-pipeline находит **37 ID**.

Поиск по LiDAR-облаку (Hamming/NCC) снят с поддержки — только pano JPG + ray-guided.

- Эталоны tag36h11 **0–586** (587 шт.), кеш bitmap
- Поиск на **LiDAR intensity row/col grid** (без VIS)
- v0 на fasade_01: 214 кандидатов за ~50s, но **много false positives**; known tags (472…) не декодированы
- v1 план: LiDAR equirect + Hamming decode по bit pattern
