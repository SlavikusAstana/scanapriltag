package com.scanapriltag

import android.app.Application
import android.media.ToneGenerator
import android.media.AudioManager
import androidx.lifecycle.AndroidViewModel
import com.scanapriltag.camera.AnnotatedVideoRecorder
import com.scanapriltag.localization.AppLanguage
import com.scanapriltag.localization.L
import com.scanapriltag.localization.LanguageSettings
import com.scanapriltag.models.DetectedTag
import com.scanapriltag.models.LiveLine
import com.scanapriltag.models.TagKey
import com.scanapriltag.models.TagLabels
import com.scanapriltag.services.DetectionEngine
import com.scanapriltag.services.ExportHelper
import com.scanapriltag.services.ScanSession
import com.scanapriltag.services.SpeedPreset
import com.scanapriltag.services.SpeedPresetSettings
import com.scanapriltag.services.TagFamilyCatalog
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import org.opencv.core.Mat
import java.util.ArrayDeque
import java.util.Date

enum class CameraFacing {
    Back,
    Front,
}

data class ScannerUiState(
    val language: AppLanguage = AppLanguage.Russian,
    val statusText: String = "",
    val perfText: String = "",
    val countText: String = "",
    val recordedCount: Int = 0,
    val uniqueCount: Int = 0,
    val inFrameCount: Int = 0,
    val duplicateCount: Int = 0,
    val resultText: String = "",
    val liveLines: List<LiveLine> = emptyList(),
    val overlayTags: List<DetectedTag> = emptyList(),
    val overlayDuplicates: Set<TagKey> = emptySet(),
    /** Show family:id on overlay / list when multi-family or mixed session. */
    val includeFamilyInLabels: Boolean = false,
    val frameWidth: Int = 0,
    val frameHeight: Int = 0,
    val selectedFamily: String = "tag36h11",
    val multiFamily: Boolean = false,
    val preset: SpeedPreset = SpeedPreset.Balanced,
    val beepOnDuplicate: Boolean = true,
    val missLimit: Int = 8,
    val scanning: Boolean = false,
    val familyLocked: Boolean = false,
    val startEnabled: Boolean = false,
    val stopEnabled: Boolean = false,
    val saveEnabled: Boolean = false,
    val settingsEnabled: Boolean = true,
    val cameraReady: Boolean = false,
    val compactMode: Boolean = false,
    val showResultDialog: String? = null,
    val showSaveMessage: String? = null,
    val showErrorMessage: String? = null,
    val title: String = L.appTitle,
    val scanDurationText: String = "",
    val exportSnackbarMessage: String? = null,
    val videoRecording: Boolean = false,
)

class ScannerViewModel(application: Application) : AndroidViewModel(application) {
    private val session = ScanSession()
    private val detector = DetectionEngine()
    private val toneGenerator = ToneGenerator(AudioManager.STREAM_NOTIFICATION, 80)

    private var frameIndex = 0
    private var probeFamilyIndex = 0
    private var probeCandidateFamily: String? = null
    private var probeCandidateId = -1
    private var probeCandidateStreak = 0
    private val frameTimes = ArrayDeque<Double>(31)
    private var scanStartTimeMs: Long = 0L
    private var lastFps: Double = 0.0
    private var lastDetectMs: Double = 0.0
    private var lastAutoDetectedTagId: Int? = null
    private var lastDuplicateLabel: String? = null
    private var cameraErrorKey: String? = null
    private val annotatedRecorder = AnnotatedVideoRecorder()
    private var pendingVideoFilename: String? = null

    private val _uiState = MutableStateFlow(ScannerUiState())
    val uiState: StateFlow<ScannerUiState> = _uiState.asStateFlow()

    val sessionRef: ScanSession get() = session

    fun toggleVideoRecording() {
        if (_uiState.value.videoRecording) {
            stopVideoRecording()
        } else {
            requestStartVideoRecording()
        }
    }

