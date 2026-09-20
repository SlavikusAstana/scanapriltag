package com.scanapriltag.ui

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.defaultMinSize
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.statusBarsPadding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.FiberManualRecord
import androidx.compose.material.icons.filled.FileDownload
import androidx.compose.material.icons.filled.Fullscreen
import androidx.compose.material.icons.filled.FullscreenExit
import androidx.compose.material.icons.filled.PlayArrow
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material.icons.filled.Stop
import androidx.compose.material.icons.filled.Videocam
import androidx.compose.material.icons.outlined.Refresh
import androidx.compose.material3.AssistChip
import androidx.compose.material3.AssistChipDefaults
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FilledTonalButton
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import com.scanapriltag.CameraFacing
import com.scanapriltag.ScannerUiState
import com.scanapriltag.ScannerViewModel
import com.scanapriltag.localization.L
import com.scanapriltag.models.LiveLine
import com.scanapriltag.services.TagFamilyCatalog
import com.scanapriltag.ui.theme.BorderSubtle
import com.scanapriltag.ui.theme.CameraBackground
import com.scanapriltag.ui.theme.CameraOverlayText
import com.scanapriltag.ui.theme.DuplicateRed
import com.scanapriltag.ui.theme.HudBackground
import com.scanapriltag.ui.theme.HudLabelStyle
import com.scanapriltag.ui.theme.IndustrialBlue
import com.scanapriltag.ui.theme.OverlayScrim
import com.scanapriltag.ui.theme.ScanGreen
import com.scanapriltag.ui.theme.StatNumberStyle

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ScannerTopBar(
    state: ScannerUiState,
    onCompact: () -> Unit,
    onSettings: () -> Unit,
    compactAction: Boolean,
) {
    TopAppBar(
        title = {
            Column {
                Text(
                    text = L.appTitle,
                    style = MaterialTheme.typography.titleMedium,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                )
                Text(
                    text = topBarSubtitle(state),
                    style = MaterialTheme.typography.labelSmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                )
            }
        },
        actions = {
            IconButton(onClick = onCompact) {
                Icon(
                    imageVector = if (compactAction) Icons.Default.Fullscreen else Icons.Default.FullscreenExit,
                    contentDescription = if (compactAction) L.s("CompactMode") else L.s("ExpandPanel"),
                )
            }
            IconButton(onClick = onSettings) {
                Icon(Icons.Default.Settings, contentDescription = L.settingsGroup)
            }
        },
        colors = TopAppBarDefaults.topAppBarColors(
            containerColor = MaterialTheme.colorScheme.surface,
            titleContentColor = MaterialTheme.colorScheme.onSurface,
        ),
    )
}

fun topBarSubtitle(state: ScannerUiState): String {
    val status = if (state.scanning) L.s("StatusScanningShort") else L.s("StatusIdle")
    val family = when {
        state.multiFamily -> L.s("TopBarMultiFamily")
        state.familyLocked -> TagFamilyCatalog.getLabel(state.selectedFamily)
        else -> L.s("TopBarAutoDetect")
    }
    return "$status · $family"
}

