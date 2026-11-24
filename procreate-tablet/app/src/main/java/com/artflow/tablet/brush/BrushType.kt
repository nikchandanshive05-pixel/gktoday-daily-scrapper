package com.artflow.tablet.brush

enum class BrushType(val displayName: String, val category: String) {
    PENCIL_6B("6B Pencil", "Sketching"),
    STUDIO_PEN("Studio Pen", "Inking"),
    SOFT_AIRBRUSH("Soft Airbrush", "Airbrushing"),
    FLAT_BRUSH("Flat Brush", "Painting"),
    SMUDGE("Smudge", "Blending"),
    ERASER("Eraser", "Utility")
}