    fun requestStartVideoRecording() {
        if (_uiState.value.videoRecording) return
        val state = _uiState.value
        when (
            val result = annotatedRecorder.start(
                context = getApplication(),
                frameWidth = state.frameWidth,
                frameHeight = state.frameHeight,
            )
        ) {
            is AnnotatedVideoRecorder.StartResult.Started -> {
                pendingVideoFilename = result.filename
                _uiState.update { it.copy(videoRecording = true) }
            }
            AnnotatedVideoRecorder.StartResult.MicPermissionRequired -> {
                _uiState.update {
                    it.copy(showErrorMessage = L.s("MicPermissionRequired"))
                }
            }
            AnnotatedVideoRecorder.StartResult.StoragePermissionRequired -> {
                _uiState.update {
                    it.copy(showErrorMessage = L.s("StoragePermissionRequired"))
                }
            }
            AnnotatedVideoRecorder.StartResult.NotReady,
            AnnotatedVideoRecorder.StartResult.AlreadyRecording,
            -> {
                _uiState.update {
                    it.copy(showErrorMessage = L.s("VideoNotReady"))
                }
            }
            is AnnotatedVideoRecorder.StartResult.Failed -> {
                _uiState.update {
                    it.copy(showErrorMessage = L.f("VideoSaveFailed", result.message))
                }
            }
        }
    }

    fun startVideoRecording() {
        requestStartVideoRecording()
    }

    fun stopVideoRecording() {
        if (!_uiState.value.videoRecording && !annotatedRecorder.isRecording) return
        when (val result = annotatedRecorder.stop(getApplication())) {
            is AnnotatedVideoRecorder.StopResult.Saved -> {
                pendingVideoFilename = null
                _uiState.update {
                    it.copy(
                        videoRecording = false,
                        exportSnackbarMessage = L.f("VideoSavedSnackbar", result.filename),
                    )
                }
            }
            AnnotatedVideoRecorder.StopResult.NotRecording -> {
                pendingVideoFilename = null
                _uiState.update { it.copy(videoRecording = false) }
            }
            is AnnotatedVideoRecorder.StopResult.Failed -> {
                pendingVideoFilename = null
                _uiState.update {
                    it.copy(
                        videoRecording = false,
                        showErrorMessage = L.f("VideoSaveFailed", result.message),
                    )
                }
            }
        }
    }

    fun onMicPermissionDenied() {
        _uiState.update {
            it.copy(showErrorMessage = L.s("MicPermissionDenied"))
        }
    }

    fun onStoragePermissionDenied() {
        _uiState.update {
            it.copy(showErrorMessage = L.s("StoragePermissionDenied"))
        }
    }

    init {
        val prefs = LanguageSettings.loadAll(application)
        L.initialize(prefs.language)
        _uiState.update {
            it.copy(
                language = prefs.language,
                // Family / multi-family always start unlocked for auto-detect.
                selectedFamily = "tag36h11",
                multiFamily = false,
                familyLocked = false,
                preset = prefs.preset,
                beepOnDuplicate = prefs.beepOnDuplicate,
                missLimit = prefs.missLimit,
                statusText = L.s("CameraConnecting"),
            )
        }
        applyDetectorConfig()
    }

    private val autoProbeMode: Boolean
        get() {
            val s = _uiState.value
            return !s.scanning && !s.familyLocked && !s.multiFamily
        }

    private fun activeFamilies(): List<String> =
        if (_uiState.value.multiFamily) TagFamilyCatalog.multiFamilies
        else listOf(_uiState.value.selectedFamily)

    fun familiesDescription(): String = activeFamilies().joinToString(", ")

    fun onCameraReady() {
        cameraErrorKey = null
        _uiState.update {
            it.copy(
                cameraReady = true,
                startEnabled = true,
                statusText = L.s("CameraReady"),
            )
        }
        applyDetectorConfig()
    }

