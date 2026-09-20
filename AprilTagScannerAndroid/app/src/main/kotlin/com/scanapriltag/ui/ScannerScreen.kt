package com.scanapriltag.ui

import android.Manifest
import android.content.pm.PackageManager
import android.os.Build
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.asPaddingValues
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.navigationBars
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import androidx.core.content.ContextCompat
import com.scanapriltag.ScannerUiState
import com.scanapriltag.ScannerViewModel
import com.scanapriltag.localization.L

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ScannerScreen(
    viewModel: ScannerViewModel,
    onSaveRequest: () -> Unit,
) {
    val state by viewModel.uiState.collectAsState()
    var reconnectToken by remember { mutableIntStateOf(0) }
    var showSettings by remember { mutableStateOf(false) }
    val snackbarHostState = remember { SnackbarHostState() }
    val context = LocalContext.current

    val videoPermissionLauncher = rememberLauncherForActivityResult(
        ActivityResultContracts.RequestMultiplePermissions(),
    ) { granted ->
        val micOk = granted[Manifest.permission.RECORD_AUDIO] != false &&
            ContextCompat.checkSelfPermission(context, Manifest.permission.RECORD_AUDIO) ==
            PackageManager.PERMISSION_GRANTED
        val storageNeeded = Build.VERSION.SDK_INT < Build.VERSION_CODES.Q
        val storageOk = !storageNeeded ||
            ContextCompat.checkSelfPermission(context, Manifest.permission.WRITE_EXTERNAL_STORAGE) ==
            PackageManager.PERMISSION_GRANTED
        when {
            !micOk -> viewModel.onMicPermissionDenied()
            !storageOk -> viewModel.onStoragePermissionDenied()
            else -> viewModel.requestStartVideoRecording()
        }
    }

    fun onToggleVideo() {
        if (state.videoRecording) {
            viewModel.stopVideoRecording()
            return
        }
        val need = mutableListOf<String>()
        if (ContextCompat.checkSelfPermission(context, Manifest.permission.RECORD_AUDIO) !=
            PackageManager.PERMISSION_GRANTED
        ) {
            need += Manifest.permission.RECORD_AUDIO
        }
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.Q &&
            ContextCompat.checkSelfPermission(context, Manifest.permission.WRITE_EXTERNAL_STORAGE) !=
            PackageManager.PERMISSION_GRANTED
        ) {
            need += Manifest.permission.WRITE_EXTERNAL_STORAGE
        }
        if (need.isEmpty()) {
            viewModel.requestStartVideoRecording()
        } else {
            videoPermissionLauncher.launch(need.toTypedArray())
        }
    }

    LocalizedUi {
        LaunchedEffect(state.exportSnackbarMessage) {
            val message = state.exportSnackbarMessage ?: return@LaunchedEffect
            snackbarHostState.showSnackbar(message)
            viewModel.dismissExportSnackbar()
        }

        Dialogs(state, viewModel)

        if (showSettings) {
            SettingsBottomSheet(
                state = state,
                onDismiss = { showSettings = false },
                onLanguageChange = viewModel::setLanguage,
                onFamilyChange = viewModel::setSelectedFamily,
                onMultiFamilyChange = viewModel::setMultiFamily,
                onPresetChange = viewModel::setPreset,
                onBeepChange = viewModel::setBeepOnDuplicate,
                onMissChange = viewModel::setMissLimit,
                onReconnect = {
                    viewModel.reconnectCamera()
                    reconnectToken++
                },
            )
        }

        Scaffold(
            snackbarHost = { SnackbarHost(snackbarHostState) },
            containerColor = MaterialTheme.colorScheme.background,
        ) { padding ->
            ScannerLayout(
                state = state,
                viewModel = viewModel,
                reconnectToken = reconnectToken,
                modifier = Modifier
                    .fillMaxSize()
                    .padding(padding),
                onSave = onSaveRequest,
                onCompact = { viewModel.toggleCompactMode(force = true) },
                onExpand = { viewModel.toggleCompactMode(force = false) },
                onSettings = { showSettings = true },
                onStart = viewModel::startScan,
                onStop = viewModel::stopScan,
                onReset = viewModel::resetScan,
                onToggleVideo = ::onToggleVideo,
            )
        }
    }
}

/**
 * Single camera instance for the whole screen — switching compact/full must not
 * dispose [CameraPreview] (that unbinds CameraX and blanks the preview).
 */
@Composable
private fun ScannerLayout(
    state: ScannerUiState,
    viewModel: ScannerViewModel,
    reconnectToken: Int,
    modifier: Modifier = Modifier,
    onSave: () -> Unit,
    onCompact: () -> Unit,
    onExpand: () -> Unit,
    onSettings: () -> Unit,
    onStart: () -> Unit,
    onStop: () -> Unit,
    onReset: () -> Unit,
    onToggleVideo: () -> Unit,
) {
    val compact = state.compactMode
    val dockLift = 140.dp + WindowInsets.navigationBars.asPaddingValues().calculateBottomPadding()

    Box(modifier = modifier) {
        Column(modifier = Modifier.fillMaxSize()) {
            if (!compact) {
                ScannerTopBar(
                    state = state,
                    onCompact = onCompact,
                    onSettings = onSettings,
                    compactAction = true,
                )
            }

            CameraScannerPanel(
                viewModel = viewModel,
                state = state,
                reconnectToken = reconnectToken,
                showPerf = !compact,
                roundedBottom = !compact,
                statusBottomPadding = if (compact) dockLift else 0.dp,
                modifier = Modifier
                    .fillMaxWidth()
                    .weight(if (compact) 1f else 0.63f),
            )

            if (!compact) {
                FullControlPanel(
                    state = state,
                    onStart = onStart,
                    onStop = onStop,
                    onReset = onReset,
                    onExport = onSave,
                    onToggleVideo = onToggleVideo,
                    modifier = Modifier
                        .fillMaxWidth()
                        .weight(0.37f),
                )
            }
        }

        if (compact) {
            Box(
                modifier = Modifier
                    .align(Alignment.TopCenter)
                    .fillMaxWidth(),
            ) {
                CompactScannerHud(state, onExpand, onSettings)
            }
            Box(
                modifier = Modifier
                    .align(Alignment.BottomCenter)
                    .fillMaxWidth(),
            ) {
                CompactBottomDock(
                    state = state,
                    onStart = onStart,
                    onStop = onStop,
                    onReset = onReset,
                    onExport = onSave,
                    onToggleVideo = onToggleVideo,
                )
            }
        }
    }
}

@Composable
private fun Dialogs(
    state: ScannerUiState,
    viewModel: ScannerViewModel,
) {
    state.showResultDialog?.let { message ->
        AlertDialog(
            onDismissRequest = viewModel::dismissResultDialog,
            title = { Text(L.resultTitle) },
            text = { Text(message) },
            confirmButton = {
                TextButton(onClick = viewModel::dismissResultDialog) { Text(L.s("Ok")) }
            },
        )
    }
    state.showErrorMessage?.let { message ->
        AlertDialog(
            onDismissRequest = viewModel::dismissErrorMessage,
            title = { Text(L.errorTitle) },
            text = { Text(message) },
            confirmButton = {
                TextButton(onClick = viewModel::dismissErrorMessage) { Text(L.s("Ok")) }
            },
        )
    }
}
