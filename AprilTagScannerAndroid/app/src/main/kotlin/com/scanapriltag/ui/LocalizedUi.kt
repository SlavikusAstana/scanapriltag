package com.scanapriltag.ui

import androidx.compose.runtime.Composable
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.runtime.staticCompositionLocalOf
import com.scanapriltag.localization.AppLanguage
import com.scanapriltag.localization.L

val LocalAppLanguage = staticCompositionLocalOf { AppLanguage.Russian }

/**
 * Subscribes the UI tree to [L.current] so every [L.s] call recomposes on locale change.
 * Does not remount the tree (no [key]) — preserves sheet open state and camera token.
 */
@Composable
fun LocalizedUi(content: @Composable () -> Unit) {
    val activeLanguage = L.current
    CompositionLocalProvider(LocalAppLanguage provides activeLanguage) {
        content()
    }
}
