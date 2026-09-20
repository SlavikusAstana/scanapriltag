package com.scanapriltag

import android.app.Application
import android.util.Log
import org.opencv.android.OpenCVLoader

class AprilTagApp : Application() {
    override fun onCreate() {
        super.onCreate()
        if (!OpenCVLoader.initLocal()) {
            Log.e("AprilTagScanner", "OpenCV initialization failed")
        }
    }
}
