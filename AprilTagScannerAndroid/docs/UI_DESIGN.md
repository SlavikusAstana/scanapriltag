# AprilTag Scanner Pro — Android UI Design Brief

Документ для дизайнера / нейросети: текущее состояние интерфейса, ограничения и задачи на улучшение.

**Платформа:** Android, Jetpack Compose, Material Design 3  
**Языки:** RU / EN (переключение в настройках)  
**Desktop-референс:** Windows-приложение `AprilTagScanner/` (WPF, та же логика сканирования)

---

## 1. Назначение приложения

Мобильный сканер AprilTag: камера в реальном времени, детекция меток, запись уникальных ID, предупреждение о дубликатах, экспорт результата. Генератор PDF-тегов **отсутствует** (есть только в C# версии).

---

## 2. Режимы экрана

### 2.1 Полный режим (по умолчанию)

```
┌─────────────────────────────┐
│  TopBar: заголовок,         │
│  [компакт] [настройки]      │
├─────────────────────────────┤
│                             │
│   Камера + оверлей (~44%)   │
│   градиент + статус + FPS   │
│                             │
├─────────────────────────────┤
│   Панель управления (~56%)  │
│   • 4 stat-карточки         │
│   • Start / Stop / Reset    │
│   • Save                    │
│   • Live list (скролл)      │
│   • Result card (после Stop)│
└─────────────────────────────┘
```

### 2.2 Компактный режим (камера ~на весь экран)

Включается кнопкой «развернуть» или автоматически при **Start**.

```
┌─────────────────────────────┐
│ ▓ плавающая панель (top) ▓  │  ← полупрозрачная чёрная
│ [выход] статус + счётчики   │     «Записано N · Дубл. M»
│                    [⚙]      │
│                             │
│      КАМЕРА + ОВЕРЛЕЙ       │
│      (зелёные/красные рамки)│
│                             │
│   градиент + строка статуса │
├─────────────────────────────┤
│ ░ bottom dock (surface) ░   │  ← белая/тёмная карточка
│ [чипы последних 4 тегов]    │
│ [Start/Stop] [Save] [Reset] │
└─────────────────────────────┘
```

**Скрыто в компактном:** полная сетка статистики, live list, result card, FPS chip.

---

## 3. Цветовая палитра

Исходники: `app/src/main/kotlin/com/scanapriltag/ui/theme/Color.kt`, `Theme.kt`

| Роль | Light | Dark | Использование |
|------|-------|------|---------------|
| Primary | `#1565C0` | `#9ECAFF` | Акцент, scanning status |
| Primary container | `#D1E4FF` | `#00497D` | Кнопка Start |
| Secondary (teal) | `#00695C` | `#8BD4C4` | Вторичный акцент |
| Background | `#F5F7FA` | `#111318` | Фон приложения |
| Surface | `#FFFFFF` | `#1A1C22` | Панели, bottom sheet |
| Surface variant | `#E1E7F0` | `#2D3139` | Stat chips, live list |
| Error | `#BA1A1A` | `#FFB4AB` | Дубликаты, Stop |
| Success (overlay) | `#2E7D32` | — | Рамка найденного тега |
| Warning (overlay) | `#E65100` | — | Auto-probe рамка |
| Camera BG | `#0A0A0A` | — | Область превью |
| Overlay scrim | `#CC000000` | — | Градиент под текстом на камере |
| Overlay text | `#FFFFFF` | — | Текст поверх камеры |

**Dynamic Color отключён** — фиксированная палитра (избегали «белое на белом»).

---

## 4. Типографика

Источник: `ui/theme/Type.kt`  
Шрифт: **System Sans Serif** (Roboto на Android). Отдельный brand-font не задан.

| Стиль | Размер | Weight | Где |
|-------|--------|--------|-----|
| headlineSmall | 24sp | SemiBold | Заголовок настроек |
| titleMedium | 16sp | SemiBold | TopBar заголовок |
| titleSmall | 14sp | Medium | Заголовки карточек |
| bodyMedium | 14sp | Normal | Live list, основной текст |
| bodySmall | 12sp | Normal | Статус на камере |
| labelSmall | 11sp | Medium | Подписи stat chips |

---

## 5. Компоненты и паттерны

| Комponent | Material 3 | Файл |
|-----------|------------|------|
| Scaffold + TopAppBar | CenterAlignedTopAppBar | `ScannerScreen.kt` |
| Stat cards | ElevatedCard | `ScannerScreen.kt` |
| Actions | FilledTonalButton, OutlinedButton | `ScannerScreen.kt` |
| Live tags | Card + LazyColumn | `ScannerScreen.kt` |
| Settings | ModalBottomSheet | `SettingsSheet.kt` |
| Dialogs | AlertDialog | `ScannerScreen.kt` |
| Tag overlay | Canvas (Compose) | `TagOverlay.kt` |
| Camera | CameraX PreviewView | `CameraPreview.kt` |

**Скругления:** камера bottom 24dp; control panel top 24dp; compact dock top 20dp; floating bar 16dp.

**Отступы:** горизонтальные 12–16dp; vertical scroll в полной панели.

---

## 6. Оверлей камеры

- Рамки тегов: зелёный (OK), красный толстый (дубликат), оранжевый (auto-probe до старта)
- Подписи ID у углов тегов (native canvas text)
- FIT_CENTER масштабирование — координаты из `FrameOrientation.kt`

---

## 7. Настройки (bottom sheet)

- Язык (RU/EN)
- Семейство тегов + multi-family
- Speed preset (Fast/Balanced/Accurate)
- Камера front/back
- Miss limit
- Beep on duplicate
- Reconnect camera

Блокируются во время активного сканирования (кроме reconnect где разрешено).

---

## 8. Иконка приложения

**Источник (общий с Windows):** `AprilTagScanner/Assets/AppIcon.ico` (256×256, чёрный фон, AprilTag-паттерн).

Android: adaptive icon (API 26+) + PNG mipmaps из `AprilTagScanner/Assets/AppIcon.ico` — чёрный фон, паттерн AprilTag (как в Windows). Старый placeholder «4 белых квадрата на синем» удалён.

Превью: `docs/app_icon_source.png`

---

## 9. Известные слабые места (задача для редизайна)

1. **Визуальная иерархия** — stat-карточки в полном режиме одинаково «громкие»; сложно быстро считать главное число (записано).
2. **Компактный dock** — функционален, но выглядит как стандартный M3 без характера; чипы тегов мелкие.
3. **Нет брендинга** — generic blue/teal Material; не связан визуально с desktop WPF (там проще, серые GroupBox).
4. **TopBar в полном режиме** — мало воздуха, заголовок + статус сжаты.
5. **Settings sheet** — длинный список без группировки/иконок/секций.
6. **Нет тёмной темы как отдельного UX-решения** — палитра есть, но не тестировалась на OLED/compact.
7. **Нет onboarding** — пользователь не понимает compact mode без подсказки.
8. **Save/Export** — одна кнопка без прогресса/формата файла в UI.

---

## 10. Пожелания к новому дизайну

- Сохранить **два режима**: полный (аналитика) и компакт (работа «в поле»).
- Камера и оверлей — **главный фокус**; статистика не должна перекрывать preview.
- Чёткая семантика цветов: зелёный = записано, красный = дубликат, нейтральный = в кадре.
- Доступность: контраст текста на камере, tappable targets ≥ 48dp.
- RU/EN — строки не должны ломать layout (ellipsis OK).
- Стиль: профессиональный инструмент / industrial, не consumer social app.
- Можно предложить: custom font, иконки семейств тегов, haptic feedback, анимации записи тега.

---

## 11. Файлы для разработки

```
ui/theme/Color.kt      — палитра
ui/theme/Theme.kt      — Material3 colorScheme
ui/theme/Type.kt       — typography
ui/ScannerScreen.kt    — layouts full + compact
ui/SettingsSheet.kt    — настройки
ui/TagOverlay.kt       — оверлей
ui/CameraPreview.kt    — CameraX
localization/L.kt      — строки RU/EN
```

---

## 12. Промпт-шаблон для нейросети

> Спроектируй UI/UX для Android-приложения «AprilTag Scanner Pro» — промышленный сканер QR-подобных меток AprilTag с камерой. Два режима: полный (статистика + список) и компакт (камера почти на весь экран). Material 3, палитра primary `#1565C0`, фон `#F5F7FA`. Нужны: mockup главного экрана, compact mode, bottom sheet настроек, иконка adaptive (чёрный фон, паттерн AprilTag). Стиль: чёткий, технический, хорошая читаемость на солнце. RU/EN.

---

*Версия документа: 2026-05-31. Сгенерировано из текущего кода проекта.*
