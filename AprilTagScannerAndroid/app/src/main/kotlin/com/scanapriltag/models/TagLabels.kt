package com.scanapriltag.models

object TagLabels {
    fun shortFamily(family: String): String {
        val trimmed = family.trim()
        if (trimmed.isEmpty()) return ""
        return if (trimmed.startsWith("tag", ignoreCase = true)) trimmed.substring(3) else trimmed
    }

    fun format(family: String, id: Int, includeFamily: Boolean): String =
        if (includeFamily) "${shortFamily(family)}:$id" else id.toString()

    fun sessionNeedsFamily(records: List<TagRecord>, multiFamily: Boolean): Boolean =
        multiFamily || records.map { it.family }.distinct().size > 1
}
