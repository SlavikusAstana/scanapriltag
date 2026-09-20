package com.scanapriltag.camera

import android.Manifest
import android.content.ContentValues
import android.content.Context
import android.content.pm.PackageManager
import android.graphics.Bitmap
import android.media.AudioFormat
import android.media.AudioRecord
import android.media.MediaCodec
import android.media.MediaCodecInfo
import android.media.MediaFormat
import android.media.MediaMuxer
import android.media.MediaRecorder
import android.net.Uri
import android.os.Build
import android.os.ParcelFileDescriptor
import android.provider.MediaStore
import android.view.Surface
import androidx.core.content.ContextCompat
import com.scanapriltag.models.DetectedTag
import com.scanapriltag.models.TagKey
import org.opencv.android.Utils
import org.opencv.core.Mat
import org.opencv.core.Size
import org.opencv.imgproc.Imgproc
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import java.util.concurrent.LinkedBlockingQueue
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicBoolean
import java.util.concurrent.atomic.AtomicReference

/**
 * Records annotated camera frames + mic audio.
 *
 * A/V sync: both tracks use the same wall-clock timeline from [recordingStartNs].
 * Video PTS is the capture time of each frame (not a fake fixed FPS counter).
 */
class AnnotatedVideoRecorder {
    private data class FrameJob(
        val mat: Mat,
        val tags: List<DetectedTag>,
        val duplicates: Set<TagKey>,
        val autoProbe: Boolean,
        val includeFamily: Boolean,
        val capturePtsUs: Long,
        val poison: Boolean = false,
    )

    private val running = AtomicBoolean(false)
    private val frameQueue = LinkedBlockingQueue<FrameJob>(4)
    /** PTS of frames posted to the encoder surface, consumed when muxing video samples. */
    private val postedPtsQueue = LinkedBlockingQueue<Long>(64)
    private val outputUri = AtomicReference<Uri?>(null)
    private val outputName = AtomicReference<String?>(null)

    @Volatile private var videoEncoder: MediaCodec? = null
    @Volatile private var audioEncoder: MediaCodec? = null
    @Volatile private var muxer: MediaMuxer? = null
    @Volatile private var inputSurface: Surface? = null
    @Volatile private var audioRecord: AudioRecord? = null
    @Volatile private var outputPfd: ParcelFileDescriptor? = null
    @Volatile private var videoTrack = -1
    @Volatile private var audioTrack = -1
    @Volatile private var muxerStarted = false
    private val muxerLock = Any()

    private var videoThread: Thread? = null
    private var audioThread: Thread? = null
    private var encodeWidth = 0
    private var encodeHeight = 0
    @Volatile private var recordingStartNs = 0L
    private var lastOfferedPtsUs = -1L
    private var lastMuxVideoPtsUs = -1L
    private var lastMuxAudioPtsUs = -1L
    private var reusableBitmap: Bitmap? = null

    val isRecording: Boolean get() = running.get()

    fun start(context: Context, frameWidth: Int, frameHeight: Int): StartResult {
        if (running.get()) return StartResult.AlreadyRecording
        if (frameWidth < 16 || frameHeight < 16) return StartResult.NotReady
        if (ContextCompat.checkSelfPermission(context, Manifest.permission.RECORD_AUDIO) !=
            PackageManager.PERMISSION_GRANTED
        ) {
            return StartResult.MicPermissionRequired
        }
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.Q &&
            ContextCompat.checkSelfPermission(context, Manifest.permission.WRITE_EXTERNAL_STORAGE) !=
            PackageManager.PERMISSION_GRANTED
        ) {
            return StartResult.StoragePermissionRequired
        }

        val probe = Mat.zeros(frameHeight, frameWidth, org.opencv.core.CvType.CV_8UC3)
        val sized = TagOverlayDrawer.ensureEvenSize(probe, maxLongSide = ENCODE_MAX_SIDE)
        encodeWidth = sized.cols()
        encodeHeight = sized.rows()
        if (sized !== probe) sized.release()
        probe.release()

