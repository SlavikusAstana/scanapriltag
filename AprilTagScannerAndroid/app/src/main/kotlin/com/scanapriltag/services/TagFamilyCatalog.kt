package com.scanapriltag.services

import com.scanapriltag.localization.L
import org.opencv.objdetect.Objdetect

object TagFamilyCatalog {
    val allFamilies: List<String> = listOf("tag36h11", "tag25h9", "tag16h5", "tag36h10")
    val probePriority: List<String> = allFamilies
    val multiFamilies: List<String> = listOf("tag36h11", "tag25h9", "tag16h5")

    fun getLabel(family: String): String = L.familyLabel(family)

    fun toDictionary(family: String): Int = when (family) {
        "tag36h11" -> Objdetect.DICT_APRILTAG_36h11
        "tag25h9" -> Objdetect.DICT_APRILTAG_25h9
        "tag16h5" -> Objdetect.DICT_APRILTAG_16h5
        "tag36h10" -> Objdetect.DICT_APRILTAG_36h10
        else -> Objdetect.DICT_APRILTAG_36h11
    }
}

enum class SpeedPreset {
    Fast,
    Balanced,
    Accurate,
}

object SpeedPresetSettings {
    data class Settings(val detectWidth: Int, val decimate: Float, val stride: Int)

    fun get(preset: SpeedPreset): Settings = when (preset) {
        SpeedPreset.Fast -> Settings(640, 2.0f, 2)
        SpeedPreset.Balanced -> Settings(960, 1.5f, 1)
        SpeedPreset.Accurate -> Settings(1280, 1.0f, 1)
    }

    fun label(preset: SpeedPreset): String = when (preset) {
        SpeedPreset.Fast -> L.presetFast
        SpeedPreset.Balanced -> L.presetBalanced
        SpeedPreset.Accurate -> L.presetAccurate
    }
}
