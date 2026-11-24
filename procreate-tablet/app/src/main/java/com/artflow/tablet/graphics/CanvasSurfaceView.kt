package com.artflow.tablet.graphics

import android.content.Context
import android.graphics.PixelFormat
import android.util.AttributeSet
import android.view.MotionEvent
import android.view.SurfaceHolder
import android.view.SurfaceView
import androidx.graphics.opengl.GLFrontBufferedRenderer
import com.artflow.tablet.brush.BrushConfig
import com.artflow.tablet.brush.BrushType
import com.artflow.tablet.brush.StrokePoint
import com.artflow.tablet.input.TouchInputHandler
import com.artflow.tablet.model.CanvasDocument

class CanvasSurfaceView @JvmOverloads constructor(
    context: Context,
    attrs: AttributeSet? = null
) : SurfaceView(context, attrs), SurfaceHolder.Callback {

    var document: CanvasDocument = CanvasDocument(width = 2560, height = 1600)
    var compositor: LayerCompositor? = null
    var frontBufferedRenderer: GLFrontBufferedRenderer<StrokePoint>? = null
    var touchInputHandler: TouchInputHandler? = null

    var activeBrushConfig: BrushConfig = BrushConfig.createDefault(BrushType.STUDIO_PEN)
    var activeColorRgba: FloatArray = floatArrayOf(0.1f, 0.1f, 0.1f, 1.0f) // Dark charcoal default

    init {
        holder.addCallback(this)
        holder.setFormat(PixelFormat.TRANSLUCENT)
        isFocusable = true
        isFocusableInTouchMode = true
    }

    override fun surfaceCreated(holder: SurfaceHolder) {
        val comp = LayerCompositor(document.width, document.height)
        comp.initializeGl()
        compositor = comp

        val inkCallback = FrontBufferInkRenderer(
            document = document,
            compositor = comp,
            activeBrushConfig = { activeBrushConfig },
            activeColorRgba = { activeColorRgba }
        )

        frontBufferedRenderer = GLFrontBufferedRenderer(this, inkCallback)
    }

    override fun surfaceChanged(holder: SurfaceHolder, format: Int, width: Int, height: Int) {
        // Redraw canvas stack
        frontBufferedRenderer?.commit()
    }

    override fun surfaceDestroyed(holder: SurfaceHolder) {
        frontBufferedRenderer?.release(true)
        frontBufferedRenderer = null
        compositor?.release()
        compositor = null
    }

    override fun onTouchEvent(event: MotionEvent): Boolean {
        // Request low-latency unbuffered dispatch from the OS
        requestUnbufferedDispatch(event)

        val handler = touchInputHandler
        if (handler != null) {
            return handler.onTouchEvent(event)
        }
        return super.onTouchEvent(event)
    }

    fun renderStampToFrontBuffer(point: StrokePoint) {
        frontBufferedRenderer?.renderFrontBufferedLayer(point)
    }

    fun commitCompletedStroke() {
        frontBufferedRenderer?.commit()
    }

    fun requestRedraw() {
        frontBufferedRenderer?.commit()
    }
}