    fun onCameraError(message: String) {
        cameraErrorKey = if (message == L.s("PermissionRequired") || message.contains("permission", ignoreCase = true)) {
            "PermissionRequired"
        } else {
            null
        }
        _uiState.update {
            it.copy(
                cameraReady = false,
                startEnabled = false,
                statusText = cameraErrorKey?.let { key -> L.s(key) } ?: message,
            )
        }
    }

    fun onFrame(bgr: Mat, width: Int, height: Int) {
        val frameStart = System.nanoTime()
        frameIndex++

        val (tags, detectMs, _) = detector.snapshot()
        val recording = annotatedRecorder.isRecording
        val state = _uiState.value
        val includeFamily = state.multiFamily ||
            TagLabels.sessionNeedsFamily(session.records, multiFamily = false)
        val dupSnapshot = session.duplicates

        // While recording: feed video first, then throttle detection so encode keeps up with audio.
        if (recording) {
            annotatedRecorder.offerFrame(
                bgr = bgr,
                tags = tags,
                duplicates = dupSnapshot,
                autoProbe = autoProbeMode,
                includeFamily = includeFamily,
            )
            if (frameIndex % RECORDING_DETECT_STRIDE == 0) {
                requestDetection(bgr, force = true)
            }
        } else {
            requestDetection(bgr, force = false)
        }

        var liveLines = state.liveLines
        var statusText = state.statusText
        if (state.scanning) {
            val added = session.processDetections(tags, state.missLimit)
            if (added.isNotEmpty()) {
                val newLines = liveLines.toMutableList()
                for (record in added) {
                    val label = record.displayLabel(includeFamily)
                    val suffix = if (record.duplicate) L.s("DuplicateMark") else ""
                    newLines.add(LiveLine("${session.records.size}. $label$suffix", record.duplicate))
                    if (record.duplicate) {
                        statusText = L.f("StatusDuplicate", label)
                        lastDuplicateLabel = label
                        if (state.beepOnDuplicate) {
                            toneGenerator.startTone(ToneGenerator.TONE_PROP_BEEP, 150)
                        }
                    }
                }
                liveLines = newLines
            }
        } else {
            session.clearTracking()
            tryAutoSelectFamily(tags)
        }

        val unique = session.records.map { TagKey(it.family, it.id) }.distinct().size
        val recordsSize = session.records.size
        val dupCount = session.duplicates.size
        val frameMs = (System.nanoTime() - frameStart) / 1_000_000.0
        val perfText = nextPerfText(frameMs, detectMs)

        _uiState.update {
            it.copy(
                frameWidth = width,
                frameHeight = height,
                liveLines = liveLines,
                statusText = statusText,
                overlayTags = tags,
                overlayDuplicates = session.duplicates,
                includeFamilyInLabels = includeFamily || it.multiFamily,
                recordedCount = recordsSize,
                uniqueCount = unique,
                inFrameCount = tags.size,
                duplicateCount = dupCount,
                countText = L.f(
                    "CountLine",
                    recordsSize,
                    unique,
                    tags.size,
                    dupCount,
                ),
                perfText = perfText,
            )
        }
        bgr.release()
    }

    private fun requestDetection(frame: Mat, force: Boolean) {
        if (autoProbeMode) {
            if (!force && frameIndex % PROBE_STRIDE != 0) return
            val family = TagFamilyCatalog.probePriority[probeFamilyIndex % TagFamilyCatalog.probePriority.size]
            if (detector.trySubmit(frame, PROBE_WIDTH, listOf(family), probeMode = true)) {
                probeFamilyIndex++
            }
            return
        }

        val settings = SpeedPresetSettings.get(_uiState.value.preset)
        if (!force && frameIndex % settings.stride != 0 && !_uiState.value.scanning) return
        // During scan+record, still respect a light stride unless forced by recording path.
        if (!force && annotatedRecorder.isRecording && frameIndex % RECORDING_DETECT_STRIDE != 0) return

        detector.trySubmit(frame, settings.detectWidth, activeFamilies(), probeMode = false)
    }

