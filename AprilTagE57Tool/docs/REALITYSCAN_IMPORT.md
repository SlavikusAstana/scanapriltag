# Импорт AprilTag в RealityScan

Pipeline сохраняет в папке E57:

| Файл | Назначение |
|------|------------|
| **`apriltag_realityscan_gcp.csv`** | 3D — WORKFLOW → **Ground Control** |
| **`apriltag_realityscan_measurements.csv`** | 2D на pano JPG — привязка к снимкам |
| `apriltag_centers.csv` | Внутренний отчёт |

## Имена точек

```text
36h11:052   (= OpenCV ID 82)
36h11:1d8   (= OpenCV ID 472)
```

Формат: `36h11:` + **3 hex-цифры** OpenCV ID (как у авто-детекта RS).

---

## Рекомендуемый порядок (3D + 2D)

### 1. Ground Control (3D)

**WORKFLOW → Ground Control** → `apriltag_realityscan_gcp.csv`

- Разделитель `,`, первая строка — заголовок
- СК проекта = Register360 / E57

### 2. Control point measurements (2D)

**WORKFLOW → Import Metadata → Control Points** → `apriltag_realityscan_measurements.csv`

```csv
Image,Point,X,Y
G:\work\...\pano\new_fasade_01.jpg,36h11:1d8,3812.9001,4632.1119
```

- **Image** — полный путь к JPG; должен **совпадать** с путём в проекте RS (или добавьте те же pano в RS)
- **Point** — то же имя, что в GCP (`36h11:…`)
- **X, Y** — пиксели от левого верхнего угла pano

После импорта 2D точки перестанут быть **unassigned** и получат проекции на pano.

### 3. Если в RS только DSLR-фото (не pano JPG)

2D с pano **не совпадут** с путями в проекте. Варианты:

- добавить color pano из `pano/` в RS как отдельные «фото», или
- использовать только **Detect Markers** на DSLR + наш GCP 3D для тегов без 2D

---

## Пересборка 2D без полного pipeline

```bash
python tools/regenerate_realityscan_measurements.py G:\work\A495\Smirnoff\e57\new
```

Берёт `apriltag_metashape_projections.csv` + `apriltag_centers.csv`.

---

## Соответствие centers.csv

| centers.csv | RealityScan |
|-------------|-------------|
| `tag36h11;472` | `36h11:1d8` |
