package com.artflow.tablet.model

enum class BlendMode(val displayName: String, val glslFunction: String) {
    NORMAL("Normal", "blendNormal"),
    MULTIPLY("Multiply", "blendMultiply"),
    SCREEN("Screen", "blendScreen"),
    OVERLAY("Overlay", "blendOverlay"),
    ADD("Add", "blendAdd"),
    COLOR_DODGE("Color Dodge", "blendColorDodge"),
    DARKEN("Darken", "blendDarken"),
    LIGHTEN("Lighten", "blendLighten");

    companion object {
        fun fromName(name: String): BlendMode {
            return entries.find { it.name.equals(name, ignoreCase = true) } ?: NORMAL
        }
    }
}
