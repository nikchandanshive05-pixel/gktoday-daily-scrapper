package com.artflow.tablet.graphics

import androidx.graphics.lowlatency.BufferInfo
import androidx.graphics.lowlatency.GLFrontBufferedRenderer
import androidx.graphics.opengl.egl.EGLManager
import com.artflow.tablet.brush.BrushConfig
import com.artflow.tablet.brush.StrokePoint
import com.artflow.tablet.model.CanvasDocument

class FrontBufferInkRenderer(
    private val document: CanvasDocument,
    private val compositor: LayerCompositor,
    private val activeBrushConfig: () -> BrushConfig,
    private val activeColorRgba: () -> FloatArray
) : GLFrontBufferedRenderer.Callback<StrokePoint> {

    override fun onDrawFrontBufferedLayer(
        eglManager: EGLManager,
        bufferInfo: BufferInfo,
        transform: FloatArray,
        param: StrokePoint
    ) {
        val layer = document.activeLayer
        val config = activeBrushConfig()
        val color = activeColorRgba()
        compositor.renderStamp(layer, param, config, color)
    }

    override fun onDrawDoubleBufferedLayer(
        eglManager: EGLManager,
        bufferInfo: BufferInfo,
        transform: FloatArray,
        params: Collection<StrokePoint>
    ) {
        compositor.compositeAllLayersToTarget(document, 0)
    }
}
