package com.scanapriltag.localization

import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import java.util.Locale

object L {
    var current by mutableStateOf(AppLanguage.Russian)
        private set

    fun initialize(language: AppLanguage) {
        current = language
    }

    fun setLanguage(
        language: AppLanguage,
        context: android.content.Context? = null,
        persist: Boolean = true,
    ) {
        if (current == language) return
        current = language
        if (persist && context != null) LanguageSettings.save(context, language)
    }

    fun languageName(language: AppLanguage): String = when (language) {
        AppLanguage.Russian -> "Русский"
        AppLanguage.English -> "English"
    }

    fun f(key: String, vararg args: Any?): String =
        String.format(Locale.getDefault(), s(key), *args)

    fun s(key: String): String {
        val lang = current
        return table[lang to key] ?: key
    }
    val appTitle get() = s("AppTitle")
    val languageLabel get() = s("LanguageLabel")
    val settingsGroup get() = s("SettingsGroup")
    val familyAuto get() = s("FamilyAuto")
    val multiFamily get() = s("MultiFamily")
    val speed get() = s("Speed")
    val camera get() = s("Camera")
    val miss get() = s("Miss")
    val beepOnDuplicate get() = s("BeepOnDuplicate")
    val reconnectCamera get() = s("ReconnectCamera")
    val start get() = s("Start")
    val stop get() = s("Stop")
    val reset get() = s("Reset")
    val export get() = s("Export")
    val save get() = export
    val liveList get() = s("LiveList")
    val resultAfterStop get() = s("ResultAfterStop")
    val presetFast get() = s("PresetFast")
    val presetBalanced get() = s("PresetBalanced")
    val presetAccurate get() = s("PresetAccurate")
    val family36h11 get() = s("Family36h11")
    val family25h9 get() = s("Family25h9")
    val family16h5 get() = s("Family16h5")
    val family36h10 get() = s("Family36h10")
    val errorTitle get() = s("ErrorTitle")
    val resultTitle get() = s("ResultTitle")
    val savedTitle get() = s("SavedTitle")

    fun familyLabel(family: String): String = when (family) {
        "tag36h11" -> family36h11
        "tag25h9" -> family25h9
        "tag16h5" -> family16h5
        "tag36h10" -> family36h10
        else -> family.removePrefix("tag")
    }

