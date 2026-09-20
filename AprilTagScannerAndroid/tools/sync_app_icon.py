"""Generate Android launcher icons from the shared Windows AppIcon.ico."""
from __future__ import annotations

import os
import sys

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_ICO = os.path.join(ROOT, "..", "AprilTagScanner", "Assets", "AppIcon.ico")
RES = os.path.join(ROOT, "app", "src", "main", "res")

SIZES = {
    "mipmap-mdpi": 48,
    "mipmap-hdpi": 72,
    "mipmap-xhdpi": 96,
    "mipmap-xxhdpi": 144,
    "mipmap-xxxhdpi": 192,
}

ADAPTIVE_XML = """<?xml version="1.0" encoding="utf-8"?>
<adaptive-icon xmlns:android="http://schemas.android.com/apk/res/android">
    <background android:drawable="@color/ic_launcher_background" />
    <foreground android:drawable="@drawable/ic_launcher_foreground" />
</adaptive-icon>
"""

# Adaptive icon safe zone: center 66% of 108dp canvas.
ADAPTIVE_CANVAS = 432
ADAPTIVE_ICON_SCALE = 0.82


def load_icon() -> Image.Image:
    src_path = os.path.normpath(SRC_ICO)
    if not os.path.isfile(src_path):
        print(f"ERROR: icon not found: {src_path}", file=sys.stderr)
        raise SystemExit(1)
    return Image.open(src_path).convert("RGBA")


def write_legacy_mipmaps(icon: Image.Image) -> None:
    for folder, size in SIZES.items():
        out_dir = os.path.join(RES, folder)
        os.makedirs(out_dir, exist_ok=True)
        resized = icon.resize((size, size), Image.Resampling.LANCZOS)
        for name in ("ic_launcher.png", "ic_launcher_round.png"):
            resized.save(os.path.join(out_dir, name))


def write_adaptive_foreground(icon: Image.Image) -> None:
    """Full AppIcon centered in adaptive safe zone; black goes to background color."""
    drawable_dir = os.path.join(RES, "drawable")
    os.makedirs(drawable_dir, exist_ok=True)

    icon_size = int(ADAPTIVE_CANVAS * ADAPTIVE_ICON_SCALE)
    scaled = icon.resize((icon_size, icon_size), Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", (ADAPTIVE_CANVAS, ADAPTIVE_CANVAS), (0, 0, 0, 0))
    offset = (ADAPTIVE_CANVAS - icon_size) // 2
    canvas.paste(scaled, (offset, offset), scaled)
    canvas.save(os.path.join(drawable_dir, "ic_launcher_foreground.png"))


def write_adaptive_xml() -> None:
    anydpi_dir = os.path.join(RES, "mipmap-anydpi-v26")
    os.makedirs(anydpi_dir, exist_ok=True)
    for name in ("ic_launcher.xml", "ic_launcher_round.xml"):
        path = os.path.join(anydpi_dir, name)
        with open(path, "w", encoding="utf-8", newline="\n") as file:
            file.write(ADAPTIVE_XML)


def main() -> int:
    icon = load_icon()
    write_legacy_mipmaps(icon)
    write_adaptive_foreground(icon)
    write_adaptive_xml()
    print(f"Synced launcher icons (legacy + adaptive) from {os.path.normpath(SRC_ICO)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
