package com.artflow.tablet.brush

import kotlin.math.hypot

data class StrokePoint(
    val x: Float,
    val y: Float,
    val pressure: Float = 0.5f,
    val tilt: Float = 0f,
    val orientation: Float = 0f,
    val timestamp: Long = System.currentTimeMillis()
) {
    fun distanceTo(other: StrokePoint): Float {
        return hypot(x - other.x, y - other.y)
    }

    fun interpolate(other: StrokePoint, t: Float): StrokePoint {
        val clampedT = t.coerceIn(0f, 1f)
        return StrokePoint(
            x = x + (other.x - x) * clampedT,
            y = y + (other.y - y) * clampedT,
            pressure = pressure + (other.pressure - pressure) * clampedT,
            tilt = tilt + (other.tilt - tilt) * clampedT,
            orientation = orientation + (other.orientation - orientation) * clampedT,
            timestamp = (timestamp + ((other.timestamp - timestamp) * clampedT)).toLong()
        )
    }
}
