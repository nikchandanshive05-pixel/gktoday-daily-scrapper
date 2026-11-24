package com.artflow.tablet.graphics

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
        bufferWidth: Int,
        bufferHeight: Int,
        transform: FloatArray,
        param: StrokePoint
    ) {
        // Fast front-buffer wet ink stroke rendering directly to display overlay
        val layer = document.activeLayer
        val config = activeBrushConfig()
        val color = activeColorRgba()
        compositor.renderStamp(layer, param, config, color)
    }

    override fun onDrawDoubleBufferedLayer(
        eglManager: EGLManager,
        bufferWidth: Int,
        bufferHeight: Int,
        transform: FloatArray,
        params: Collection<StrokePoint>
    ) {
        // Full composition pass on stroke completion or viewport invalidation
        compositor.compositeAllLayersToTarget(document, 0)
    }
}
