package com.scanapriltag.services

import com.scanapriltag.models.DetectedTag
import org.opencv.core.Mat
import org.opencv.core.Point
import org.opencv.core.Size
import org.opencv.imgproc.Imgproc
import org.opencv.objdetect.ArucoDetector
import org.opencv.objdetect.DetectorParameters
import org.opencv.objdetect.Dictionary
import org.opencv.objdetect.Objdetect
import java.util.concurrent.atomic.AtomicInteger

class DetectionEngine : AutoCloseable {
    private val lock = Any()
    private val worker = Thread(::workerLoop, "AprilTagDetect").apply {
        isDaemon = true
        start()
    }

    @Volatile
    private var running = true

    @Volatile
    private var busy = false

    private var pendingBgr: Mat? = null
    private var detectWidth = 960
    private var families: List<String> = emptyList()
    private var probe = false

    @Volatile
    private var decimate = 1.5f

    private var lastTags: List<DetectedTag> = emptyList()
    private var lastMs = 0.0

    private val cacheVersion = AtomicInteger(0)
    private val detectorCache = mutableMapOf<String, ArucoDetector>()

    fun bumpCache() {
        cacheVersion.incrementAndGet()
    }

    fun configure(decimateValue: Float) {
        if (decimate == decimateValue) return
        decimate = decimateValue
        bumpCache()
    }

    fun trySubmit(bgrFrame: Mat, detectWidthValue: Int, familiesValue: List<String>, probeMode: Boolean): Boolean {
        if (familiesValue.isEmpty()) return false

        val clone = try {
            bgrFrame.clone()
        } catch (_: Exception) {
            return false
        }

        synchronized(lock) {
            if (busy) {
                clone.release()
                return false
            }
            pendingBgr?.release()
            pendingBgr = clone
            detectWidth = detectWidthValue
            families = familiesValue
            probe = probeMode
            busy = true
            (lock as Object).notifyAll()
            return true
        }
    }

    fun snapshot(): Triple<List<DetectedTag>, Double, Boolean> =
        synchronized(lock) {
            Triple(lastTags.toList(), lastMs, busy)
        }

    private fun prepareGray(bgr: Mat, width: Int): Pair<Mat, Float> {
        val w = bgr.cols()
        val scale = minOf(1.0, width.toDouble() / w)
        return if (scale < 1.0) {
            val small = Mat()
            Imgproc.resize(
                bgr,
                small,
                Size(w * scale, bgr.rows() * scale),
                0.0,
                0.0,
                Imgproc.INTER_AREA,
            )
            val gray = Mat()
            Imgproc.cvtColor(small, gray, Imgproc.COLOR_BGR2GRAY)
            small.release()
            gray to (1.0f / scale.toFloat())
        } else {
            val gray = Mat()
            Imgproc.cvtColor(bgr, gray, Imgproc.COLOR_BGR2GRAY)
            gray to 1f
        }
    }

    private fun getDetector(family: String): ArucoDetector {
        val key = "$family@${decimate}"
        return detectorCache.getOrPut(key) {
            val dict: Dictionary = Objdetect.getPredefinedDictionary(TagFamilyCatalog.toDictionary(family))
            val params = DetectorParameters().apply {
                set_aprilTagQuadDecimate(decimate)
            }
            ArucoDetector(dict, params)
        }
    }

    private fun workerLoop() {
        var localCacheVersion = -1

        while (running) {
            val frame = dequeueFrame() ?: continue

            var gray: Mat? = null
            val start = System.nanoTime()
            val found = mutableListOf<DetectedTag>()

            try {
                val (grayMat, invScale) = prepareGray(frame.bgr, frame.width)
                gray = grayMat

                val version = cacheVersion.get()
                if (localCacheVersion != version) {
                    detectorCache.clear()
                    localCacheVersion = version
                }

                for (family in frame.families) {
                    val detector = getDetector(family)
                    val corners = mutableListOf<Mat>()
                    val ids = Mat()
                    val rejected = mutableListOf<Mat>()

                    detector.detectMarkers(gray, corners, ids, rejected)
                    rejected.forEach { it.release() }

                    if (ids.empty()) {
                        ids.release()
                        corners.forEach { it.release() }
                        continue
                    }

                    for (i in 0 until ids.rows()) {
                        val cornerMat = corners[i]
                        val scaled = Array(4) { idx ->
                            val p = cornerMat.get(0, idx)
                            Point(p[0] * invScale, p[1] * invScale)
                        }
                        found.add(
                            DetectedTag(
                                family = family,
                                id = ids.get(i, 0)[0].toInt(),
                                corners = scaled,
                            ),
                        )
                        cornerMat.release()
                    }
                    ids.release()
                }
            } catch (_: Exception) {
                found.clear()
            } finally {
                gray?.release()
                frame.bgr.release()
            }

            val elapsedMs = (System.nanoTime() - start) / 1_000_000.0
            synchronized(lock) {
                lastTags = found
                lastMs = elapsedMs
                busy = false
            }
        }
    }

    private data class PendingFrame(
        val bgr: Mat,
        val width: Int,
        val families: List<String>,
        val probe: Boolean,
    )

    private fun dequeueFrame(): PendingFrame? {
        synchronized(lock) {
            while (running && pendingBgr == null) {
                (lock as Object).wait(50)
            }
            if (!running) return null

            val bgr = pendingBgr ?: return null
            pendingBgr = null
            return PendingFrame(bgr, detectWidth, families.toList(), probe)
        }
    }

    override fun close() {
        running = false
        synchronized(lock) {
            pendingBgr?.release()
            pendingBgr = null
            (lock as Object).notifyAll()
        }
        worker.join(1000)
        detectorCache.clear()
    }
}
