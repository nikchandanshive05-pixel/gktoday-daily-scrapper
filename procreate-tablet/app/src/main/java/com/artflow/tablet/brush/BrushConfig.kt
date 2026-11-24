package com.artflow.tablet.brush

data class BrushConfig(
    val type: BrushType,
    var size: Float = 24f,
    var opacity: Float = 1.0f,
    var spacing: Float = 0.08f,
    var streamline: Float = 0.4f,
    var pressureSizeDynamics: Float = 0.8f,
    var pressureOpacityDynamics: Float = 0.6f,
    var jitter: Float = 0.0f,
    var hardness: Float = 0.9f,
    var grainScale: Float = 1.0f
) {
    fun calculateRadius(pressure: Float): Float {
        val dynamicFactor = 1.0f - pressureSizeDynamics + (pressureSizeDynamics * pressure.coerceIn(0.05f, 1.0f))
        return (size / 2.0f) * dynamicFactor
    }

    fun calculateAlpha(pressure: Float): Float {
        val dynamicFactor = 1.0f - pressureOpacityDynamics + (pressureOpacityDynamics * pressure.coerceIn(0.05f, 1.0f))
        return (opacity * dynamicFactor).coerceIn(0.01f, 1.0f)
    }

    companion object {
        fun createDefault(type: BrushType): BrushConfig {
            return when (type) {
                BrushType.PENCIL_6B -> BrushConfig(
                    type = type,
                    size = 18f,
                    opacity = 0.85f,
                    spacing = 0.12f,
                    streamline = 0.15f,
                    pressureSizeDynamics = 0.5f,
                    pressureOpacityDynamics = 0.9f,
                    jitter = 0.15f,
                    hardness = 0.6f,
                    grainScale = 2.0f
                )
                BrushType.STUDIO_PEN -> BrushConfig(
                    type = type,
                    size = 12f,
                    opacity = 1.0f,
                    spacing = 0.04f,
                    streamline = 0.65f, // Procreate's signature smooth ink
                    pressureSizeDynamics = 0.95f,
                    pressureOpacityDynamics = 0.2f,
                    jitter = 0.0f,
                    hardness = 0.95f
                )
                BrushType.SOFT_AIRBRUSH -> BrushConfig(
                    type = type,
                    size = 64f,
                    opacity = 0.4f,
                    spacing = 0.06f,
                    streamline = 0.25f,
                    pressureSizeDynamics = 0.3f,
                    pressureOpacityDynamics = 0.8f,
                    hardness = 0.1f // diffuse falloff
                )
                BrushType.FLAT_BRUSH -> BrushConfig(
                    type = type,
                    size = 36f,
                    opacity = 0.9f,
                    spacing = 0.05f,
                    streamline = 0.3f,
                    pressureSizeDynamics = 0.7f,
                    pressureOpacityDynamics = 0.5f,
                    hardness = 0.85f
                )
                BrushType.SMUDGE -> BrushConfig(
                    type = type,
                    size = 32f,
                    opacity = 0.6f,
                    spacing = 0.05f,
                    streamline = 0.35f,
                    pressureSizeDynamics = 0.5f,
                    pressureOpacityDynamics = 0.5f,
                    hardness = 0.5f
                )
                BrushType.ERASER -> BrushConfig(
                    type = type,
                    size = 28f,
                    opacity = 1.0f,
                    spacing = 0.05f,
                    streamline = 0.2f,
                    pressureSizeDynamics = 0.6f,
                    pressureOpacityDynamics = 0.1f,
                    hardness = 0.9f
                )
            }
        }
    }
}
