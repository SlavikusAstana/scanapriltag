# Импорт AprilTag в Agisoft Metashape

Файлы рядом с `apriltag_centers.csv`:

| Файл | Назначение |
|------|------------|
| `apriltag_metashape_markers.csv` | 3D координаты (Reference) |
| `apriltag_metashape_projections.csv` | 2D на JPG-панорамах (опционально) |

## Рекомендуемый способ: 3D на все ракурсы

Как при импорте только через **Reference** — маркер виден на всех сканах/гранях, где точка попадает в кадр.

1. Выровнять laser scans.
2. **Reference → Import** → `apriltag_metashape_markers.csv`  
   - разделитель `,`, первая строка — заголовок  
   - колонки: label, x, y, z, accuracy_x, accuracy_y, accuracy_z  
   - система координат — локальная, как в E57  
3. **Tools → Run Script…** → `tools/import_metashape_projections.py`  
   - файл CSV **не** выбирается  
   - скрипт пересчитывает 2D из 3D на **все камеры** chunk (6 граней × N сканов)
4. При необходимости: **Tools → Markers → Refine Markers**

Параметры в скрипте:

- `CLEAR_PROJECTIONS_FIRST = True` — убрать старые 2D перед пересчётом  
- `MARGIN_PX` — запас у края кадра

## Опционально: CSV с пикселями панорамы

Только если в chunk добавлены **те же JPG**, что в `pano\` (`new_fasade_01.jpg` …), не cubemap GUID.

**Tools → Run Script…** → `tools/import_metashape_projections_csv.py` → выбрать CSV.

Для laser scan + 6 граней E57 этот путь **не подходит** — используйте 3D-способ выше.

## Примечания

- **Tools → Markers** не содержит Import CSV для 2D.  
- **Tools → Import → Import Markers** — только Agisoft XML.  
- Лишние маркеры на одном виде после только Reference — нормально до шага 3 (пересчёт из 3D) или ручной очистки.
