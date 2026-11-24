package com.artflow.tablet.storage

import android.graphics.Bitmap
import com.artflow.tablet.model.CanvasDocument
import java.io.OutputStream

object ExportEngine {

    enum class ExportFormat {
        PNG,
        JPEG
    }

    fun exportFlattenedImage(
        bitmap: Bitmap,
        format: ExportFormat,
        quality: Int = 100,
        outputStream: OutputStream
    ): Boolean {
        val compressFormat = when (format) {
            ExportFormat.PNG -> Bitmap.CompressFormat.PNG
            ExportFormat.JPEG -> Bitmap.CompressFormat.JPEG
        }
        return bitmap.compress(compressFormat, quality, outputStream)
    }
}
