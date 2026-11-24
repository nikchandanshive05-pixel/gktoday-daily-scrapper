package com.artflow.tablet.model

import java.util.UUID

data class ArtLayer(
    val id: String = UUID.randomUUID().toString(),
    var name: String = "Layer",
    var opacity: Float = 1.0f,
    var blendMode: BlendMode = BlendMode.NORMAL,
    var isVisible: Boolean = true,
    var isAlphaLocked: Boolean = false,
    var isClippingMask: Boolean = false,
    var textureId: Int = 0,
    var isSwappedToDisk: Boolean = false,
    var cacheFilePath: String? = null
) {
    fun copyState(): ArtLayer {
        return copy()
    }
}
