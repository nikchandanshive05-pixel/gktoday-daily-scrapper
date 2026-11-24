package com.artflow.tablet.features

import com.artflow.tablet.brush.StrokePoint
import org.junit.Assert.*
import org.junit.Test
import kotlin.math.cos
import kotlin.math.sin

class ShapeSnapTest {

    @Test
    fun testStraightLineDetection() {
        val points = mutableListOf<StrokePoint>()
        for (i in 0..20) {
            points.add(StrokePoint(x = i * 10f, y = i * 10f))
        }

        val shape = ShapeSnapDetector.detectShape(points)
        assertNotNull(shape)
        assertTrue("Expected straight line result", shape is ShapeResult.StraightLine)

        val line = shape as ShapeResult.StraightLine
        assertEquals(0f, line.start.x, 0.01f)
        assertEquals(200f, line.end.x, 0.01f)
    }

    @Test
    fun testCircleDetection() {
        val points = mutableListOf<StrokePoint>()
        val centerX = 150f
        val centerY = 150f
        val radius = 50f

        for (i in 0..30) {
            val angle = (i.toFloat() / 30f) * 2f * Math.PI.toFloat()
            val x = centerX + radius * cos(angle)
            val y = centerY + radius * sin(angle)
            points.add(StrokePoint(x, y))
        }

        val shape = ShapeSnapDetector.detectShape(points)
        assertNotNull(shape)
        assertTrue("Expected ellipse/circle result", shape is ShapeResult.Ellipse)

        val ellipse = shape as ShapeResult.Ellipse
        assertEquals(centerX, ellipse.centerX, 2.0f)
        assertEquals(centerY, ellipse.centerY, 2.0f)
        assertEquals(radius, ellipse.radiusX, 2.0f)
        assertEquals(radius, ellipse.radiusY, 2.0f)
    }
}
