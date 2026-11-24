package com.artflow.tablet.input

import kotlin.math.atan2
import kotlin.math.hypot

interface CanvasGestureCallback {
    fun onTwoFingerTapUndo()
    fun onThreeFingerTapRedo()
    fun onCanvasTransform(deltaX: Float, deltaY: Float, scaleFactor: Float, rotationDegrees: Float)
    fun onResetViewport()
}

class CanvasGestureListener(private val callback: CanvasGestureCallback) {

    private var initialPointerCount = 0
    private var gestureStartTime = 0L
    private var maxTravelDistance = 0f

    private var prevFocusX = 0f
    private var prevFocusY = 0f
    private var prevSpan = 0f
    private var prevAngle = 0f

    fun onTouchDown(pointerCount: Int, x: Float, y: Float) {
        initialPointerCount = pointerCount
        gestureStartTime = System.currentTimeMillis()
        maxTravelDistance = 0f
        prevFocusX = x
        prevFocusY = y
    }

    fun onTwoPointerMove(x1: Float, y1: Float, x2: Float, y2: Float) {
        val focusX = (x1 + x2) / 2f
        val focusY = (y1 + y2) / 2f
        val span = hypot(x2 - x1, y2 - y1)
        val angle = Math.toDegrees(atan2((y2 - y1).toDouble(), (x2 - x1).toDouble())).toFloat()

        if (prevSpan > 0f) {
            val deltaX = focusX - prevFocusX
            val deltaY = focusY - prevFocusY
            val scaleFactor = span / prevSpan
            val rotationDelta = angle - prevAngle

            maxTravelDistance += hypot(deltaX, deltaY)
            callback.onCanvasTransform(deltaX, deltaY, scaleFactor, rotationDelta)
        }

        prevFocusX = focusX
        prevFocusY = focusY
        prevSpan = span
        prevAngle = angle
    }

    fun onPointersUp(pointerCountEnding: Int, totalTravel: Float = maxTravelDistance): Boolean {
        val duration = System.currentTimeMillis() - gestureStartTime
        val isQuickTap = duration < 250L && totalTravel < 25f

        prevSpan = 0f
        prevAngle = 0f

        if (isQuickTap) {
            if (initialPointerCount == 2 || pointerCountEnding == 2) {
                callback.onTwoFingerTapUndo()
                return true
            } else if (initialPointerCount == 3 || pointerCountEnding == 3) {
                callback.onThreeFingerTapRedo()
                return true
            }
        }
        return false
    }
}