    private val table: Map<Pair<AppLanguage, String>, String> = buildMap {
        fun add(lang: AppLanguage, key: String, value: String) {
            put(lang to key, value)
        }

        val entries = listOf(
            Triple("AppTitle", "AprilTag Scanner Pro", "AprilTag Scanner Pro"),
            Triple("LanguageLabel", "Язык", "Language"),
            Triple("SettingsGroup", "Настройки", "Settings"),
            Triple("FamilyAuto", "Семейство (авто):", "Family (auto):"),
            Triple("MultiFamily", "Несколько семейств (36h11+25h9+16h5)", "Multiple families (36h11+25h9+16h5)"),
            Triple("Speed", "Скорость:", "Speed:"),
            Triple("Camera", "Камера:", "Camera:"),
            Triple("CameraBack", "Задняя", "Back"),
            Triple("CameraFront", "Передняя", "Front"),
            Triple("CameraNoneFound", "Камера не найдена. Предоставьте разрешение и нажмите «Переподключить».", "No camera found. Grant permission and tap Reconnect."),
            Triple("CameraConnecting", "Подключение камеры...", "Connecting camera..."),
            Triple("CameraReady", "Камера готова — покажите тег для автоопределения семейства", "Camera ready — show a tag to auto-detect the family"),
            Triple("Miss", "Miss:", "Miss:"),
            Triple("BeepOnDuplicate", "Звук при повторе", "Beep on duplicate"),
            Triple("ReconnectCamera", "Переподключить камеру", "Reconnect camera"),
            Triple("Start", "Старт", "Start"),
            Triple("Stop", "Стоп", "Stop"),
            Triple("Reset", "Сброс", "Reset"),
            Triple("Save", "Экспорт", "Export"),
            Triple("Export", "Экспорт", "Export"),
            Triple("ExportEmptyHint", "Нет данных для экспорта", "Nothing to export"),
            Triple("ExportSuccessSnackbar", "Экспорт: %s", "Exported: %s"),
            Triple("SectionDetection", "Обнаружение", "Detection"),
            Triple("SectionCamera", "Камера", "Camera"),
            Triple("SectionFeedback", "Отклик", "Feedback"),
            Triple("SectionApp", "Приложение", "App"),
            Triple("StatusScanningShort", "Сканирование", "Scanning"),
            Triple("StatusIdle", "Готов", "Ready"),
            Triple("RecentTags", "Последние", "Recent"),
            Triple("ResultSummary", "Итог сессии", "Session summary"),
            Triple("ResultDuration", "Длительность: %s", "Duration: %s"),
            Triple("ResultExportAction", "Экспортировать", "Export"),
            Triple("TopBarCameraBack", "Задняя камера", "Back camera"),
            Triple("TopBarCameraFront", "Передняя камера", "Front camera"),
            Triple("TopBarMultiFamily", "Несколько семейств", "Multi-family"),
            Triple("TopBarAutoDetect", "Авто", "Auto"),
            Triple("Ok", "OK", "OK"),
            Triple("LiveList", "Список (live):", "List (live):"),
            Triple("ResultAfterStop", "Результат после «Стоп»:", "Result after Stop:"),
            Triple("PresetFast", "Быстро", "Fast"),
            Triple("PresetBalanced", "Баланс", "Balanced"),
            Triple("PresetAccurate", "Точно", "Accurate"),
            Triple("Family36h11", "36h11 (стандарт)", "36h11 (standard)"),
            Triple("Family25h9", "25h9", "25h9"),
            Triple("Family16h5", "16h5", "16h5"),
            Triple("Family36h10", "36h10", "36h10"),
            Triple("TitleAutoDetect", "AprilTag Scanner Pro — автоопределение", "AprilTag Scanner Pro — auto-detect"),
            Triple("PerfAuto", "авто", "auto"),
            Triple("PerfLine", "FPS: %.1f  |  Детекция: %d мс  |  %s", "FPS: %.1f  |  Detect: %d ms  |  %s"),
            Triple("ResultDurationLabel", "Длительность", "Duration"),
            Triple("OverlayDup", "DUP", "DUP"),
            Triple("DuplicateMark", "  [ПОВТОР]", "  [DUP]"),
            Triple("DuplicateMarkExport", " (повтор)", " (duplicate)"),
            Triple("StatusDuplicate", "ПОВТОР! %s — отложите этот тег", "DUPLICATE! %s — set this tag aside"),
            Triple("StatusFamilyDetected", "Определено: %s, ID %d — нажмите «Старт»", "Detected: %s, ID %d — press Start"),
            Triple("StatusScanning", "Сканирование — показывайте лист с тегами", "Scanning — show the sheet with tags"),
            Triple("StatusDoneDup", "Готово. Повторы есть: %s", "Done. Duplicates: %s"),
            Triple("StatusDoneNoDup", "Готово. Повторов нет.", "Done. No duplicates."),
            Triple("StatusShowTag", "Покажите тег камере — семейство определится автоматически", "Show a tag to the camera — the family will be detected automatically"),
            Triple("StatusFamilyManual", "Семейство: %s — нажмите «Старт»", "Family: %s — press Start"),
            Triple("StatusMultiFamily", "Режим нескольких семейств — нажмите «Старт»", "Multiple families mode — press Start"),
            Triple("CountLine", "Записано: %d  |  Уник.: %d  |  В кадре: %d  |  Повторов: %d", "Recorded: %d  |  Unique: %d  |  In frame: %d  |  Duplicates: %d"),
            Triple("StatRecorded", "Записано", "Recorded"),
            Triple("StatUnique", "Уник.", "Unique"),
            Triple("StatInFrame", "В кадре", "In frame"),
            Triple("StatDuplicates", "Дубликаты", "Duplicates"),
            Triple("StatFps", "FPS", "FPS"),
            Triple("LiveListEmpty", "Покажите теги камере — список появится здесь", "Show tags to the camera — the list will appear here"),
            Triple("SaveDialogTitle", "Сохранить результат", "Save result"),
            Triple("SaveSuccess", "Результат сохранён:\n%s", "Result saved:\n%s"),
            Triple("SaveFailed", "Не удалось сохранить файл:\n%s", "Could not save file:\n%s"),
            Triple("ErrorTitle", "Ошибка", "Error"),
            Triple("ResultTitle", "Результат", "Result"),
            Triple("SavedTitle", "Сохранено", "Saved"),
            Triple("ExportTitle", "AprilTag Scanner Pro", "AprilTag Scanner Pro"),
            Triple("ExportDate", "Дата: %s", "Date: %s"),
            Triple("ExportFamilies", "Семейства: %s", "Families: %s"),
            Triple("ExportEmpty", "Список пуст — теги не обнаружены.", "List is empty — no tags detected."),
            Triple("ExportTotal", "Всего записано: %d", "Total recorded: %d"),
            Triple("ExportUnique", "Уникальных: %d", "Unique: %d"),
            Triple("ExportDupYes", "ПОВТОРЫ ЕСТЬ: %s", "DUPLICATES: %s"),
            Triple("ExportDupNo", "ПОВТОРОВ НЕТ — все теги уникальные.", "NO DUPLICATES — all tags are unique."),
            Triple("PermissionRequired", "Нужно разрешение камеры для сканирования", "Camera permission is required for scanning"),
            Triple("CompactMode", "Компакт", "Compact"),
            Triple("FullMode", "Полный", "Full"),
            Triple("ExpandPanel", "Развернуть панель", "Expand panel"),
            Triple("CompactModeHint", "Компакт — камера и управление сканом", "Compact — camera and scan controls"),
            Triple("CompactStatLine", "%d зап. · %d повт.", "%d rec. · %d dup."),
            Triple("RecordVideo", "Видео", "Video"),
            Triple("StopRecording", "Стоп видео", "Stop video"),
            Triple("RecordingIndicator", "● ЗАПИСЬ", "● REC"),
            Triple("VideoSavedSnackbar", "Видео сохранено: %s", "Video saved: %s"),
            Triple("VideoSaveFailed", "Не удалось сохранить видео:\n%s", "Could not save video:\n%s"),
            Triple("VideoNotReady", "Подождите кадр камеры, затем нажмите «Видео»", "Wait for a camera frame, then tap Video"),
            Triple("MicPermissionRequired", "Нужен доступ к микрофону для голосовых комментариев", "Microphone access is required for voice commentary"),
            Triple("MicPermissionDenied", "Без микрофона запись невозможна — разрешите доступ в настройках", "Recording needs the microphone — allow access in settings"),
            Triple("StoragePermissionRequired", "Нужен доступ к памяти, чтобы сохранить видео", "Storage access is required to save video"),
            Triple("StoragePermissionDenied", "Без доступа к памяти видео не сохранится — разрешите в настройках", "Video needs storage access — allow it in settings"),
        )

        for ((key, ru, en) in entries) {
            add(AppLanguage.Russian, key, ru)
            add(AppLanguage.English, key, en)
        }
    }
}