@Composable
fun CameraScannerPanel(
    viewModel: ScannerViewModel,
    state: ScannerUiState,
    reconnectToken: Int,
    showPerf: Boolean,
    roundedBottom: Boolean,
    statusBottomPadding: androidx.compose.ui.unit.Dp = 0.dp,
    modifier: Modifier = Modifier,
) {
    val shape = if (roundedBottom) {
        RoundedCornerShape(bottomStart = 16.dp, bottomEnd = 16.dp)
    } else {
        RoundedCornerShape(0.dp)
    }

    Box(
        modifier = modifier
            .clip(shape)
            .background(CameraBackground)
            .border(1.dp, BorderSubtle.copy(alpha = 0.35f), shape),
    ) {
        CameraPreview(
            viewModel = viewModel,
            cameraFacing = CameraFacing.Back,
            reconnectToken = reconnectToken,
            modifier = Modifier.fillMaxSize(),
        )
        TagOverlay(
            tags = state.overlayTags,
            duplicates = state.overlayDuplicates,
            autoProbe = !state.scanning && !state.familyLocked && !state.multiFamily,
            frameWidth = state.frameWidth,
            frameHeight = state.frameHeight,
            includeFamily = state.includeFamilyInLabels,
            modifier = Modifier.fillMaxSize(),
        )

        if (state.videoRecording) {
            Surface(
                modifier = Modifier
                    .align(Alignment.TopStart)
                    .padding(start = 12.dp, top = 12.dp),
                shape = RoundedCornerShape(8.dp),
                color = DuplicateRed.copy(alpha = 0.92f),
            ) {
                Text(
                    text = L.s("RecordingIndicator"),
                    modifier = Modifier.padding(horizontal = 10.dp, vertical = 6.dp),
                    style = MaterialTheme.typography.labelLarge,
                    color = Color.White,
                    fontWeight = FontWeight.Bold,
                )
            }
        }

        Box(
            modifier = Modifier
                .fillMaxWidth()
                .align(Alignment.BottomCenter)
                .background(
                    Brush.verticalGradient(
                        colors = listOf(Color.Transparent, OverlayScrim),
                    ),
                )
                .padding(start = 16.dp, end = 16.dp, top = 40.dp, bottom = 12.dp),
        ) {
            Column(
                modifier = Modifier.padding(bottom = statusBottomPadding),
                verticalArrangement = Arrangement.spacedBy(6.dp),
            ) {
                if (showPerf && state.perfText.isNotBlank()) {
                    SecondaryMetricChip(
                        label = state.perfText,
                        accent = IndustrialBlue,
                    )
                }
                if (state.statusText.isNotBlank()) {
                    Text(
                        text = state.statusText,
                        style = MaterialTheme.typography.bodySmall,
                        color = CameraOverlayText,
                        fontWeight = FontWeight.Medium,
                        maxLines = 2,
                        overflow = TextOverflow.Ellipsis,
                    )
                }
            }
        }
    }
}

@Composable
fun PrimaryStatsPanel(state: ScannerUiState) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.spacedBy(10.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Card(
            modifier = Modifier.weight(1.2f),
            colors = CardDefaults.cardColors(
                containerColor = MaterialTheme.colorScheme.primaryContainer,
            ),
            shape = RoundedCornerShape(12.dp),
        ) {
            Column(modifier = Modifier.padding(horizontal = 16.dp, vertical = 14.dp)) {
                Text(
                    text = L.s("StatRecorded"),
                    style = MaterialTheme.typography.labelMedium,
                    color = MaterialTheme.colorScheme.onPrimaryContainer,
                )
                Text(
                    text = state.recordedCount.toString(),
                    style = StatNumberStyle,
                    color = MaterialTheme.colorScheme.onPrimaryContainer,
                )
            }
        }
        Column(
            modifier = Modifier.weight(1f),
            verticalArrangement = Arrangement.spacedBy(6.dp),
        ) {
            SecondaryMetricChip(
                label = "${L.s("StatDuplicates")}: ${state.duplicateCount}",
                accent = if (state.duplicateCount > 0) DuplicateRed else MaterialTheme.colorScheme.outline,
                highlight = state.duplicateCount > 0,
            )
            SecondaryMetricChip(
                label = "${L.s("StatInFrame")}: ${state.inFrameCount}",
                accent = IndustrialBlue,
            )
            if (state.perfText.isNotBlank()) {
                val fps = state.perfText.substringBefore("  |").trim()
                SecondaryMetricChip(
                    label = fps.ifBlank { state.perfText },
                    accent = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }
        }
    }
}

