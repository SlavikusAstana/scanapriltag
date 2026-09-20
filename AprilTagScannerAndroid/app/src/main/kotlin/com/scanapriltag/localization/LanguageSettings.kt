package com.scanapriltag.localization

import android.content.Context
import com.scanapriltag.services.SpeedPreset

/** Persisted scanner prefs. Family / multi-family are never restored (auto-detect each launch). */
data class ScannerPrefs(
    val language: AppLanguage = AppLanguage.Russian,
    val preset: SpeedPreset = SpeedPreset.Balanced,
    val beepOnDuplicate: Boolean = true,
    val missLimit: Int = 8,
)

object LanguageSettings {
    private const val PREFS = "apriltag_scanner_settings"
    private const val KEY_LANGUAGE = "language"
    private const val KEY_PRESET = "preset"
    private const val KEY_BEEP = "beep_on_duplicate"
    private const val KEY_MISS = "miss_limit"

    fun load(context: Context): AppLanguage = loadAll(context).language

    fun loadAll(context: Context): ScannerPrefs {
        val prefs = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
        val language = prefs.getString(KEY_LANGUAGE, null)
            ?.let { runCatching { AppLanguage.valueOf(it) }.getOrNull() }
            ?: AppLanguage.Russian
        val preset = prefs.getString(KEY_PRESET, null)
            ?.let { runCatching { SpeedPreset.valueOf(it) }.getOrNull() }
            ?: SpeedPreset.Balanced
        val beep = prefs.getBoolean(KEY_BEEP, true)
        val miss = prefs.getInt(KEY_MISS, 8).coerceIn(1, 99)
        return ScannerPrefs(language, preset, beep, miss)
    }

    fun save(context: Context, language: AppLanguage) {
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
            .edit()
            .putString(KEY_LANGUAGE, language.name)
            .apply()
    }

    fun saveScanner(
        context: Context,
        preset: SpeedPreset,
        beepOnDuplicate: Boolean,
        missLimit: Int = 8,
    ) {
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
            .edit()
            .putString(KEY_PRESET, preset.name)
            .putBoolean(KEY_BEEP, beepOnDuplicate)
            .putInt(KEY_MISS, missLimit.coerceIn(1, 99))
            .apply()
    }
}
