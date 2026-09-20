# AprilTag Scanner Pro (Android)

Android-версия сканера AprilTag — только сканирование, без генератора. Функционал соответствует вкладке «Сканер» в Windows-приложении.

## Возможности

- Live-сканирование с камеры (CameraX)
- Автоопределение семейства до «Старт»
- Семейства: **36h11, 25h9, 16h5, 36h10**
- Режим нескольких семейств (36h11+25h9+16h5)
- Профили скорости: Быстро / Баланс / Точно
- Умные повторы (anti-flicker, miss limit)
- Подсветка повторов + звук
- Экспорт TXT / CSV / JSON
- Детекция в фоновом потоке (OpenCV Aruco)
- Русский / English

## Требования

- Android Studio Ladybug (2024.2+) или новее
- Android SDK 35
- JDK 17
- Устройство или эмулятор с камерой (API 26+)

## Сборка

1. Откройте папку `AprilTagScannerAndroid` в Android Studio
2. Дождитесь синхронизации Gradle
3. **Run** на подключённом устройстве

Или из командной строки (при установленном Android SDK):

```bat
cd AprilTagScannerAndroid
gradlew.bat assembleDebug
```

APK: `app/build/outputs/apk/debug/AprilTagScannerPro.apk`

## Подпись APK (ваше авторство)

Любой Android APK **обязательно подписан** цифровым ключом. Это и есть «авторство»:

| Сборка | Ключ | Для чего |
|--------|------|----------|
| **Debug** (`build.bat`) | общий отладочный | разработка и тесты |
| **Release** (`build-release.bat`) | **ваш** `release.keystore` | установка на телефоны, обновления |

### Один раз — создать ключ

```bat
cd AprilTagScannerAndroid
create-keystore.bat
```

Укажите **своё имя** в поле CN (Common Name) — оно попадёт в сертификат подписи.

Скопируйте настройки:

```bat
copy keystore.properties.example keystore.properties
```

Откройте `keystore.properties` и впишите пароли.

**Сохраните `release.keystore` и пароли** — без них нельзя выпускать обновления с тем же именем пакета.

### Сборка подписанного APK

```bat
build-release.bat
```

Результат: `release/AprilTagScannerPro.apk` — подписан вашим ключом.

### Проверить подпись

```bat
"%LOCALAPPDATA%\Android\Sdk\build-tools\34.0.0\apksigner.bat" verify --print-certs release\AprilTagScannerPro.apk
```

В выводе будет CN (имя) и SHA-256 отпечаток вашего сертификата.

## Использование

1. Разрешите доступ к камере
2. Покажите тег — семейство определится автоматически (или выберите вручную)
3. **Старт** — начать запись тегов
4. **Стоп** — показать отчёт
5. **Сохранить** — экспорт в TXT, CSV или JSON (выберите расширение в диалоге)

## Структура

```
app/src/main/kotlin/com/scanapriltag/
├── ScannerViewModel.kt      # логика сканирования
├── services/
│   ├── DetectionEngine.kt   # OpenCV Aruco в фоне
│   ├── ScanSession.kt       # запись и повторы
│   └── ExportHelper.kt      # TXT/CSV/JSON
├── ui/
│   ├── ScannerScreen.kt     # интерфейс
│   └── CameraPreview.kt     # CameraX
└── localization/L.kt        # RU/EN
```

## Связь с Windows-версией

Логика `ScanSession`, `DetectionEngine`, экспорт и настройки скопированы из C# проекта `AprilTagScanner`. Генератор PDF не включён.
