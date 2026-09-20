package com.scanapriltag.models

import org.opencv.core.Point

data class TagKey(val family: String, val id: Int)

data class DetectedTag(
    val family: String,
    val id: Int,
    val corners: Array<Point>,
) {
    val center: Point
        get() {
            var x = 0.0
            var y = 0.0
            for (p in corners) {
                x += p.x
                y += p.y
            }
            return Point(x / corners.size, y / corners.size)
        }

    val key: TagKey get() = TagKey(family, id)

    override fun equals(other: Any?): Boolean {
        if (this === other) return true
        if (other !is DetectedTag) return false
        return family == other.family && id == other.id && corners.contentEquals(other.corners)
    }

    override fun hashCode(): Int {
        var result = family.hashCode()
        result = 31 * result + id
        result = 31 * result + corners.contentHashCode()
        return result
    }
}

data class TagRecord(
    val family: String,
    val id: Int,
    val duplicate: Boolean,
) {
    fun displayLabel(includeFamily: Boolean): String =
        TagLabels.format(family, id, includeFamily)

    /** ID-only; prefer [displayLabel] when family may be ambiguous. */
    val label: String get() = id.toString()
}

data class LiveLine(
    val text: String,
    val duplicate: Boolean,
)
