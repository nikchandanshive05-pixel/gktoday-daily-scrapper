package com.artflow.tablet.storage

import java.io.File
import java.io.FileWriter
import java.io.PrintWriter

class WriteAheadJournal(val journalFile: File) {

    fun logStrokeCommit(layerId: String, pointCount: Int) {
        try {
            val writer = PrintWriter(FileWriter(journalFile, true))
            writer.println("${System.currentTimeMillis()}|$layerId|$pointCount")
            writer.flush()
            writer.close()
        } catch (e: Exception) {
            e.printStackTrace()
        }
    }

    fun hasPendingRecovery(): Boolean {
        return journalFile.exists() && journalFile.length() > 0
    }

    fun clearJournal() {
        if (journalFile.exists()) {
            journalFile.delete()
        }
    }
}
