package com.artflow.tablet.features

import com.artflow.tablet.brush.StrokePoint
import kotlin.math.*

sealed class ShapeResult {
    data class StraightLine(val start: StrokePoint, val end: StrokePoint) : ShapeResult()
    data class Ellipse(val centerX: Float, val centerY: Float, val radiusX: Float, val radiusY: Float) : ShapeResult()
    data class Rectangle(val left: Float, val top: Float, val right: Float, val bottom: Float) : ShapeResult()
    data class SmoothPolygon(val vertices: List<StrokePoint>) : ShapeResult()
}

object ShapeSnapDetector {

    fun detectShape(points: List<StrokePoint>): ShapeResult? {
        if (points.size < 6) return null

        val start = points.first()
        val end = points.last()
        val endpointDist = start.distanceTo(end)

        var totalPathLength = 0f
        for (i in 0 until points.size - 1) {
            totalPathLength += points[i].distanceTo(points[i + 1])
        }

        // Test 1: Straight Line
        // If the path length is close to the straight chord distance, it's a line
        val straightnessRatio = endpointDist / totalPathLength.coerceAtLeast(1f)
        if (straightnessRatio > 0.90f) {
            return ShapeResult.StraightLine(start, end)
        }

        // Test 2: Closed loop (Circle, Ellipse, Rectangle)
        val isClosed = (endpointDist / totalPathLength) < 0.20f || endpointDist < 50f
        if (isClosed) {
            var minX = Float.MAX_VALUE
            var minY = Float.MAX_VALUE
            var maxX = Float.MIN_VALUE
            var maxY = Float.MIN_VALUE

            for (p in points) {
                if (p.x < minX) minX = p.x
                if (p.x > maxX) maxX = p.x
                if (p.y < minY) minY = p.y
                if (p.y > maxY) maxY = p.y
            }

            val centerX = (minX + maxX) / 2f
            val centerY = (minY + maxY) / 2f
            val radiusX = (maxX - minX) / 2f
            val radiusY = (maxY - minY) / 2f

            // Radial variance test for circle/ellipse
            var radialVariance = 0f
            for (p in points) {
                val dx = (p.x - centerX) / radiusX.coerceAtLeast(1f)
                val dy = (p.y - centerY) / radiusY.coerceAtLeast(1f)
                val normalizedDist = hypot(dx, dy)
                radialVariance += abs(normalizedDist - 1.0f)
            }
            val avgRadialError = radialVariance / points.size

            if (avgRadialError < 0.25f) {
                return ShapeResult.Ellipse(centerX, centerY, radiusX, radiusY)
            } else {
                return ShapeResult.Rectangle(minX, minY, maxX, maxY)
            }
        }

        return null
    }
}
