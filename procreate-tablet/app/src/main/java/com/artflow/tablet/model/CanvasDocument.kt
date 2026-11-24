package com.artflow.tablet.model

import java.util.UUID

data class CanvasDocument(
    val id: String = UUID.randomUUID().toString(),
    var title: String = "Untitled Artwork",
    val width: Int,
    val height: Int,
    val dpi: Int = 300,
    val layers: MutableList<ArtLayer> = mutableListOf(),
    var activeLayerIndex: Int = 0,
    var backgroundColor: Int = 0xFFFFFFFF.toInt(),
    var maxLayersLimit: Int = 16
) {
    init {
        if (layers.isEmpty()) {
            layers.add(ArtLayer(name = "Background", isVisible = true))
            layers.add(ArtLayer(name = "Layer 1", isVisible = true))
            activeLayerIndex = 1
        }
    }

    val activeLayer: ArtLayer
        get() = layers.getOrElse(activeLayerIndex) { layers.last() }

    fun canAddLayer(): Boolean = layers.size < maxLayersLimit

    fun addLayer(name: String? = null, atIndex: Int? = null): ArtLayer? {
        if (!canAddLayer()) return null
        val newLayer = ArtLayer(name = name ?: "Layer ${layers.size}")
        val insertIndex = atIndex ?: (activeLayerIndex + 1).coerceAtMost(layers.size)
        layers.add(insertIndex, newLayer)
        activeLayerIndex = insertIndex
        return newLayer
    }

    fun removeLayer(index: Int): ArtLayer? {
        if (layers.size <= 1) return null // Must retain at least one layer
        val removed = layers.removeAt(index)
        activeLayerIndex = activeLayerIndex.coerceAtMost(layers.size - 1)
        return removed
    }

    fun reorderLayers(fromIndex: Int, toIndex: Int) {
        if (fromIndex in layers.indices && toIndex in layers.indices && fromIndex != toIndex) {
            val item = layers.removeAt(fromIndex)
            layers.add(toIndex, item)
            activeLayerIndex = toIndex
        }
    }

    companion object {
        fun calculateSafeMaxLayers(width: Int, height: Int, availableRamMb: Long): Int {
            val bytesPerLayer = width.toLong() * height.toLong() * 4L // RGBA_8888
            val mbPerLayer = (bytesPerLayer / (1024L * 1024L)).coerceAtLeast(1L)
            val budgetedMb = (availableRamMb * 0.35f).toLong() // 35% of free RAM budget for active textures
            val calculated = (budgetedMb / mbPerLayer).toInt()
            return calculated.coerceIn(8, 64)
        }
    }
}
