package com.scanapriltag.ui

import android.Manifest
import android.content.pm.PackageManager
import android.util.Size
import android.view.Surface
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.camera.core.CameraSelector
import androidx.camera.core.ImageAnalysis
import androidx.camera.core.Preview
import androidx.camera.core.resolutionselector.ResolutionSelector
import androidx.camera.core.resolutionselector.ResolutionStrategy
import androidx.camera.lifecycle.ProcessCameraProvider
import androidx.camera.view.PreviewView
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.viewinterop.AndroidView
import androidx.core.content.ContextCompat
import androidx.lifecycle.compose.LocalLifecycleOwner
import com.scanapriltag.CameraFacing
import com.scanapriltag.ScannerViewModel
import com.scanapriltag.camera.FrameOrientation
import com.scanapriltag.localization.L
import java.util.concurrent.Executors

@Composable
fun CameraPreview(
    viewModel: ScannerViewModel,
    cameraFacing: CameraFacing,
    reconnectToken: Int,
    modifier: Modifier = Modifier,
) {
    val context = LocalContext.current
    val lifecycleOwner = LocalLifecycleOwner.current
    val executor = remember { Executors.newSingleThreadExecutor() }
    var permissionGranted by remember {
        mutableIntStateOf(
            if (ContextCompat.checkSelfPermission(context, Manifest.permission.CAMERA) == PackageManager.PERMISSION_GRANTED) 1 else 0,
        )
    }

    val permissionLauncher = rememberLauncherForActivityResult(
        ActivityResultContracts.RequestPermission(),
    ) { granted ->
        if (granted) permissionGranted++
        else viewModel.onCameraError(L.s("PermissionRequired"))
    }

    DisposableEffect(Unit) {
        if (permissionGranted == 0) {
            permissionLauncher.launch(Manifest.permission.CAMERA)
        }
        onDispose { executor.shutdown() }
    }

    val previewView = remember {
        PreviewView(context).apply {
            implementationMode = PreviewView.ImplementationMode.COMPATIBLE
            scaleType = PreviewView.ScaleType.FIT_CENTER
        }
    }

    DisposableEffect(cameraFacing, reconnectToken, permissionGranted) {
        if (permissionGranted == 0) {
            return@DisposableEffect onDispose { }
        }

        val cameraProviderFuture = ProcessCameraProvider.getInstance(context)
        val listener = Runnable {
            val cameraProvider = cameraProviderFuture.get()
            cameraProvider.unbindAll()

            val selector = when (cameraFacing) {
                CameraFacing.Back -> CameraSelector.DEFAULT_BACK_CAMERA
                CameraFacing.Front -> CameraSelector.DEFAULT_FRONT_CAMERA
            }

            val mirrorHorizontal = cameraFacing == CameraFacing.Front
            val targetRotation = previewView.display?.rotation ?: Surface.ROTATION_0

            val resolutionSelector = ResolutionSelector.Builder()
                .setResolutionStrategy(
                    ResolutionStrategy(
                        Size(1280, 720),
                        ResolutionStrategy.FALLBACK_RULE_CLOSEST_HIGHER_THEN_LOWER,
                    ),
                )
                .build()

            val preview = Preview.Builder()
                .setResolutionSelector(resolutionSelector)
                .setTargetRotation(targetRotation)
                .build()
                .also { it.surfaceProvider = previewView.surfaceProvider }

            val analysis = ImageAnalysis.Builder()
                .setResolutionSelector(resolutionSelector)
                .setTargetRotation(targetRotation)
                .setBackpressureStrategy(ImageAnalysis.STRATEGY_KEEP_ONLY_LATEST)
                .build()

            analysis.setAnalyzer(executor) { imageProxy ->
                try {
                    val frame = FrameOrientation.toDisplayOriented(imageProxy, mirrorHorizontal)
                    if (frame != null) {
                        viewModel.onFrame(
                            frame.bgr,
                            frame.width,
                            frame.height,
                        )
                    }
                } finally {
                    imageProxy.close()
                }
            }

            try {
                cameraProvider.bindToLifecycle(
                    lifecycleOwner,
                    selector,
                    preview,
                    analysis,
                )
                viewModel.onCameraReady()
            } catch (ex: Exception) {
                viewModel.onCameraError(ex.message ?: ex.toString())
            }
        }

        cameraProviderFuture.addListener(listener, ContextCompat.getMainExecutor(context))

        onDispose {
            runCatching {
                cameraProviderFuture.get().unbindAll()
            }
        }
    }

    AndroidView(
        modifier = modifier,
        factory = { previewView },
    )
}
