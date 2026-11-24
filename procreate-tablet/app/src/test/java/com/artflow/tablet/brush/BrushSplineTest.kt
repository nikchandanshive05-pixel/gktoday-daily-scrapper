package com.artflow.tablet.brush

import org.junit.Assert.*
import org.junit.Test

class BrushSplineTest {

    @Test
    fun testStrokePointInterpolation() {
        val p1 = StrokePoint(x = 0f, y = 0f, pressure = 0.2f)
        val p2 = StrokePoint(x = 100f, y = 100f, pressure = 0.8f)

        assertEquals(141.42f, p1.distanceTo(p2), 0.05f)

        val mid = p1.interpolate(p2, 0.5f)
        assertEquals(50f, mid.x, 0.01f)
        assertEquals(50f, mid.y, 0.01f)
        assertEquals(0.5f, mid.pressure, 0.01f)
    }

    @Test
    fun testCatmullRomSplineEndpoints() {
        val p0 = StrokePoint(0f, 0f)
        val p1 = StrokePoint(10f, 20f)
        val p2 = StrokePoint(50f, 60f)
        val p3 = StrokePoint(100f, 100f)

        val start = CatmullRomSpline.interpolatePoint(p0, p1, p2, p3, 0f)
        assertEquals(p1.x, start.x, 0.01f)
        assertEquals(p1.y, start.y, 0.01f)

        val end = CatmullRomSpline.interpolatePoint(p0, p1, p2, p3, 1f)
        assertEquals(p2.x, end.x, 0.01f)
        assertEquals(p2.y, end.y, 0.01f)
    }

    @Test
    fun testStrokeStabilizerDampening() {
        val stabilizer = StrokeStabilizer(streamline = 0.8f)

        val p1 = StrokePoint(0f, 0f)
        val p2 = StrokePoint(100f, 0f)

        val res1 = stabilizer.processPoint(p1)
        assertEquals(0f, res1.x, 0.01f)

        val res2 = stabilizer.processPoint(p2)
        // With streamline 0.8, alpha is 0.2, so res2.x should be significantly less than 100
        assertTrue("Stabilizer should dampen rapid jump", res2.x < 50f)
        assertTrue("Stabilizer should advance forward", res2.x > 0f)
    }

    @Test
    fun testBrushConfigPressureCurves() {
        val pen = BrushConfig.createDefault(BrushType.STUDIO_PEN)
        pen.size = 20f

        val radiusLowPressure = pen.calculateRadius(0.1f)
        val radiusHighPressure = pen.calculateRadius(1.0f)

        assertTrue(radiusLowPressure < radiusHighPressure)
        assertEquals(10f, radiusHighPressure, 0.1f)
    }
}
