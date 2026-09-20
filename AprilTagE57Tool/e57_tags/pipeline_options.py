"""Pipeline presets and helpers (pano scale, speed vs recall)."""

from __future__ import annotations

# GUI / config preset keys
PANO_SCALE_FAST = "2"
PANO_SCALE_FULL = "1"
PANO_SCALE_MAX = "1+2"

PANO_SCALE_LABELS: dict[str, str] = {
    PANO_SCALE_FAST: "2 — быстро (~6–8 мин с ray)",
    PANO_SCALE_FULL: "1 — полное разрешение (~14–16 мин с ray)",
    PANO_SCALE_MAX: "1+2 — максимум ID на pano (~20–25 мин с ray)",
}

PANO_SCALE_TOOLTIPS: dict[str, str] = {
    PANO_SCALE_FAST: (
        "ArUco на color JPG, панорама уменьшена в 2× (~10240×5120).\n"
        "Рекомендуемый режим по умолчанию.\n\n"
        "Это не поиск по всему LiDAR-облаку — только растровая pano."
    ),
    PANO_SCALE_FULL: (
        "ArUco на полной pano 20480×10240.\n"
        "Лучше видны дальние мелкие теги на JPG.\n\n"
        "Всё ещё только pano, не глобальный перебор облака точек."
    ),
    PANO_SCALE_MAX: (
        "Максимум уникальных ID на pano: два прохода ArUco (scale 2 и 1).\n"
        "Только color JPG, ~18–20 мин (+ ray-guided ~2–3 мин).\n\n"
        "Вместе с Ray-guided: для тегов, уже найденных на другой станции, "
        "доп. 3D на сканах без детекций на JPG."
    ),
}

RAY_GUIDED_TOOLTIP = (
    "Работа с LiDAR-облаком, но не полный поиск тегов.\n\n"
    "После pano: для каждого tag_id, уже найденного на другой станции, "
    "от позиции текущего сканера строится луч к известной 3D-точке → "
    "точки в угловом конусе (row/col, XYZ) → plane-ray → новое наблюдение.\n\n"
    "Не находит новые ID без pano. Полезно для станций 13–17 (0 на JPG). "
    "+1–3 мин."
)

INTENSITY_REFINE_TOOLTIP = (
    "В ROI ±40 cells вокруг pano-ray — ArUco на карте LiDAR intensity (row/col).\n"
    "На Smirnoff теги на grid не декодируются; уточнение обычно не срабатывает."
)

FUSION_TOOLTIP = (
    "best — итоговая позиция с одной станции (max вес: ракурс, дистанция, размер на pano).\n"
    "weighted — взвешенное среднее всех станций."
)


def pano_scales_from_preset(preset: str) -> tuple[int, ...]:
    """Map GUI preset to OpenCV downscale factors (1 = full 20480×10240)."""
    s = preset.strip().lower()
    if "1+2" in s or "2+1" in s:
        return (2, 1)
    if s.startswith("1 ") or s == "1" or s.startswith("1—") or s.startswith("1 -"):
        return (1,)
    return (2,)


def pano_preset_label(scales: tuple[int, ...]) -> str:
    if scales == (1,):
        return PANO_SCALE_FULL
    if scales == (2, 1) or scales == (1, 2):
        return PANO_SCALE_MAX
    return PANO_SCALE_FAST
