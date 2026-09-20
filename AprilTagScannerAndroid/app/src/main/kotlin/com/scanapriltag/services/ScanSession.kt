package com.scanapriltag.services

import com.scanapriltag.models.DetectedTag
import com.scanapriltag.models.TagKey
import com.scanapriltag.models.TagRecord

/**
 * Session state is mutated from the camera analysis thread and read from main
 * (UI / export). All public access goes through [lock].
 */
class ScanSession {
    private val lock = Any()

    private val visibleNow = mutableSetOf<TagKey>()
    private val missCounts = mutableMapOf<TagKey, Int>()
    private val recordsMut = mutableListOf<TagRecord>()
    private val duplicatesMut = mutableSetOf<TagKey>()

    /** Immutable snapshot — safe to iterate off the analysis thread. */
    val records: List<TagRecord>
        get() = synchronized(lock) { recordsMut.toList() }

    /** Immutable snapshot for overlay / export. */
    val duplicates: Set<TagKey>
        get() = synchronized(lock) { duplicatesMut.toSet() }

    fun reset() {
        synchronized(lock) {
            recordsMut.clear()
            duplicatesMut.clear()
            visibleNow.clear()
            missCounts.clear()
        }
    }

    fun clearTracking() {
        synchronized(lock) {
            visibleNow.clear()
            missCounts.clear()
        }
    }

    fun shouldRecord(key: TagKey): Pair<Boolean, Boolean> {
        synchronized(lock) {
            return shouldRecordLocked(key)
        }
    }

    fun tryAppend(tag: DetectedTag): TagRecord? {
        synchronized(lock) {
            return tryAppendLocked(tag)
        }
    }

    fun processDetections(tags: List<DetectedTag>, missLimit: Int): List<TagRecord> {
        synchronized(lock) {
            val detected = tags.associateBy { it.key }
            val appended = mutableListOf<TagRecord>()

            for (key in visibleNow.toList()) {
                if (detected.containsKey(key)) {
                    missCounts[key] = 0
                    continue
                }

                val missed = (missCounts[key] ?: 0) + 1
                missCounts[key] = missed
                if (missed >= missLimit) {
                    visibleNow.remove(key)
                    missCounts.remove(key)
                }
            }

            val newKeys = detected.keys
                .filter { it !in visibleNow }
                .sortedWith(
                    compareBy<TagKey> { detected[it]!!.center.y }
                        .thenBy { detected[it]!!.center.x },
                )

            for (key in newKeys) {
                val record = tryAppendLocked(detected[key]!!)
                if (record != null) appended.add(record)
                visibleNow.add(key)
                missCounts[key] = 0
            }

            return appended
        }
    }

    private fun shouldRecordLocked(key: TagKey): Pair<Boolean, Boolean> {
        val keys = recordsMut.map { TagKey(it.family, it.id) }
        if (!keys.contains(key)) return true to false

        val lastPos = keys.indexOfLast { it == key }
        val otherSince = keys.drop(lastPos + 1).any { it != key }
        if (!otherSince) return false to false

        return true to true
    }

    private fun tryAppendLocked(tag: DetectedTag): TagRecord? {
        val (should, isDup) = shouldRecordLocked(tag.key)
        if (!should) return null

        val record = TagRecord(tag.family, tag.id, isDup)
        if (isDup) duplicatesMut.add(tag.key)
        recordsMut.add(record)
        return record
    }
}
