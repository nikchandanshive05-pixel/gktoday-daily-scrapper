package com.artflow.tablet.features

import org.junit.Assert.*
import org.junit.Test

class DropFillTest {

    @Test
    fun testDropFillFloodFill() {
        val width = 10
        val height = 10
        val pixels = IntArray(width * height) { 0xFFFFFFFF.toInt() } // White canvas

        // Draw a black box barrier from (2,2) to (7,7)
        for (x in 2..7) {
            pixels[2 * width + x] = 0xFF000000.toInt()
            pixels[7 * width + x] = 0xFF000000.toInt()
        }
        for (y in 2..7) {
            pixels[y * width + 2] = 0xFF000000.toInt()
            pixels[y * width + 7] = 0xFF000000.toInt()
        }

        val redFill = 0xFFFF0000.toInt()

        // Fill inside the closed box at (4,4) with zero dilation for clean boundary verification
        val filled = DropFillEngine.floodFill(
            pixels = pixels,
            width = width,
            height = height,
            startX = 4,
            startY = 4,
            fillColor = redFill,
            tolerance = 0.05f,
            dilatePixels = 0
        )

        assertTrue(filled)
        // Inside should be filled red
        assertEquals(redFill, pixels[4 * width + 4])
        assertEquals(redFill, pixels[3 * width + 3])
        // Outside should remain untouched white
        assertEquals(0xFFFFFFFF.toInt(), pixels[0 * width + 0])
        // Barrier should remain black
        assertEquals(0xFF000000.toInt(), pixels[2 * width + 2])
    }
}
