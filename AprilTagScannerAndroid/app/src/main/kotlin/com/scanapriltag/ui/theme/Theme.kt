package com.scanapriltag.ui.theme

import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

private val LightColorScheme = lightColorScheme(
    primary = IndustrialBlue,
    onPrimary = Color.White,
    primaryContainer = IndustrialBlueContainer,
    onPrimaryContainer = IndustrialOnBlueContainer,
    secondary = IndustrialBlueDark,
    onSecondary = Color.White,
    secondaryContainer = Color(0xFFB8D4EF),
    onSecondaryContainer = IndustrialBlueDark,
    tertiary = WarningAmber,
    onTertiary = Color(0xFF3E2000),
    error = DuplicateRed,
    onError = Color.White,
    errorContainer = ErrorContainerLight,
    onErrorContainer = ErrorOnContainerLight,
    background = PanelLight,
    onBackground = TextPrimaryLight,
    surface = PanelSurface,
    onSurface = TextPrimaryLight,
    surfaceVariant = PanelSurfaceVariant,
    onSurfaceVariant = TextSecondaryLight,
    outline = BorderSubtle,
    outlineVariant = Color(0xFFE2E8F0),
)

private val DarkColorScheme = darkColorScheme(
    primary = IndustrialBlueLight,
    onPrimary = Color(0xFF002A4D),
    primaryContainer = IndustrialBlueDark,
    onPrimaryContainer = Color(0xFFD6E8F7),
    secondary = Color(0xFF7EB8E8),
    onSecondary = Color(0xFF002A4D),
    secondaryContainer = Color(0xFF0F3558),
    onSecondaryContainer = Color(0xFFB8D4EF),
    tertiary = WarningAmber,
    onTertiary = Color(0xFF3E2000),
    error = Color(0xFFFF8A80),
    onError = Color(0xFF5C0000),
    errorContainer = ErrorContainerDark,
    onErrorContainer = ErrorOnContainerDark,
    background = Graphite,
    onBackground = TextPrimaryDark,
    surface = GraphiteSurface,
    onSurface = TextPrimaryDark,
    surfaceVariant = GraphiteElevated,
    onSurfaceVariant = TextSecondaryDark,
    outline = Color(0xFF3D4556),
    outlineVariant = Color(0xFF2A3140),
)

@Composable
fun AprilTagTheme(
    darkTheme: Boolean = isSystemInDarkTheme(),
    content: @Composable () -> Unit,
) {
    MaterialTheme(
        colorScheme = if (darkTheme) DarkColorScheme else LightColorScheme,
        typography = AppTypography,
        content = content,
    )
}