@Composable
fun SecondaryMetricChip(
    label: String,
    accent: Color,
    highlight: Boolean = false,
) {
    Surface(
        shape = RoundedCornerShape(8.dp),
        color = if (highlight) {
            MaterialTheme.colorScheme.errorContainer.copy(alpha = 0.55f)
        } else {
            MaterialTheme.colorScheme.surfaceVariant
        },
        modifier = Modifier.fillMaxWidth(),
    ) {
        Row(
            modifier = Modifier.padding(horizontal = 10.dp, vertical = 8.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Box(
                modifier = Modifier
                    .size(8.dp)
                    .background(accent, RoundedCornerShape(4.dp)),
            )
            Spacer(modifier = Modifier.width(8.dp))
            Text(
                text = label,
                style = MaterialTheme.typography.labelSmall,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis,
            )
        }
    }
}

@Composable
fun ScannerActions(
    state: ScannerUiState,
    onStart: () -> Unit,
    onStop: () -> Unit,
    onReset: () -> Unit,
    onExport: () -> Unit,
    onToggleVideo: () -> Unit,
    compact: Boolean = false,
) {
    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
        if (state.scanning) {
            Button(
                onClick = onStop,
                modifier = Modifier
                    .fillMaxWidth()
                    .defaultMinSize(minHeight = 52.dp),
                colors = ButtonDefaults.buttonColors(
                    containerColor = MaterialTheme.colorScheme.error,
                    contentColor = MaterialTheme.colorScheme.onError,
                ),
            ) {
                Icon(Icons.Default.Stop, contentDescription = null)
                Spacer(modifier = Modifier.width(8.dp))
                Text(L.stop, fontWeight = FontWeight.SemiBold)
            }
        } else {
            Button(
                onClick = onStart,
                enabled = state.startEnabled,
                modifier = Modifier
                    .fillMaxWidth()
                    .defaultMinSize(minHeight = 52.dp),
                colors = ButtonDefaults.buttonColors(
                    containerColor = IndustrialBlue,
                    contentColor = Color.White,
                ),
            ) {
                Icon(Icons.Default.PlayArrow, contentDescription = null)
                Spacer(modifier = Modifier.width(8.dp))
                Text(L.start, fontWeight = FontWeight.SemiBold)
            }
        }

        OutlinedButton(
            onClick = onToggleVideo,
            enabled = state.cameraReady && state.frameWidth > 0,
            modifier = Modifier
                .fillMaxWidth()
                .defaultMinSize(minHeight = 48.dp),
            colors = if (state.videoRecording) {
                ButtonDefaults.outlinedButtonColors(
                    contentColor = DuplicateRed,
                )
            } else {
                ButtonDefaults.outlinedButtonColors()
            },
        ) {
            Icon(
                imageVector = if (state.videoRecording) Icons.Default.Stop else Icons.Default.Videocam,
                contentDescription = null,
                modifier = Modifier.size(18.dp),
            )
            Spacer(modifier = Modifier.width(8.dp))
            Text(
                text = if (state.videoRecording) L.s("StopRecording") else L.s("RecordVideo"),
                fontWeight = if (state.videoRecording) FontWeight.SemiBold else FontWeight.Normal,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis,
            )
            if (state.videoRecording) {
                Spacer(modifier = Modifier.width(8.dp))
                Icon(
                    Icons.Default.FiberManualRecord,
                    contentDescription = null,
                    tint = DuplicateRed,
                    modifier = Modifier.size(12.dp),
                )
            }
        }

        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            OutlinedButton(
                onClick = onExport,
                enabled = state.saveEnabled,
                modifier = Modifier
                    .weight(1f)
                    .defaultMinSize(minHeight = 48.dp),
            ) {
                Icon(Icons.Default.FileDownload, contentDescription = null, modifier = Modifier.size(18.dp))
                Spacer(modifier = Modifier.width(6.dp))
                Text(L.export, maxLines = 1, overflow = TextOverflow.Ellipsis)
            }
            OutlinedButton(
                onClick = onReset,
                enabled = state.cameraReady && !state.scanning,
                modifier = Modifier
                    .weight(if (compact) 0.45f else 0.55f)
                    .defaultMinSize(minHeight = 48.dp),
            ) {
                Icon(Icons.Outlined.Refresh, contentDescription = null, modifier = Modifier.size(18.dp))
                if (!compact) {
                    Spacer(modifier = Modifier.width(6.dp))
                    Text(L.reset)
                }
            }
        }
    }
}

@Composable
fun RecentTagsStrip(
    lines: List<LiveLine>,
    modifier: Modifier = Modifier,
    large: Boolean = false,
) {
    if (lines.isEmpty()) return
    Row(
        modifier = modifier.horizontalScroll(rememberScrollState()),
        horizontalArrangement = Arrangement.spacedBy(8.dp),
    ) {
        lines.takeLast(4).forEach { line ->
            TagChip(line = line, large = large)
        }
    }
}

