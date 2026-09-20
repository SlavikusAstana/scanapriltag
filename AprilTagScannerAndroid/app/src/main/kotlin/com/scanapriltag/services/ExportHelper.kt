package com.scanapriltag.services

import com.scanapriltag.localization.L
import com.scanapriltag.models.TagKey
import com.scanapriltag.models.TagLabels
import org.json.JSONArray
import org.json.JSONObject
import java.io.File
import java.io.OutputStream
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

object ExportHelper {
    fun extensionForFilename(filename: String): String =
        File(filename).extension.lowercase(Locale.US).ifEmpty { "txt" }

    fun writeTo(output: OutputStream, session: ScanSession, families: String, extension: String) {
        val whenDate = Date()
        val content = when (extension) {
            "json" -> buildJson(session, families, whenDate)
            "csv" -> buildCsv(session, families)
            else -> buildTextReport(session, families, whenDate)
        }
        output.write(content.toByteArray(Charsets.UTF_8))
    }

    fun buildTextReport(session: ScanSession, families: String, whenDate: Date): String {
        val includeFamily = TagLabels.sessionNeedsFamily(session.records, families.contains(','))
        val sb = StringBuilder()
        sb.appendLine(L.s("ExportTitle"))
        sb.appendLine(L.f("ExportDate", formatDate(whenDate)))
        sb.appendLine()
        sb.appendLine(L.f("ExportFamilies", families))

        if (session.records.isEmpty()) {
            sb.appendLine(L.s("ExportEmpty"))
            return sb.toString()
        }

        sb.appendLine(L.f("ExportTotal", session.records.size))
        sb.appendLine(
            L.f(
                "ExportUnique",
                session.records.map { TagKey(it.family, it.id) }.distinct().size,
            ),
        )
        sb.appendLine()

        session.records.forEachIndexed { index, record ->
            val mark = if (record.duplicate) L.s("DuplicateMarkExport") else ""
            sb.appendLine("  ${index + 1}. ${record.displayLabel(includeFamily)}$mark")
        }

        sb.appendLine()
        if (session.duplicates.isNotEmpty()) {
            val dup = session.duplicates.joinToString(", ") {
                TagLabels.format(it.family, it.id, includeFamily)
            }
            sb.appendLine(L.f("ExportDupYes", dup))
        } else {
            sb.appendLine(L.s("ExportDupNo"))
        }

        return sb.toString()
    }

    fun save(path: String, session: ScanSession, families: String) {
        val ext = File(path).extension.lowercase(Locale.US)
        File(path).writeText(
            when (ext) {
                "json" -> buildJson(session, families, Date())
                "csv" -> buildCsv(session, families)
                else -> buildTextReport(session, families, Date())
            },
            Charsets.UTF_8,
        )
    }

    private fun buildJson(session: ScanSession, families: String, whenDate: Date): String {
        val includeFamily = TagLabels.sessionNeedsFamily(session.records, families.contains(','))
        val payload = JSONObject().apply {
            put("app", L.s("ExportTitle"))
            put("date", formatDate(whenDate))
            put("families", families)
            put("total", session.records.size)
            put(
                "unique",
                session.records.map { TagKey(it.family, it.id) }.distinct().size,
            )
            put(
                "duplicates",
                JSONArray().apply {
                    session.duplicates.forEach { d ->
                        put(JSONObject().apply {
                            put("family", d.family)
                            put("id", d.id)
                        })
                    }
                },
            )
            put(
                "tags",
                JSONArray().apply {
                    session.records.forEachIndexed { index, record ->
                        put(JSONObject().apply {
                            put("index", index + 1)
                            put("family", record.family)
                            put("id", record.id)
                            put("label", record.displayLabel(includeFamily))
                            put("duplicate", record.duplicate)
                        })
                    }
                },
            )
        }
        return payload.toString(2)
    }

    private fun buildCsv(session: ScanSession, families: String): String {
        val includeFamily = TagLabels.sessionNeedsFamily(session.records, families.contains(','))
        val sb = StringBuilder()
        sb.appendLine("index,family,id,label,duplicate")
        session.records.forEachIndexed { index, record ->
            sb.appendLine(
                "${index + 1},${record.family},${record.id},${record.displayLabel(includeFamily)},${record.duplicate}",
            )
        }
        return sb.toString()
    }

    private fun formatDate(date: Date): String =
        SimpleDateFormat("yyyy-MM-dd HH:mm:ss", Locale.US).format(date)
}
