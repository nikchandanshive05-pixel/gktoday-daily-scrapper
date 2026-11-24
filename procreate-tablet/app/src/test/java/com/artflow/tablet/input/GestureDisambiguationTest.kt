package com.artflow.tablet.input

import org.junit.Assert.*
import org.junit.Test

class GestureDisambiguationTest {

    @Test
    fun testTwoFingerTapTriggersUndo() {
        var undoCalled = false
        var redoCalled = false

        val listener = CanvasGestureListener(object : CanvasGestureCallback {
            override fun onTwoFingerTapUndo() { undoCalled = true }
            override fun onThreeFingerTapRedo() { redoCalled = true }
            override fun onCanvasTransform(deltaX: Float, deltaY: Float, scaleFactor: Float, rotationDegrees: Float) {}
            override fun onResetViewport() {}
        })

        listener.onTouchDown(pointerCount = 2, x = 100f, y = 100f)
        val handled = listener.onPointersUp(pointerCountEnding = 2, totalTravel = 5f)

        assertTrue(handled)
        assertTrue(undoCalled)
        assertFalse(redoCalled)
    }

    @Test
    fun testThreeFingerTapTriggersRedo() {
        var redoCalled = false

        val listener = CanvasGestureListener(object : CanvasGestureCallback {
            override fun onTwoFingerTapUndo() {}
            override fun onThreeFingerTapRedo() { redoCalled = true }
            override fun onCanvasTransform(deltaX: Float, deltaY: Float, scaleFactor: Float, rotationDegrees: Float) {}
            override fun onResetViewport() {}
        })

        listener.onTouchDown(pointerCount = 3, x = 150f, y = 150f)
        val handled = listener.onPointersUp(pointerCountEnding = 3, totalTravel = 8f)

        assertTrue(handled)
        assertTrue(redoCalled)
    }

    @Test
    fun testPanPinchDoesNotTriggerUndo() {
        var undoCalled = false
        var transformCalled = false

        val listener = CanvasGestureListener(object : CanvasGestureCallback {
            override fun onTwoFingerTapUndo() { undoCalled = true }
            override fun onThreeFingerTapRedo() {}
            override fun onCanvasTransform(deltaX: Float, deltaY: Float, scaleFactor: Float, rotationDegrees: Float) {
                transformCalled = true
            }
            override fun onResetViewport() {}
        })

        listener.onTouchDown(pointerCount = 2, x = 100f, y = 100f)
        listener.onTwoPointerMove(100f, 100f, 300f, 300f)
        listener.onTwoPointerMove(120f, 120f, 350f, 350f)
        // High travel distance (e.g. 150px)
        val handled = listener.onPointersUp(pointerCountEnding = 2, totalTravel = 150f)

        assertFalse("Long pinch should not trigger quick tap undo", handled)
        assertFalse(undoCalled)
        assertTrue(transformCalled)
    }
}
