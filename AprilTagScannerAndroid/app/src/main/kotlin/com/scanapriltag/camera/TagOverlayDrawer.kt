package com.scanapriltag.camera

import com.scanapriltag.localization.L
import com.scanapriltag.models.DetectedTag
import com.scanapriltag.models.TagKey
import com.scanapriltag.models.TagLabels
import org.opencv.core.Mat
import org.opencv.core.Point
import org.opencv.core.Scalar
import org.opencv.core.Size
import org.opencv.imgproc.Imgproc
import kotlin.math.max
import kotlin.math.roundToInt

/**
 * Draws the same tag outlines / ID badges that the live Compose overlay shows,
 * directly onto an OpenCV BGR frame for video encoding.
 */
object TagOverlayDrawer {
    private val green = Scalar(99.0, 164.0, 31.0) // BGR of #1FA463
    private val red = Scalar(47.0, 47.0, 211.0) // BGR of #D32F2F
    private val amber = Scalar(0.0, 152.0, 255.0) // BGR of #FF9800
    private val white = Scalar(255.0, 255.0, 255.0)

    fun draw(
        bgr: Mat,
        tags: List<DetectedTag>,
        duplicates: Set<TagKey>,
        autoProbe: Boolean,
        includeFamily: Boolean = false,
    ) {
        if (tags.isEmpty()) return
        val scale = (minOf(bgr.cols(), bgr.rows()) / 720.0).coerceIn(0.65, 1.4)
        val stroke = max(2, (3.0 * scale).roundToInt())
        val dupStroke = max(3, (5.0 * scale).roundToInt())
        val fontScale = (0.9 * scale).coerceIn(0.55, 1.35)
        val thickness = max(1, (2.0 * scale).roundToInt())
        val dupLabel = L.s("OverlayDup")

        for (tag in tags) {
            val dup = duplicates.contains(tag.key)
            val color = when {
                dup -> red
                autoProbe -> amber
                else -> green
            }
            val lineW = if (dup) dupStroke else stroke
            val corners = tag.corners
            for (i in corners.indices) {
                Imgproc.line(bgr, corners[i], corners[(i + 1) % corners.size], color, lineW, Imgproc.LINE_AA)
            }

            val idText = TagLabels.format(tag.family, tag.id, includeFamily)
            val label = when {
                autoProbe -> "$idText?"
                dup -> "$idText $dupLabel"
                else -> idText
            }
            val center = tag.center
            val baseline = IntArray(1)
            val textSize = Imgproc.getTextSize(label, Imgproc.FONT_HERSHEY_SIMPLEX, fontScale, thickness, baseline)
            val padH = 10.0 * scale
            val padV = 8.0 * scale
            val bgTl = Point(center.x - textSize.width / 2.0 - padH, center.y - textSize.height - padV)
            val bgBr = Point(center.x + textSize.width / 2.0 + padH, center.y + padV)
            Imgproc.rectangle(bgr, bgTl, bgBr, color, -1, Imgproc.LINE_AA)
            val textOrg = Point(center.x - textSize.width / 2.0, center.y - baseline[0] / 2.0)
            Imgproc.putText(
                bgr,
                label,
                textOrg,
                Imgproc.FONT_HERSHEY_SIMPLEX,
                fontScale,
                white,
                thickness,
                Imgproc.LINE_AA,
                false,
            )
        }
    }

    fun ensureEvenSize(src: Mat, maxLongSide: Int = 1280): Mat {
        var w = src.cols()
        var h = src.rows()
        val longSide = max(w, h)
        if (longSide > maxLongSide) {
            val scale = maxLongSide.toDouble() / longSide
            w = (w * scale).roundToInt()
            h = (h * scale).roundToInt()
        }
        if (w % 2 != 0) w--
        if (h % 2 != 0) h--
        w = w.coerceAtLeast(2)
        h = h.coerceAtLeast(2)
        if (w == src.cols() && h == src.rows()) return src
        val dst = Mat()
        Imgproc.resize(src, dst, Size(w.toDouble(), h.toDouble()), 0.0, 0.0, Imgproc.INTER_AREA)
        return dst
    }
}
