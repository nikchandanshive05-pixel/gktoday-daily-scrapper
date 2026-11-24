package com.artflow.tablet.brush

object CatmullRomSpline {

    fun interpolatePoint(
        p0: StrokePoint,
        p1: StrokePoint,
        p2: StrokePoint,
        p3: StrokePoint,
        t: Float
    ): StrokePoint {
        val t2 = t * t
        val t3 = t2 * t

        // Standard Catmull-Rom formulation (tension = 0.5)
        val x = 0.5f * (
            (2f * p1.x) +
            (-p0.x + p2.x) * t +
            (2f * p0.x - 5f * p1.x + 4f * p2.x - p3.x) * t2 +
            (-p0.x + 3f * p1.x - 3f * p2.x + p3.x) * t3
        )

        val y = 0.5f * (
            (2f * p1.y) +
            (-p0.y + p2.y) * t +
            (2f * p0.y - 5f * p1.y + 4f * p2.y - p3.y) * t2 +
            (-p0.y + 3f * p1.y - 3f * p2.y + p3.y) * t3
        )

        val pressure = p1.pressure + (p2.pressure - p1.pressure) * t
        val tilt = p1.tilt + (p2.tilt - p1.tilt) * t
        val orientation = p1.orientation + (p2.orientation - p1.orientation) * t
        val timestamp = (p1.timestamp + (p2.timestamp - p1.timestamp) * t).toLong()

        return StrokePoint(x, y, pressure, tilt, orientation, timestamp)
    }

    fun generateInterpolatedSegment(
        p0: StrokePoint,
        p1: StrokePoint,
        p2: StrokePoint,
        p3: StrokePoint,
        stepDistance: Float
    ): List<StrokePoint> {
        val chordDist = p1.distanceTo(p2)
        val steps = (chordDist / stepDistance.coerceAtLeast(1f)).toInt().coerceIn(1, 100)
        val result = ArrayList<StrokePoint>(steps)
        for (i in 1..steps) {
            val t = i.toFloat() / steps.toFloat()
            result.add(interpolatePoint(p0, p1, p2, p3, t))
        }
        return result
    }
}