    private fun tryAutoSelectFamily(tags: List<DetectedTag>) {
        if (!autoProbeMode || tags.isEmpty()) return

        val tag = tags[0]
        if (probeCandidateFamily == tag.family && probeCandidateId == tag.id) {
            probeCandidateStreak++
        } else {
            probeCandidateFamily = tag.family
            probeCandidateId = tag.id
            probeCandidateStreak = 1
        }

        if (probeCandidateStreak < 2) return

        lastAutoDetectedTagId = tag.id
        _uiState.update {
            it.copy(
                selectedFamily = tag.family,
                familyLocked = true,
                statusText = L.f(
                    "StatusFamilyDetected",
                    TagFamilyCatalog.getLabel(tag.family),
                    tag.id,
                ),
            )
        }
        probeFamilyIndex = 0
        applyDetectorConfig()
    }

    private fun updateCount(inFrame: Int) {
        val unique = session.records.map { TagKey(it.family, it.id) }.distinct().size
        _uiState.update {
            it.copy(
                recordedCount = session.records.size,
                uniqueCount = unique,
                inFrameCount = inFrame,
                duplicateCount = session.duplicates.size,
                countText = L.f(
                    "CountLine",
                    session.records.size,
                    unique,
                    inFrame,
                    session.duplicates.size,
                ),
            )
        }
    }

    private fun trackFps(frameMs: Double, detectMs: Double) {
        nextPerfText(frameMs, detectMs)
        _uiState.update {
            it.copy(perfText = buildPerfText())
        }
    }

    private fun nextPerfText(frameMs: Double, detectMs: Double): String {
        frameTimes.addLast(frameMs.coerceAtLeast(1.0))
        while (frameTimes.size > 30) frameTimes.removeFirst()
        val avg = frameTimes.average()
        lastFps = if (avg > 0) 1000.0 / avg else 0.0
        lastDetectMs = detectMs
        return buildPerfText()
    }

    private fun buildPerfText(): String {
        val presetLabel = SpeedPresetSettings.label(_uiState.value.preset)
        val autoSuffix = if (autoProbeMode) "  |  ${L.s("PerfAuto")}" else ""
        return L.f("PerfLine", lastFps, lastDetectMs.toInt(), presetLabel) + autoSuffix
    }

    private fun buildTitle(): String =
        if (autoProbeMode) {
            L.s("TitleAutoDetect")
        } else {
            "${L.appTitle} - ${activeFamilies().joinToString("+") { f -> f.removePrefix("tag") }}"
        }

    private fun buildStatusText(): String {
        val state = _uiState.value
        when {
            !state.cameraReady -> {
                cameraErrorKey?.let { return L.s(it) }
                return if (state.startEnabled) L.s("CameraReady") else L.s("CameraConnecting")
            }
            state.scanning -> {
                lastDuplicateLabel?.let { return L.f("StatusDuplicate", it) }
                return L.s("StatusScanning")
            }
            state.resultText.isNotBlank() -> {
                return if (session.duplicates.isNotEmpty()) {
                    L.f("StatusDoneDup", session.duplicates.joinToString(", ") { it.id.toString() })
                } else {
                    L.s("StatusDoneNoDup")
                }
            }
            state.multiFamily -> return L.s("StatusMultiFamily")
            state.familyLocked -> {
                val familyLabel = TagFamilyCatalog.getLabel(state.selectedFamily)
                val tagId = lastAutoDetectedTagId
                return if (tagId != null) {
                    L.f("StatusFamilyDetected", familyLabel, tagId)
                } else {
                    L.f("StatusFamilyManual", familyLabel)
                }
            }
            else -> return L.s("StatusShowTag")
        }
    }

    private fun buildCountText(inFrame: Int): String {
        val unique = session.records.map { TagKey(it.family, it.id) }.distinct().size
        return L.f(
            "CountLine",
            session.records.size,
            unique,
            inFrame,
            session.duplicates.size,
        )
    }

