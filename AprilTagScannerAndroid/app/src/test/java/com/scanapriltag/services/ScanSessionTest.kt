package com.scanapriltag.services

import com.scanapriltag.models.DetectedTag
import com.scanapriltag.models.TagKey
import com.scanapriltag.models.TagLabels
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test
import org.opencv.core.Point

class ScanSessionTest {
    private fun tag(family: String, id: Int, x: Double = 10.0, y: Double = 10.0): DetectedTag {
        val corners = arrayOf(
            Point(x, y),
            Point(x + 20, y),
            Point(x + 20, y + 20),
            Point(x, y + 20),
        )
        return DetectedTag(family, id, corners)
    }

    @Test
    fun firstSight_recordsOnce() {
        val session = ScanSession()
        val a = tag("tag36h11", 7)
        assertEquals(1, session.processDetections(listOf(a), 8).size)
        assertEquals(0, session.processDetections(listOf(a), 8).size)
        assertEquals(1, session.records.size)
    }

    @Test
    fun reappearAfterOtherTag_isDuplicate() {
        val session = ScanSession()
        val a = tag("tag36h11", 1, x = 10.0)
        val b = tag("tag36h11", 2, x = 100.0)
        session.processDetections(listOf(a), 8)
        session.processDetections(listOf(a, b), 8)
        session.clearTracking()
        val again = session.processDetections(listOf(a), 8)
        assertEquals(1, again.size)
        assertTrue(again[0].duplicate)
        assertTrue(session.duplicates.contains(TagKey("tag36h11", 1)))
    }

    @Test
    fun flickerWithinMissLimit_doesNotRerecord() {
        val session = ScanSession()
        val a = tag("tag36h11", 3)
        session.processDetections(listOf(a), 3)
        session.processDetections(emptyList(), 3)
        session.processDetections(emptyList(), 3)
        assertTrue(session.processDetections(listOf(a), 3).isEmpty())
    }

    @Test
    fun tagLabels_format() {
        assertEquals("12", TagLabels.format("tag36h11", 12, false))
        assertEquals("36h11:12", TagLabels.format("tag36h11", 12, true))
        assertFalse(TagLabels.sessionNeedsFamily(emptyList(), multiFamily = false))
        assertTrue(TagLabels.sessionNeedsFamily(emptyList(), multiFamily = true))
    }
}