@Composable
private fun TagChip(line: LiveLine, large: Boolean) {
    val shape = RoundedCornerShape(if (large) 10.dp else 8.dp)
    Surface(
        shape = shape,
        color = MaterialTheme.colorScheme.surfaceVariant,
        modifier = Modifier.border(
            width = if (line.duplicate) 2.dp else 1.dp,
            color = if (line.duplicate) DuplicateRed else BorderSubtle,
            shape = shape,
        ),
    ) {
        Row(
            modifier = Modifier.padding(
                horizontal = if (large) 12.dp else 8.dp,
                vertical = if (large) 10.dp else 6.dp,
            ),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            if (line.duplicate) {
                Box(
                    modifier = Modifier
                        .size(if (large) 10.dp else 8.dp)
                        .background(DuplicateRed, RoundedCornerShape(5.dp)),
                )
                Spacer(modifier = Modifier.width(8.dp))
            }
            Text(
                text = line.text.trim(),
                style = if (large) MaterialTheme.typography.bodyMedium else MaterialTheme.typography.labelSmall,
                fontWeight = if (line.duplicate) FontWeight.SemiBold else FontWeight.Normal,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis,
            )
        }
    }
}

@Composable
fun LiveTagList(state: ScannerUiState) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
        shape = RoundedCornerShape(12.dp),
    ) {
        Column(modifier = Modifier.padding(12.dp)) {
            Text(L.liveList, style = MaterialTheme.typography.titleSmall)
            HorizontalDivider(
                modifier = Modifier.padding(vertical = 8.dp),
                color = MaterialTheme.colorScheme.outlineVariant,
            )
            if (state.liveLines.isEmpty()) {
                Text(
                    text = L.s("LiveListEmpty"),
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    modifier = Modifier.padding(vertical = 20.dp),
                )
            } else {
                LazyColumn(
                    modifier = Modifier.height(120.dp),
                    verticalArrangement = Arrangement.spacedBy(2.dp),
                ) {
                    itemsIndexed(state.liveLines) { index, line ->
                        val isRecent = index >= state.liveLines.size - 3
                        LiveTagRow(line = line, highlighted = isRecent)
                    }
                }
            }
        }
    }
}

@Composable
private fun LiveTagRow(line: LiveLine, highlighted: Boolean) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .background(
                if (highlighted) MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.6f)
                else Color.Transparent,
                RoundedCornerShape(6.dp),
            )
            .padding(horizontal = 8.dp, vertical = 6.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Box(
            modifier = Modifier
                .width(3.dp)
                .height(18.dp)
                .background(
                    if (line.duplicate) DuplicateRed else ScanGreen,
                    RoundedCornerShape(2.dp),
                ),
        )
        Spacer(modifier = Modifier.width(8.dp))
        Text(
            text = line.text,
            style = MaterialTheme.typography.bodySmall,
            fontWeight = if (line.duplicate) FontWeight.SemiBold else FontWeight.Normal,
            maxLines = 1,
            overflow = TextOverflow.Ellipsis,
        )
    }
}

@Composable
fun SessionResultCard(
    state: ScannerUiState,
    onExport: () -> Unit,
) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(
            containerColor = MaterialTheme.colorScheme.surfaceVariant,
        ),
        shape = RoundedCornerShape(12.dp),
    ) {
        Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            Text(
                L.s("ResultSummary"),
                style = MaterialTheme.typography.titleSmall,
                color = MaterialTheme.colorScheme.onSurface,
            )
            ResultMetricRow(L.s("StatUnique"), state.uniqueCount.toString())
            ResultMetricRow(L.s("StatDuplicates"), state.duplicateCount.toString())
            if (state.scanDurationText.isNotBlank()) {
                ResultMetricRow(
                    L.s("ResultDurationLabel"),
                    state.scanDurationText,
                )
            }
            Spacer(modifier = Modifier.height(4.dp))
            OutlinedButton(
                onClick = onExport,
                enabled = state.saveEnabled,
                modifier = Modifier.fillMaxWidth(),
            ) {
                Icon(Icons.Default.FileDownload, contentDescription = null, modifier = Modifier.size(18.dp))
                Spacer(modifier = Modifier.width(8.dp))
                Text(L.s("ResultExportAction"))
            }
        }
    }
}

@Composable
private fun ResultMetricRow(label: String, value: String) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.SpaceBetween,
    ) {
        Text(label, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
        Text(value, style = MaterialTheme.typography.bodyMedium, fontWeight = FontWeight.SemiBold)
    }
}