    fun applyLocalizedTexts(inFrame: Int = _uiState.value.inFrameCount) {
        _uiState.update { buildLocalizedState(it, inFrame) }
    }

    private fun buildLocalizedState(base: ScannerUiState, inFrame: Int = base.inFrameCount): ScannerUiState {
        val unique = session.records.map { TagKey(it.family, it.id) }.distinct().size
        val perfText = if (lastFps > 0.0 || lastDetectMs > 0.0 || base.perfText.isNotBlank()) {
            buildPerfText()
        } else {
            base.perfText
        }
        return base.copy(
            title = buildTitle(),
            statusText = buildStatusText(),
            perfText = perfText,
            countText = buildCountText(inFrame),
            recordedCount = session.records.size,
            uniqueCount = unique,
            duplicateCount = session.duplicates.size,
            liveLines = rebuildLiveLines(),
            resultText = if (base.resultText.isNotBlank()) {
                ExportHelper.buildTextReport(session, familiesDescription(), Date())
            } else {
                ""
            },
            showResultDialog = if (base.showResultDialog != null) buildStatusText() else null,
        )
    }

    fun startScan() {
        val state = _uiState.value
        var locked = state.familyLocked
        if (!locked && !state.multiFamily) {
            locked = true
        }
        session.clearTracking()
        scanStartTimeMs = System.currentTimeMillis()
        lastDuplicateLabel = null
        _uiState.update {
            it.copy(
                scanning = true,
                compactMode = true,
                familyLocked = locked,
                startEnabled = false,
                stopEnabled = true,
                saveEnabled = false,
                settingsEnabled = false,
                statusText = L.s("StatusScanning"),
                scanDurationText = "",
                resultText = "",
            )
        }
        applyDetectorConfig()
    }

    fun stopScan() {
        session.clearTracking()
        val report = ExportHelper.buildTextReport(session, familiesDescription(), Date())
        val durationText = formatScanDuration(System.currentTimeMillis() - scanStartTimeMs)
        val summary = if (session.duplicates.isNotEmpty()) {
            L.f("StatusDoneDup", session.duplicates.joinToString(", ") { it.id.toString() })
        } else {
            L.s("StatusDoneNoDup")
        }
        _uiState.update {
            it.copy(
                scanning = false,
                compactMode = false,
                startEnabled = true,
                stopEnabled = false,
                saveEnabled = session.records.isNotEmpty(),
                settingsEnabled = true,
                resultText = report,
                statusText = summary,
                scanDurationText = durationText,
                showResultDialog = summary,
            )
        }
        scanStartTimeMs = 0L
    }

    fun toggleCompactMode(force: Boolean? = null) {
        _uiState.update {
            it.copy(compactMode = force ?: !it.compactMode)
        }
    }

    fun dismissResultDialog() {
        _uiState.update { it.copy(showResultDialog = null) }
    }

    fun resetScan() {
        session.reset()
        probeFamilyIndex = 0
        probeCandidateStreak = 0
        lastAutoDetectedTagId = null
        lastDuplicateLabel = null
        _uiState.update {
            it.copy(
                scanning = false,
                familyLocked = false,
                liveLines = emptyList(),
                resultText = "",
                scanDurationText = "",
                startEnabled = true,
                stopEnabled = false,
                saveEnabled = false,
                settingsEnabled = true,
                statusText = L.s("StatusShowTag"),
            )
        }
        updateCount(0)
        applyDetectorConfig()
    }


    fun onSaveSuccess(filename: String) {
        val message = L.f("ExportSuccessSnackbar", filename)
        _uiState.update {
            it.copy(
                showSaveMessage = L.f("SaveSuccess", filename),
                exportSnackbarMessage = message,
            )
        }
    }

    fun dismissExportSnackbar() {
        _uiState.update { it.copy(exportSnackbarMessage = null) }
    }

    fun onSaveFailed(message: String) {
        _uiState.update { it.copy(showErrorMessage = L.f("SaveFailed", message)) }
    }

