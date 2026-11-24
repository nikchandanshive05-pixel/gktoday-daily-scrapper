package com.artflow.tablet.input

import android.os.Handler
import android.os.Looper
import android.view.MotionEvent
import com.artflow.tablet.brush.StrokePoint
import com.artflow.tablet.brush.StrokeStabilizer

interface DrawingInteractionCallback {
    fun onStrokeStart(point: StrokePoint)
    fun onStrokePoint(point: StrokePoint)
    fun onStrokeEnd(point: StrokePoint)
    fun onStrokeCancelled()
    fun onSteadyHoldDetected(points: List<StrokePoint>)
}

class TouchInputHandler(
    var inputMode: InputMode = InputMode.FINGER_DRAWING,
    val gestureListener: CanvasGestureListener,
    val drawingCallback: DrawingInteractionCallback
) {
    var isStylusButtonPressed: Boolean = false
        private set

    private var isCurrentlyDrawing = false
    private val strokePoints = mutableListOf<StrokePoint>()
    private val stabilizer = StrokeStabilizer(streamline = 0.5f)

    private val holdHandler = Handler(Looper.getMainLooper())
    private var holdRunnable: Runnable? = null
    private var lastPointX = 0f
    private var lastPointY = 0f

    fun onTouchEvent(event: MotionEvent): Boolean {
        // Discard system-flagged palm cancellation events
        if (event.actionMasked == MotionEvent.ACTION_CANCEL ||
            (event.flags and MotionEvent.FLAG_CANCELED) != 0) {
            cancelActiveStroke()
            return true
        }

        val toolType = event.getToolType(0)
        val isStylus = toolType == MotionEvent.TOOL_TYPE_STYLUS || toolType == MotionEvent.TOOL_TYPE_ERASER
        isStylusButtonPressed = (event.buttonState and MotionEvent.BUTTON_STYLUS_PRIMARY) != 0

        val pointerCount = event.pointerCount

        // 2+ pointers: Always viewport navigation / multi-touch gestures
        if (pointerCount >= 2) {
            if (isCurrentlyDrawing) {
                // Second finger landed mid-stroke: cancel stroke cleanly to prevent stray paint blobs
                cancelActiveStroke()
            }

            when (event.actionMasked) {
                MotionEvent.ACTION_POINTER_DOWN -> {
                    gestureListener.onTouchDown(pointerCount, event.x, event.y)
                }
                MotionEvent.ACTION_MOVE -> {
                    gestureListener.onTwoPointerMove(
                        event.getX(0), event.getY(0),
                        event.getX(1), event.getY(1)
                    )
                }
                MotionEvent.ACTION_POINTER_UP, MotionEvent.ACTION_UP -> {
                    gestureListener.onPointersUp(pointerCount)
                }
            }
            return true
        }

        // Single pointer handling
        val x = event.x
        val y = event.y
        val pressure = if (isStylus) event.pressure.coerceIn(0.01f, 1.0f) else 0.5f
        val tilt = if (isStylus) event.getAxisValue(MotionEvent.AXIS_TILT) else 0f
        val orientation = if (isStylus) event.getAxisValue(MotionEvent.AXIS_ORIENTATION) else 0f
        val currentPoint = StrokePoint(x, y, pressure, tilt, orientation, event.eventTime)

        val shouldDraw = isStylus || (inputMode == InputMode.FINGER_DRAWING)

        if (!shouldDraw) {
            // Stylus-Only mode with single finger touch: ignored for painting (palm rejection)
            return false
        }

        when (event.actionMasked) {
            MotionEvent.ACTION_DOWN -> {
                isCurrentlyDrawing = true
                strokePoints.clear()
                stabilizer.reset()

                val smoothed = stabilizer.processPoint(currentPoint)
                strokePoints.add(smoothed)
                drawingCallback.onStrokeStart(smoothed)

                scheduleHoldDetection(x, y)
                lastPointX = x
                lastPointY = y
                return true
            }

            MotionEvent.ACTION_MOVE -> {
                if (!isCurrentlyDrawing) return false

                val smoothed = stabilizer.processPoint(currentPoint)
                strokePoints.add(smoothed)
                drawingCallback.onStrokePoint(smoothed)

                // If user moves pen significantly, reset hold detection
                if (Math.hypot((x - lastPointX).toDouble(), (y - lastPointY).toDouble()) > 15.0) {
                    scheduleHoldDetection(x, y)
                    lastPointX = x
                    lastPointY = y
                }
                return true
            }

            MotionEvent.ACTION_UP -> {
                cancelHoldDetection()
                if (isCurrentlyDrawing) {
                    val finalPoint = stabilizer.processPoint(currentPoint)
                    strokePoints.add(finalPoint)
                    drawingCallback.onStrokeEnd(finalPoint)
                    isCurrentlyDrawing = false
                }
                return true
            }
        }

        return false
    }

    private fun cancelActiveStroke() {
        cancelHoldDetection()
        if (isCurrentlyDrawing) {
            isCurrentlyDrawing = false
            strokePoints.clear()
            drawingCallback.onStrokeCancelled()
        }
    }

    private fun scheduleHoldDetection(x: Float, y: Float) {
        cancelHoldDetection()
        val runnable = Runnable {
            if (isCurrentlyDrawing && strokePoints.size > 5) {
                drawingCallback.onSteadyHoldDetected(strokePoints.toList())
            }
        }
        holdRunnable = runnable
        holdHandler.postDelayed(runnable, 400L) // 400ms threshold for ShapeSnap
    }

    private fun cancelHoldDetection() {
        holdRunnable?.let { holdHandler.removeCallbacks(it) }
        holdRunnable = null
    }
}
