package com.scanapriltag.camera

import androidx.camera.core.ImageProxy
import org.opencv.core.Core
import org.opencv.core.Mat

data class OrientedFrame(
    val bgr: Mat,
    val width: Int,
    val height: Int,
)

object FrameOrientation {
    fun toDisplayOriented(image: ImageProxy, mirrorHorizontal: Boolean): OrientedFrame? {
        val raw = YuvToMat.toBgr(image) ?: return null
        val rotation = image.imageInfo.rotationDegrees

        val oriented = when (rotation) {
            90 -> rotate(raw, Core.ROTATE_90_CLOCKWISE)
            180 -> rotate(raw, Core.ROTATE_180)
            270 -> rotate(raw, Core.ROTATE_90_COUNTERCLOCKWISE)
            else -> raw
        }

        if (oriented !== raw) {
            raw.release()
        }

        if (mirrorHorizontal) {
            Core.flip(oriented, oriented, 1)
        }

        return OrientedFrame(
            bgr = oriented,
            width = oriented.cols(),
            height = oriented.rows(),
        )
    }

    private fun rotate(src: Mat, code: Int): Mat {
        val dst = Mat()
        Core.rotate(src, dst, code)
        return dst
    }
}