@Composable
fun CompactScannerHud(
    state: ScannerUiState,
    onExpand: () -> Unit,
    onSettings: () -> Unit,
) {
    Surface(
        modifier = Modifier
            .fillMaxWidth()
            .statusBarsPadding()
            .padding(horizontal = 10.dp, vertical = 8.dp),
        shape = RoundedCornerShape(14.dp),
        color = HudBackground,
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 4.dp, vertical = 6.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            IconButton(onClick = onExpand) {
                Icon(
                    Icons.Default.FullscreenExit,
                    contentDescription = L.s("ExpandPanel"),
                    tint = CameraOverlayText,
                )
            }
            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = if (state.scanning) L.s("StatusScanningShort") else L.s("CompactMode"),
                    style = MaterialTheme.typography.labelLarge,
                    color = CameraOverlayText,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                )
                Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                    HudStat(L.s("StatRecorded"), state.recordedCount)
                    HudStat(L.s("StatDuplicates"), state.duplicateCount, warn = state.duplicateCount > 0)
                }
            }
            IconButton(onClick = onSettings, enabled = state.settingsEnabled) {
                Icon(
                    Icons.Default.Settings,
                    contentDescription = L.settingsGroup,
                    tint = CameraOverlayText.copy(alpha = if (state.settingsEnabled) 1f else 0.45f),
                )
            }
        }
    }
}

@Composable
private fun HudStat(label: String, value: Int, warn: Boolean = false) {
    Column {
        Text(
            text = label,
            style = HudLabelStyle,
            color = CameraOverlayText.copy(alpha = 0.75f),
        )
        Text(
            text = value.toString(),
            style = MaterialTheme.typography.titleMedium,
            color = if (warn) DuplicateRed else CameraOverlayText,
            fontWeight = FontWeight.Bold,
        )
    }
}

@Composable
fun CompactBottomDock(
    state: ScannerUiState,
    onStart: () -> Unit,
    onStop: () -> Unit,
    onReset: () -> Unit,
    onExport: () -> Unit,
    onToggleVideo: () -> Unit,
) {
    Surface(
        modifier = Modifier.fillMaxWidth(),
        color = MaterialTheme.colorScheme.surface,
        shadowElevation = 12.dp,
        shape = RoundedCornerShape(topStart = 18.dp, topEnd = 18.dp),
    ) {
        Column(
            modifier = Modifier
                .navigationBarsPadding()
                .padding(horizontal = 14.dp, vertical = 12.dp),
            verticalArrangement = Arrangement.spacedBy(10.dp),
        ) {
            if (state.liveLines.isNotEmpty()) {
                Text(
                    L.s("RecentTags"),
                    style = MaterialTheme.typography.labelMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
                RecentTagsStrip(lines = state.liveLines, large = true)
            }
            ScannerActions(
                state = state,
                onStart = onStart,
                onStop = onStop,
                onReset = onReset,
                onExport = onExport,
                onToggleVideo = onToggleVideo,
                compact = true,
            )
        }
    }
}

@Composable
fun FullControlPanel(
    state: ScannerUiState,
    onStart: () -> Unit,
    onStop: () -> Unit,
    onReset: () -> Unit,
    onExport: () -> Unit,
    onToggleVideo: () -> Unit,
    modifier: Modifier = Modifier,
) {
    Surface(
        modifier = modifier,
        shape = RoundedCornerShape(topStart = 16.dp, topEnd = 16.dp),
        color = MaterialTheme.colorScheme.surface,
        tonalElevation = 1.dp,
    ) {
        Column(
            modifier = Modifier
                .fillMaxSize()
                .verticalScroll(rememberScrollState())
                .padding(horizontal = 16.dp, vertical = 14.dp),
            verticalArrangement = Arrangement.spacedBy(14.dp),
        ) {
            PrimaryStatsPanel(state)
            ScannerActions(state, onStart, onStop, onReset, onExport, onToggleVideo)
            LiveTagList(state)
            AnimatedVisibility(visible = state.resultText.isNotBlank()) {
                SessionResultCard(state, onExport)
            }
            Spacer(modifier = Modifier.height(4.dp))
        }
    }
}
