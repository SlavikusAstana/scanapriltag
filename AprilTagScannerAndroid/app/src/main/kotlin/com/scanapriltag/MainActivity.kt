package com.scanapriltag

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.activity.result.contract.ActivityResultContracts
import androidx.lifecycle.viewmodel.compose.viewModel
import com.scanapriltag.services.ExportHelper
import com.scanapriltag.ui.ScannerScreen
import com.scanapriltag.ui.theme.AprilTagTheme
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

class MainActivity : ComponentActivity() {
    private var viewModel: ScannerViewModel? = null

    private val saveLauncher = registerForActivityResult(
        ActivityResultContracts.CreateDocument("*/*"),
    ) { uri ->
        val vm = viewModel ?: return@registerForActivityResult
        if (uri == null) return@registerForActivityResult

        try {
            val filename = uri.lastPathSegment ?: "apriltag_scan.txt"
            val ext = ExportHelper.extensionForFilename(filename)
            contentResolver.openOutputStream(uri)?.use { stream ->
                ExportHelper.writeTo(stream, vm.sessionRef, vm.familiesDescription(), ext)
            } ?: throw IllegalStateException("No output stream")
            vm.onSaveSuccess(filename)
        } catch (ex: Exception) {
            vm.onSaveFailed(ex.message ?: ex.toString())
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()

        setContent {
            val vm: ScannerViewModel = viewModel()
            viewModel = vm

            AprilTagTheme {
                ScannerScreen(
                    viewModel = vm,
                    onSaveRequest = { launchSave() },
                )
            }
        }
    }

    private fun launchSave() {
        val timestamp = SimpleDateFormat("yyyyMMdd_HHmmss", Locale.US).format(Date())
        saveLauncher.launch("apriltag_scan_$timestamp.txt")
    }
}
