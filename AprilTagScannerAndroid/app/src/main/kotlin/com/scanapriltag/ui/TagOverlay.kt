package com.scanapriltag.ui

import androidx.compose.foundation.Canvas
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.nativeCanvas
import com.scanapriltag.localization.L
import com.scanapriltag.models.DetectedTag
import com.scanapriltag.models.TagKey
import com.scanapriltag.models.TagLabels
import com.scanapriltag.ui.theme.DuplicateRed
import com.scanapriltag.ui.theme.ScanGreen
import com.scanapriltag.ui.theme.WarningAmber

/**
 * Maps tag corners from analysis image space to the preview area.
 * Analysis frames are already rotated to match [PreviewView] display orientation.
 */
@Composable
fun TagOverlay(
    tags: List<DetectedTag>,
    duplicates: Set<TagKey>,
    autoProbe: Boolean,
    frameWidth: Int,
    frameHeight: Int,
    includeFamily: Boolean = false,
    modifier: Modifier = Modifier,
) {
    val overlayDupLabel = L.s("OverlayDup")
    Canvas(modifier = modifier) {
        if (frameWidth <= 0 || frameHeight <= 0) return@Canvas

        val srcW = frameWidth.toFloat()
        val srcH = frameHeight.toFloat()
        val scale = minOf(size.width / srcW, size.height / srcH)
        val offsetX = (size.width - srcW * scale) / 2f
        val offsetY = (size.height - srcH * scale) / 2f

        fun mapPoint(x: Double, y: Double): Offset =
            Offset(
                offsetX + x.toFloat() * scale,
                offsetY + y.toFloat() * scale,
            )

        for (tag in tags) {
            val dup = duplicates.contains(tag.key)
            val color = when {
                dup -> DuplicateRed
                autoProbe -> WarningAmber
                else -> ScanGreen
            }
            val stroke = if (dup) 5f else 3f

            val points = tag.corners.map { mapPoint(it.x, it.y) }
            for (i in points.indices) {
                drawLine(
                    color = color,
                    start = points[i],
                    end = points[(i + 1) % 4],
                    strokeWidth = stroke,
                )
            }

            val center = mapPoint(tag.center.x, tag.center.y)
            val idText = TagLabels.format(tag.family, tag.id, includeFamily)
            val label = when {
                autoProbe -> "$idText?"
                dup -> "$idText $overlayDupLabel"
                else -> idText
            }

            drawContext.canvas.nativeCanvas.apply {
                val textSizePx = 34f * scale.coerceIn(0.65f, 1.25f)
                val textPaint = android.graphics.Paint().apply {
                    this.color = android.graphics.Color.WHITE
                    this.textSize = textSizePx
                    isAntiAlias = true
                    textAlign = android.graphics.Paint.Align.CENTER
                    isFakeBoldText = true
                }
                val textWidth = textPaint.measureText(label)
                val padH = 10f * scale.coerceIn(0.7f, 1.1f)
                val padV = 6f * scale.coerceIn(0.7f, 1.1f)
                val bgLeft = center.x - textWidth / 2f - padH
                val bgTop = center.y - textSizePx / 2f - padV
                val bgRight = center.x + textWidth / 2f + padH
                val bgBottom = center.y + textSizePx / 2f + padV

                val bgPaint = android.graphics.Paint().apply {
                    this.color = android.graphics.Color.argb(
                        210,
                        (color.red * 255).toInt(),
                        (color.green * 255).toInt(),
                        (color.blue * 255).toInt(),
                    )
                    isAntiAlias = true
                }
                drawRoundRect(
                    bgLeft,
                    bgTop,
                    bgRight,
                    bgBottom,
                    8f,
                    8f,
                    bgPaint,
                )
                drawText(label, center.x, center.y + textSizePx / 3f, textPaint)
            }
        }
    }
}