    fun dismissSaveMessage() {
        _uiState.update { it.copy(showSaveMessage = null) }
    }

    fun dismissErrorMessage() {
        _uiState.update { it.copy(showErrorMessage = null) }
    }

    fun setLanguage(language: AppLanguage) {
        if (_uiState.value.language == language) return
        L.setLanguage(language, getApplication(), persist = true)
        _uiState.update { buildLocalizedState(it.copy(language = language)) }
    }

    fun setSelectedFamily(family: String) {
        if (_uiState.value.scanning) return
        lastAutoDetectedTagId = null
        _uiState.update {
            it.copy(
                selectedFamily = family,
                familyLocked = true,
                statusText = L.f("StatusFamilyManual", TagFamilyCatalog.getLabel(family)),
            )
        }
        applyDetectorConfig()
    }

    fun setMultiFamily(enabled: Boolean) {
        if (_uiState.value.scanning) return
        _uiState.update {
            it.copy(
                multiFamily = enabled,
                familyLocked = enabled,
                statusText = if (enabled) L.s("StatusMultiFamily") else L.s("StatusShowTag"),
            )
        }
        if (!enabled) {
            _uiState.update { it.copy(familyLocked = false) }
        }
        applyDetectorConfig()
    }

    fun setPreset(preset: SpeedPreset) {
        if (_uiState.value.scanning) return
        _uiState.update { it.copy(preset = preset) }
        applyDetectorConfig()
        persistScannerPrefs()
    }

    fun setBeepOnDuplicate(enabled: Boolean) {
        if (_uiState.value.scanning) return
        _uiState.update { it.copy(beepOnDuplicate = enabled) }
        persistScannerPrefs()
    }

    fun setMissLimit(limit: Int) {
        if (_uiState.value.scanning) return
        val clamped = limit.coerceIn(1, 99)
        _uiState.update { it.copy(missLimit = clamped) }
        persistScannerPrefs()
    }

    private fun persistScannerPrefs() {
        val state = _uiState.value
        LanguageSettings.saveScanner(
            getApplication(),
            preset = state.preset,
            beepOnDuplicate = state.beepOnDuplicate,
            missLimit = state.missLimit,
        )
    }

    fun reconnectCamera() {
        if (annotatedRecorder.isRecording) {
            stopVideoRecording()
        }
        cameraErrorKey = null
        _uiState.update {
            it.copy(
                cameraReady = false,
                startEnabled = false,
                videoRecording = false,
                statusText = L.s("CameraConnecting"),
            )
        }
    }

    private fun applyDetectorConfig() {
        val settings = SpeedPresetSettings.get(_uiState.value.preset)
        detector.configure(settings.decimate)
        detector.bumpCache()
        _uiState.update { it.copy(title = buildTitle()) }
    }

    private fun rebuildLiveLines(): List<LiveLine> =
        session.records.mapIndexed { index, record ->
            val suffix = if (record.duplicate) L.s("DuplicateMark") else ""
            LiveLine("${index + 1}. ${record.label}$suffix", record.duplicate)
        }

    private fun refreshLocalizedStaticText() {
        applyLocalizedTexts()
    }

    private fun formatScanDuration(durationMs: Long): String {
        if (durationMs <= 0L) return "—"
        val totalSeconds = durationMs / 1000
        val minutes = totalSeconds / 60
        val seconds = totalSeconds % 60
        return if (minutes > 0) {
            "%d:%02d".format(minutes, seconds)
        } else {
            "${seconds}s"
        }
    }

    override fun onCleared() {
        if (annotatedRecorder.isRecording) {
            runCatching { annotatedRecorder.stop(getApplication()) }
        }
        detector.close()
        toneGenerator.release()
        super.onCleared()
    }

    companion object {
        private const val PROBE_WIDTH = 560
        private const val PROBE_STRIDE = 4
        /** While recording, run detection less often so encode keeps real-time with audio. */
        private const val RECORDING_DETECT_STRIDE = 3
    }
}