        val name = "apriltag_${SimpleDateFormat("yyyyMMdd_HHmmss", Locale.US).format(Date())}.mp4"
        val values = ContentValues().apply {
            put(MediaStore.Video.Media.DISPLAY_NAME, name)
            put(MediaStore.Video.Media.MIME_TYPE, "video/mp4")
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
                put(MediaStore.Video.Media.RELATIVE_PATH, "Movies/AprilTagScanner")
                put(MediaStore.Video.Media.IS_PENDING, 1)
            }
        }
        val collection = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            MediaStore.Video.Media.getContentUri(MediaStore.VOLUME_EXTERNAL_PRIMARY)
        } else {
            MediaStore.Video.Media.EXTERNAL_CONTENT_URI
        }
        val uri = context.contentResolver.insert(collection, values)
            ?: return StartResult.Failed("MediaStore insert failed")

        val pfd = try {
            context.contentResolver.openFileDescriptor(uri, "rw")
        } catch (ex: Exception) {
            runCatching { context.contentResolver.delete(uri, null, null) }
            return StartResult.Failed(ex.message ?: ex.toString())
        } ?: run {
            runCatching { context.contentResolver.delete(uri, null, null) }
            return StartResult.Failed("Cannot open output")
        }

        try {
            val vEncoder = MediaCodec.createEncoderByType(MediaFormat.MIMETYPE_VIDEO_AVC)
            val vFormat = MediaFormat.createVideoFormat(
                MediaFormat.MIMETYPE_VIDEO_AVC,
                encodeWidth,
                encodeHeight,
            ).apply {
                setInteger(MediaFormat.KEY_COLOR_FORMAT, MediaCodecInfo.CodecCapabilities.COLOR_FormatSurface)
                setInteger(
                    MediaFormat.KEY_BIT_RATE,
                    (encodeWidth * encodeHeight * 3).coerceIn(1_200_000, 4_000_000),
                )
                setInteger(MediaFormat.KEY_FRAME_RATE, VIDEO_FRAME_RATE)
                // Baseline + frequent IDR: seeking/messengers/WhatsApp-friendly (no B-frames).
                setInteger(MediaFormat.KEY_I_FRAME_INTERVAL, 1)
                setInteger(MediaFormat.KEY_PROFILE, MediaCodecInfo.CodecProfileLevel.AVCProfileBaseline)
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
                    setInteger(MediaFormat.KEY_LEVEL, MediaCodecInfo.CodecProfileLevel.AVCLevel31)
                }
            }
            vEncoder.configure(vFormat, null, null, MediaCodec.CONFIGURE_FLAG_ENCODE)
            val surface = vEncoder.createInputSurface()
            vEncoder.start()

            val aEncoder = MediaCodec.createEncoderByType(MediaFormat.MIMETYPE_AUDIO_AAC)
            val aFormat = MediaFormat.createAudioFormat(
                MediaFormat.MIMETYPE_AUDIO_AAC,
                AUDIO_SAMPLE_RATE,
                1,
            ).apply {
                // AAC-LC is the safest for Telegram/WhatsApp/gallery players.
                setInteger(MediaFormat.KEY_AAC_PROFILE, MediaCodecInfo.CodecProfileLevel.AACObjectLC)
                setInteger(MediaFormat.KEY_BIT_RATE, 128_000)
                setInteger(MediaFormat.KEY_MAX_INPUT_SIZE, 16384)
            }
            aEncoder.configure(aFormat, null, null, MediaCodec.CONFIGURE_FLAG_ENCODE)
            aEncoder.start()

            val minBuf = AudioRecord.getMinBufferSize(
                AUDIO_SAMPLE_RATE,
                AudioFormat.CHANNEL_IN_MONO,
                AudioFormat.ENCODING_PCM_16BIT,
            )
            val record = AudioRecord(
                MediaRecorder.AudioSource.MIC,
                AUDIO_SAMPLE_RATE,
                AudioFormat.CHANNEL_IN_MONO,
                AudioFormat.ENCODING_PCM_16BIT,
                maxOf(minBuf * 2, AUDIO_SAMPLE_RATE),
            )
            if (record.state != AudioRecord.STATE_INITIALIZED) {
                throw IllegalStateException("AudioRecord init failed")
            }

            val mediaMuxer = MediaMuxer(pfd.fileDescriptor, MediaMuxer.OutputFormat.MUXER_OUTPUT_MPEG_4)

            videoEncoder = vEncoder
            audioEncoder = aEncoder
            inputSurface = surface
            audioRecord = record
            outputPfd = pfd
            muxer = mediaMuxer
            videoTrack = -1
            audioTrack = -1
            muxerStarted = false
            lastOfferedPtsUs = -1L
            lastMuxVideoPtsUs = -1L
            lastMuxAudioPtsUs = -1L
            reusableBitmap = Bitmap.createBitmap(encodeWidth, encodeHeight, Bitmap.Config.ARGB_8888)
            outputUri.set(uri)
            outputName.set(name)
            frameQueue.clear()
            postedPtsQueue.clear()
            recordingStartNs = System.nanoTime()
            running.set(true)

            record.startRecording()
            videoThread = Thread({ videoLoop() }, "ats-video-enc").also { it.start() }
            audioThread = Thread({ audioLoop() }, "ats-audio-enc").also { it.start() }

            return StartResult.Started(name, uri)
        } catch (ex: Exception) {
            releaseInternal()
            runCatching { pfd.close() }
            runCatching { context.contentResolver.delete(uri, null, null) }
            return StartResult.Failed(ex.message ?: ex.toString())
        }
    }

    fun offerFrame(
        bgr: Mat,
        tags: List<DetectedTag>,
        duplicates: Set<TagKey>,
        autoProbe: Boolean,
        includeFamily: Boolean = false,
    ) {
        if (!running.get()) return
        val ptsUs = ((System.nanoTime() - recordingStartNs) / 1000L).coerceAtLeast(0L)
        // Cap ~15 fps so encode cannot fall far behind real time (causes freeze vs audio).
        if (lastOfferedPtsUs >= 0 && ptsUs - lastOfferedPtsUs < MIN_FRAME_INTERVAL_US) {
            return
        }
        lastOfferedPtsUs = ptsUs

        val copy = Mat()
        bgr.copyTo(copy)
        val job = FrameJob(copy, tags.toList(), duplicates.toSet(), autoProbe, includeFamily, ptsUs)
        if (!frameQueue.offer(job)) {
            val dropped = frameQueue.poll()
            dropped?.mat?.release()
            if (!frameQueue.offer(job)) {
                job.mat.release()
            }
        }
    }

    fun stop(context: Context): StopResult {
        if (!running.getAndSet(false)) {
            return StopResult.NotRecording
        }
        frameQueue.offer(
            FrameJob(Mat(), emptyList(), emptySet(), false, includeFamily = false, capturePtsUs = 0L, poison = true),
        )
        videoThread?.join(5000)
        runCatching { videoEncoder?.signalEndOfInputStream() }
        drainVideo(eos = true)

        audioThread?.join(5000)
        drainAudio(eos = true)

        val uri = outputUri.get()
        val name = outputName.get()
        releaseInternal()

        if (uri != null && Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            val done = ContentValues().apply { put(MediaStore.Video.Media.IS_PENDING, 0) }
            runCatching { context.contentResolver.update(uri, done, null, null) }
        }
        return if (uri != null && name != null) {
            StopResult.Saved(name, uri)
        } else {
            StopResult.Failed("No output")
        }
    }

    private fun videoLoop() {
        while (true) {
            val job = frameQueue.poll(200, TimeUnit.MILLISECONDS)
            if (job == null) {
                if (!running.get()) break
                drainVideo(false)
                continue
            }
            if (job.poison) {
                job.mat.release()
                break
            }
            if (job.mat.empty()) {
                job.mat.release()
                continue
            }
            try {
                writeVideoFrame(job)
            } catch (_: Exception) {
            } finally {
                job.mat.release()
            }
            drainVideo(false)
        }
    }

    private fun writeVideoFrame(job: FrameJob) {
        val surface = inputSurface ?: return
        val bitmap = reusableBitmap ?: return
        var work = job.mat
        var resized: Mat? = null
        val rgba = Mat()
        try {
            TagOverlayDrawer.draw(work, job.tags, job.duplicates, job.autoProbe, job.includeFamily)
            val sized = TagOverlayDrawer.ensureEvenSize(work, maxLongSide = ENCODE_MAX_SIDE)
            if (sized !== work) {
                resized = sized
                work = sized
            }
            Imgproc.cvtColor(work, rgba, Imgproc.COLOR_BGR2RGBA)
            if (rgba.cols() != encodeWidth || rgba.rows() != encodeHeight) {
                val fitted = Mat()
                Imgproc.resize(rgba, fitted, Size(encodeWidth.toDouble(), encodeHeight.toDouble()))
                Utils.matToBitmap(fitted, bitmap)
                fitted.release()
            } else {
                Utils.matToBitmap(rgba, bitmap)
            }
            val canvas = surface.lockHardwareCanvas()
            try {
                canvas.drawBitmap(bitmap, 0f, 0f, null)
            } finally {
                surface.unlockCanvasAndPost(canvas)
            }
            postedPtsQueue.offer(job.capturePtsUs)
        } finally {
            rgba.release()
            resized?.release()
        }
    }

    private fun audioLoop() {
        val record = audioRecord ?: return
        val encoder = audioEncoder ?: return
        val buffer = ShortArray(2048)
        while (running.get()) {
            val read = record.read(buffer, 0, buffer.size)
            if (read <= 0) continue
            // Same wall-clock timeline as video frames.
            val pts = ((System.nanoTime() - recordingStartNs) / 1000L).coerceAtLeast(0L)
            val ix = encoder.dequeueInputBuffer(10_000)
            if (ix >= 0) {
                val inBuf = encoder.getInputBuffer(ix) ?: continue
                inBuf.clear()
                for (i in 0 until read) {
                    inBuf.putShort(buffer[i])
                }
                encoder.queueInputBuffer(ix, 0, read * 2, pts, 0)
            }
            drainAudio(false)
        }
        val pts = ((System.nanoTime() - recordingStartNs) / 1000L).coerceAtLeast(0L)
        val ix = encoder.dequeueInputBuffer(50_000)
        if (ix >= 0) {
            encoder.queueInputBuffer(ix, 0, 0, pts, MediaCodec.BUFFER_FLAG_END_OF_STREAM)
        }
        drainAudio(true)
    }

    private fun drainVideo(eos: Boolean) {
        val encoder = videoEncoder ?: return
        val info = MediaCodec.BufferInfo()
        var spins = 0
        while (spins++ < 64) {
            val out = encoder.dequeueOutputBuffer(info, if (eos) 20_000 else 0)
            when {
                out == MediaCodec.INFO_TRY_AGAIN_LATER -> return
                out == MediaCodec.INFO_OUTPUT_FORMAT_CHANGED -> {
                    synchronized(muxerLock) {
                        if (videoTrack < 0) {
                            videoTrack = muxer!!.addTrack(encoder.outputFormat)
                            maybeStartMuxer()
                        }
                    }
                }
                out >= 0 -> {
                    val buf = encoder.getOutputBuffer(out)
                    val isConfig = info.flags and MediaCodec.BUFFER_FLAG_CODEC_CONFIG != 0
                    if (buf != null && info.size > 0 && !isConfig) {
                        if (muxerStarted) {
                            val capturePts = postedPtsQueue.poll()
                                ?: (lastMuxVideoPtsUs + 1).coerceAtLeast(0)
                            buf.position(info.offset)
                            buf.limit(info.offset + info.size)
                            val writeInfo = MediaCodec.BufferInfo()
                            writeInfo.set(
                                info.offset,
                                info.size,
                                ensureMonotonic(capturePts, isVideo = true),
                                info.flags,
                            )
                            synchronized(muxerLock) {
                                muxer?.writeSampleData(videoTrack, buf, writeInfo)
                            }
                        } else {
                            // Discard matching capture PTS so queues stay aligned.
                            postedPtsQueue.poll()
                        }
                    }
                    encoder.releaseOutputBuffer(out, false)
                    if (info.flags and MediaCodec.BUFFER_FLAG_END_OF_STREAM != 0) return
                }
            }
        }
    }

    private fun drainAudio(eos: Boolean) {
        val encoder = audioEncoder ?: return
        val info = MediaCodec.BufferInfo()
        var spins = 0
        while (spins++ < 64) {
            val out = encoder.dequeueOutputBuffer(info, if (eos) 20_000 else 0)
            when {
                out == MediaCodec.INFO_TRY_AGAIN_LATER -> return
                out == MediaCodec.INFO_OUTPUT_FORMAT_CHANGED -> {
                    synchronized(muxerLock) {
                        if (audioTrack < 0) {
                            audioTrack = muxer!!.addTrack(encoder.outputFormat)
                            maybeStartMuxer()
                        }
                    }
                }
                out >= 0 -> {
                    val buf = encoder.getOutputBuffer(out)
                    if (buf != null && info.size > 0 && muxerStarted &&
                        info.flags and MediaCodec.BUFFER_FLAG_CODEC_CONFIG == 0
                    ) {
                        buf.position(info.offset)
                        buf.limit(info.offset + info.size)
                        val writeInfo = MediaCodec.BufferInfo()
                        writeInfo.set(
                            info.offset,
                            info.size,
                            ensureMonotonic(info.presentationTimeUs, isVideo = false),
                            info.flags,
                        )
                        synchronized(muxerLock) {
                            muxer?.writeSampleData(audioTrack, buf, writeInfo)
                        }
                    }
                    encoder.releaseOutputBuffer(out, false)
                    if (info.flags and MediaCodec.BUFFER_FLAG_END_OF_STREAM != 0) return
                }
            }
        }
    }

    private fun ensureMonotonic(ptsUs: Long, isVideo: Boolean): Long {
        return if (isVideo) {
            val pts = if (ptsUs <= lastMuxVideoPtsUs) lastMuxVideoPtsUs + 1 else ptsUs
            lastMuxVideoPtsUs = pts
            pts
        } else {
            val pts = if (ptsUs <= lastMuxAudioPtsUs) lastMuxAudioPtsUs + 1 else ptsUs
            lastMuxAudioPtsUs = pts
            pts
        }
    }

    private fun maybeStartMuxer() {
        if (!muxerStarted && videoTrack >= 0 && audioTrack >= 0) {
            muxer?.start()
            muxerStarted = true
        }
    }

    private fun releaseInternal() {
        running.set(false)
        runCatching { audioRecord?.stop() }
        runCatching { audioRecord?.release() }
        audioRecord = null
        runCatching { videoEncoder?.stop() }
        runCatching { videoEncoder?.release() }
        videoEncoder = null
        runCatching { audioEncoder?.stop() }
        runCatching { audioEncoder?.release() }
        audioEncoder = null
        runCatching { inputSurface?.release() }
        inputSurface = null
        runCatching {
            if (muxerStarted) muxer?.stop()
            muxer?.release()
        }
        muxer = null
        muxerStarted = false
        lastOfferedPtsUs = -1L
        lastMuxVideoPtsUs = -1L
        lastMuxAudioPtsUs = -1L
        reusableBitmap?.recycle()
        reusableBitmap = null
        runCatching { outputPfd?.close() }
        outputPfd = null
        while (true) {
            val job = frameQueue.poll() ?: break
            job.mat.release()
        }
        postedPtsQueue.clear()
        videoThread = null
        audioThread = null
    }

    sealed class StartResult {
        data class Started(val filename: String, val uri: Uri) : StartResult()
        data object AlreadyRecording : StartResult()
        data object NotReady : StartResult()
        data object MicPermissionRequired : StartResult()
        data object StoragePermissionRequired : StartResult()
        data class Failed(val message: String) : StartResult()
    }

    sealed class StopResult {
        data class Saved(val filename: String, val uri: Uri) : StopResult()
        data object NotRecording : StopResult()
        data class Failed(val message: String) : StopResult()
    }

    companion object {
        private const val AUDIO_SAMPLE_RATE = 44100
        private const val VIDEO_FRAME_RATE = 15
        private const val ENCODE_MAX_SIDE = 960
        private const val MIN_FRAME_INTERVAL_US = 66_000L // ~15 fps
    }
}
