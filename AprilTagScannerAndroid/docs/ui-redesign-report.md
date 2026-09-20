# UI Redesign Report — AprilTag Scanner Pro (Android)

## Files changed

| File | Change |
|------|--------|
| `ui/theme/Color.kt` | Industrial palette (blue/green/red/amber/graphite) |
| `ui/theme/Theme.kt` | Light/dark Material 3 schemes from new palette |
| `ui/theme/Type.kt` | `StatNumberStyle`, `HudLabelStyle`, `SectionHeadingStyle` |
| `ui/ScannerScreen.kt` | Orchestration, snackbar export feedback, layout weights 63/37 |
| `ui/ScannerComponents.kt` | **New** — TopBar, stats, actions, HUD, dock, result card |
| `ui/SettingsSheet.kt` | Grouped sections: Detection, Camera, Feedback, App |
| `ui/TagOverlay.kt` | Label pill backgrounds, thicker borders, semantic colors |
| `ui/ScannerPreviews.kt` | **New** — Compose previews for full/compact/result |
| `localization/L.kt` | RU/EN strings for export, sections, stats, HUD |
| `ScannerViewModel.kt` | Scan duration, export snackbar state (logic unchanged) |
| `app/build.gradle.kts` | Version 1.1.0 (versionCode 3) |

## Visual summary

- **Industrial look:** graphite camera surfaces, blue accent, high-contrast HUD.
- **Full mode:** camera ~63% height; primary “Записано” stat with large number; secondary chips for duplicates / in-frame / FPS.
- **Actions:** full-width Start/Stop; Export + Reset row (Reset de-emphasized vs Stop).
- **Live list:** compact rows with green/red left accent bar; recent entries highlighted.
- **Result card:** unique count, duplicates, duration, export button.
- **Compact mode:** floating graphite HUD (recorded + duplicates); bottom dock with larger tag chips and nav-bar safe padding.
- **Overlay:** green / red / amber borders; ID labels on colored pill for sunlight readability.
- **Settings:** four grouped sections with icons and disabled-while-scanning behavior.
- **Export:** label “Экспорт”; snackbar confirmation with file name after save.

## Intentionally not changed

- CameraX pipeline and frame processing
- OpenCV / `DetectionEngine` detection logic
- `ScanSession` duplicate/miss-limit rules
- Export file format and `ExportHelper` content
- Compact/full mode toggle behavior (Start still enters compact)
- Dynamic Material You colors (still disabled)

## TODOs / limitations

- **Haptic feedback:** not implemented (no fake toggle added).
- **In-app theme switch:** follows system light/dark only.
- **Multiple export formats:** single `.txt` via system document picker (unchanged).
- **Scan duration:** shown after Stop; not tracked if app is killed mid-scan.
- **Result dialog:** brief summary dialog kept in addition to result card + snackbar.

*2026-05-31*
