package com.scanapriltag.camera

import android.graphics.ImageFormat
import androidx.camera.core.ImageProxy
import org.opencv.core.CvType
import org.opencv.core.Mat
import org.opencv.imgproc.Imgproc

/**
 * Converts CameraX [ImageFormat.YUV_420_888] to BGR, respecting plane
 * rowStride / pixelStride (dense NV21 packing fails on many devices).
 */
object YuvToMat {
    fun toBgr(image: ImageProxy): Mat? {
        if (image.format != ImageFormat.YUV_420_888) return null

        val width = image.width
        val height = image.height
        if (width <= 0 || height <= 0) return null

        val nv21 = yuv420888ToNv21(image)

        val yuv = Mat(height + height / 2, width, CvType.CV_8UC1)
        yuv.put(0, 0, nv21)

        val bgr = Mat()
        Imgproc.cvtColor(yuv, bgr, Imgproc.COLOR_YUV2BGR_NV21)
        yuv.release()
        return bgr
    }

    private fun yuv420888ToNv21(image: ImageProxy): ByteArray {
        val width = image.width
        val height = image.height
        val yPlane = image.planes[0]
        val uPlane = image.planes[1]
        val vPlane = image.planes[2]

        val yBuffer = yPlane.buffer.duplicate()
        val uBuffer = uPlane.buffer.duplicate()
        val vBuffer = vPlane.buffer.duplicate()

        val yRowStride = yPlane.rowStride
        val yPixelStride = yPlane.pixelStride
        val uRowStride = uPlane.rowStride
        val uPixelStride = uPlane.pixelStride
        val vRowStride = vPlane.rowStride
        val vPixelStride = vPlane.pixelStride

        val nv21 = ByteArray(width * height * 3 / 2)
        var outPos = 0

        // Y
        if (yPixelStride == 1 && yRowStride == width) {
            yBuffer.position(0)
            yBuffer.get(nv21, 0, width * height)
            outPos = width * height
        } else {
            for (row in 0 until height) {
                val rowStart = row * yRowStride
                if (yPixelStride == 1) {
                    yBuffer.position(rowStart)
                    yBuffer.get(nv21, outPos, width)
                    outPos += width
                } else {
                    for (col in 0 until width) {
                        nv21[outPos++] = yBuffer.get(rowStart + col * yPixelStride)
                    }
                }
            }
        }

        // NV21 chroma: V then U, interleaved
        val chromaHeight = height / 2
        val chromaWidth = width / 2
        for (row in 0 until chromaHeight) {
            val vRowStart = row * vRowStride
            val uRowStart = row * uRowStride
            for (col in 0 until chromaWidth) {
                nv21[outPos++] = vBuffer.get(vRowStart + col * vPixelStride)
                nv21[outPos++] = uBuffer.get(uRowStart + col * uPixelStride)
            }
        }

        return nv21
    }
}
