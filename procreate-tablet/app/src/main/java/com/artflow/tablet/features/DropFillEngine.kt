package com.artflow.tablet.features

import java.util.ArrayDeque
import kotlin.math.abs

object DropFillEngine {

    fun floodFill(
        pixels: IntArray,
        width: Int,
        height: Int,
        startX: Int,
        startY: Int,
        fillColor: Int,
        tolerance: Float = 0.15f,
        dilatePixels: Int = 2
    ): Boolean {
        if (startX !in 0 until width || startY !in 0 until height) return false

        val targetColor = pixels[startY * width + startX]
        if (colorsMatch(targetColor, fillColor, 0.01f)) return false // Already matching

        val filledMask = BooleanArray(width * height)
        val queue = ArrayDeque<Pair<Int, Int>>()
        queue.add(Pair(startX, startY))
        filledMask[startY * width + startX] = true

        val dx = intArrayOf(0, 0, 1, -1)
        val dy = intArrayOf(1, -1, 0, 0)

        // Step 1: Scanline/BFS flood fill to find contiguous region within tolerance
        while (queue.isNotEmpty()) {
            val (cx, cy) = queue.removeFirst()

            for (i in 0..3) {
                val nx = cx + dx[i]
                val ny = cy + dy[i]

                if (nx in 0 until width && ny in 0 until height) {
                    val idx = ny * width + nx
                    if (!filledMask[idx]) {
                        val currentColor = pixels[idx]
                        if (colorsMatch(targetColor, currentColor, tolerance)) {
                            filledMask[idx] = true
                            queue.add(Pair(nx, ny))
                        }
                    }
                }
            }
        }

        // Step 2: Dilation pass (expands filled boundary by 1-2px beneath anti-aliased lines)
        val finalMask = if (dilatePixels > 0) {
            dilateMask(filledMask, width, height, dilatePixels)
        } else {
            filledMask
        }

        // Step 3: Apply fill color to target pixels
        for (y in 0 until height) {
            for (x in 0 until width) {
                val idx = y * width + x
                if (finalMask[idx]) {
                    pixels[idx] = fillColor
                }
            }
        }
        return true
    }

    private fun dilateMask(mask: BooleanArray, width: Int, height: Int, radius: Int): BooleanArray {
        val dilated = mask.clone()
        for (y in 0 until height) {
            for (x in 0 until width) {
                if (mask[y * width + x]) {
                    for (dy in -radius..radius) {
                        for (dx in -radius..radius) {
                            val nx = x + dx
                            val ny = y + dy
                            if (nx in 0 until width && ny in 0 until height) {
                                dilated[ny * width + nx] = true
                            }
                        }
                    }
                }
            }
        }
        return dilated
    }

    private fun colorsMatch(c1: Int, c2: Int, tolerance: Float): Boolean {
        val a1 = (c1 shr 24) and 0xFF
        val r1 = (c1 shr 16) and 0xFF
        val g1 = (c1 shr 8) and 0xFF
        val b1 = c1 and 0xFF

        val a2 = (c2 shr 24) and 0xFF
        val r2 = (c2 shr 16) and 0xFF
        val g2 = (c2 shr 8) and 0xFF
        val b2 = c2 and 0xFF

        val diffA = abs(a1 - a2) / 255.0f
        val diffR = abs(r1 - r2) / 255.0f
        val diffG = abs(g1 - g2) / 255.0f
        val diffB = abs(b1 - b2) / 255.0f

        val totalDiff = (diffA + diffR + diffG + diffB) / 4.0f
        return totalDiff <= tolerance
    }
}
