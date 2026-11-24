package com.artflow.tablet.storage

import android.graphics.Bitmap
import com.artflow.tablet.model.ArtLayer
import com.artflow.tablet.model.BlendMode
import com.artflow.tablet.model.CanvasDocument
import org.json.JSONArray
import org.json.JSONObject
import java.io.*
import java.util.zip.ZipEntry
import java.util.zip.ZipInputStream
import java.util.zip.ZipOutputStream

object DocumentSerializer {

    fun serializeManifest(document: CanvasDocument): String {
        val root = JSONObject()
        root.put("id", document.id)
        root.put("title", document.title)
        root.put("width", document.width)
        root.put("height", document.height)
        root.put("dpi", document.dpi)
        root.put("backgroundColor", document.backgroundColor)
        root.put("activeLayerIndex", document.activeLayerIndex)

        val layersArray = JSONArray()
        for (layer in document.layers) {
            val layerObj = JSONObject()
            layerObj.put("id", layer.id)
            layerObj.put("name", layer.name)
            layerObj.put("opacity", layer.opacity.toDouble())
            layerObj.put("blendMode", layer.blendMode.name)
            layerObj.put("isVisible", layer.isVisible)
            layerObj.put("isAlphaLocked", layer.isAlphaLocked)
            layerObj.put("isClippingMask", layer.isClippingMask)
            layersArray.put(layerObj)
        }
        root.put("layers", layersArray)

        return root.toString(2)
    }

    fun deserializeManifest(jsonString: String): CanvasDocument {
        val root = JSONObject(jsonString)
        val doc = CanvasDocument(
            id = root.getString("id"),
            title = root.getString("title"),
            width = root.getInt("width"),
            height = root.getInt("height"),
            dpi = root.optInt("dpi", 300),
            backgroundColor = root.optInt("backgroundColor", 0xFFFFFFFF.toInt()),
            activeLayerIndex = root.optInt("activeLayerIndex", 0)
        )
        doc.layers.clear()

        val layersArray = root.getJSONArray("layers")
        for (i in 0 until layersArray.length()) {
            val layerObj = layersArray.getJSONObject(i)
            val layer = ArtLayer(
                id = layerObj.getString("id"),
                name = layerObj.getString("name"),
                opacity = layerObj.getDouble("opacity").toFloat(),
                blendMode = BlendMode.fromName(layerObj.getString("blendMode")),
                isVisible = layerObj.getBoolean("isVisible"),
                isAlphaLocked = layerObj.optBoolean("isAlphaLocked", false),
                isClippingMask = layerObj.optBoolean("isClippingMask", false)
            )
            doc.layers.add(layer)
        }
        return doc
    }

    fun saveDocumentPackage(
        document: CanvasDocument,
        outputStream: OutputStream
    ) {
        val zipOut = ZipOutputStream(BufferedOutputStream(outputStream))

        // Write manifest.json
        val manifestEntry = ZipEntry("manifest.json")
        zipOut.putNextEntry(manifestEntry)
        val manifestBytes = serializeManifest(document).toByteArray(Charsets.UTF_8)
        zipOut.write(manifestBytes)
        zipOut.closeEntry()

        zipOut.finish()
        zipOut.flush()
    }
}
