package com.artflow.tablet.storage

import com.artflow.tablet.model.ArtLayer
import com.artflow.tablet.model.BlendMode
import com.artflow.tablet.model.CanvasDocument
import org.junit.Assert.*
import org.junit.Test
import java.io.ByteArrayInputStream
import java.io.ByteArrayOutputStream
import java.util.zip.ZipInputStream

class DocumentStorageTest {

    @Test
    fun testManifestSerializationAndDeserialization() {
        val doc = CanvasDocument(width = 2560, height = 1600, title = "Masterpiece")
        doc.layers.clear()
        doc.layers.add(ArtLayer(name = "Background", blendMode = BlendMode.NORMAL, opacity = 1.0f))
        doc.layers.add(ArtLayer(name = "Inking", blendMode = BlendMode.MULTIPLY, opacity = 0.85f, isAlphaLocked = true))
        doc.layers.add(ArtLayer(name = "Shading", blendMode = BlendMode.COLOR_DODGE, opacity = 0.5f, isClippingMask = true))
        doc.activeLayerIndex = 1

        val json = DocumentSerializer.serializeManifest(doc)
        val restored = DocumentSerializer.deserializeManifest(json)

        assertEquals("Masterpiece", restored.title)
        assertEquals(2560, restored.width)
        assertEquals(1600, restored.height)
        assertEquals(3, restored.layers.size)
        assertEquals(1, restored.activeLayerIndex)

        val layer1 = restored.layers[1]
        assertEquals("Inking", layer1.name)
        assertEquals(BlendMode.MULTIPLY, layer1.blendMode)
        assertEquals(0.85f, layer1.opacity, 0.01f)
        assertTrue(layer1.isAlphaLocked)

        val layer2 = restored.layers[2]
        assertEquals("Shading", layer2.name)
        assertEquals(BlendMode.COLOR_DODGE, layer2.blendMode)
        assertTrue(layer2.isClippingMask)
    }

    @Test
    fun testZipPackagePackaging() {
        val doc = CanvasDocument(width = 1000, height = 1000, title = "Test Zip")
        val baos = ByteArrayOutputStream()
        DocumentSerializer.saveDocumentPackage(doc, baos)

        val zipBytes = baos.toByteArray()
        assertTrue("Zip should have content", zipBytes.isNotEmpty())

        val zis = ZipInputStream(ByteArrayInputStream(zipBytes))
        var foundManifest = false
        var entry = zis.nextEntry
        while (entry != null) {
            if (entry.name == "manifest.json") {
                foundManifest = true
            }
            entry = zis.nextEntry
        }
        assertTrue("manifest.json must be present in .canvas package", foundManifest)
    }
}
