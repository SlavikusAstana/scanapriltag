package com.scanapriltag.ui

import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Surface
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import com.scanapriltag.CameraFacing
import com.scanapriltag.ScannerUiState
import com.scanapriltag.localization.AppLanguage
import com.scanapriltag.localization.L
import com.scanapriltag.models.LiveLine
import com.scanapriltag.services.SpeedPreset
import com.scanapriltag.ui.theme.AprilTagTheme

private val previewState = ScannerUiState(
    language = AppLanguage.Russian,
    statusText = "Сканирование — показывайте лист с тегами",
    perfText = "FPS: 24.5  |  Detect: 18 ms  |  Баланс",
    recordedCount = 12,
    uniqueCount = 11,
    inFrameCount = 3,
    duplicateCount = 1,
    scanning = false,
    cameraReady = true,
    startEnabled = true,
    saveEnabled = true,
    selectedFamily = "tag36h11",
    familyLocked = true,
    preset = SpeedPreset.Balanced,
    liveLines = listOf(
        LiveLine("1. 36h11 ID 316", false),
        LiveLine("2. 36h11 ID 521", false),
        LiveLine("3. 36h11 ID 316  [ПОВТОР]", true),
    ),
    scanDurationText = "1:42",
    resultText = "report",
)

@Preview(showBackground = true, heightDp = 800)
@Composable
private fun FullScannerPreview() {
    L.initialize(AppLanguage.Russian)
    AprilTagTheme {
        Scaffold { padding ->
            Surface(modifier = Modifier.padding(padding)) {
                ColumnPreviewFull()
            }
        }
    }
}

@Composable
private fun ColumnPreviewFull() {
    androidx.compose.foundation.layout.Column {
        ScannerTopBar(
            state = previewState,
            onCompact = {},
            onSettings = {},
            compactAction = true,
        )
        PrimaryStatsPanel(previewState)
        ScannerActions(
            state = previewState.copy(frameWidth = 1280, frameHeight = 720),
            onStart = {},
            onStop = {},
            onReset = {},
            onExport = {},
            onToggleVideo = {},
        )
        LiveTagList(previewState)
    }
}

@Preview(showBackground = true, heightDp = 640)
@Composable
private fun CompactHudPreview() {
    L.initialize(AppLanguage.Russian)
    AprilTagTheme(darkTheme = true) {
        androidx.compose.foundation.layout.Column {
            CompactScannerHud(previewState.copy(scanning = true), {}, {})
            CompactBottomDock(
                state = previewState.copy(scanning = true, frameWidth = 1280, frameHeight = 720),
                onStart = {},
                onStop = {},
                onReset = {},
                onExport = {},
                onToggleVideo = {},
            )
        }
    }
}

@Preview(showBackground = true)
@Composable
private fun SessionResultPreview() {
    AprilTagTheme {
        SessionResultCard(previewState, onExport = {})
    }
}
