package com.artflow.tablet.graphics

import android.opengl.GLES30
import androidx.graphics.opengl.GLFrontBufferedRenderer
import androidx.graphics.opengl.GLRenderer
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
        eglManager: GLSurfaceControlManager,
        width: Int,
        height: Int,
        param: StrokePoint
    ) {
        // Fast front-buffer wet ink stroke rendering directly to display overlay
        val layer = document.activeLayer
        val config = activeBrushConfig()
        val color = activeColorRgba()
        compositor.renderStamp(layer, param, config, color)
    }

    override fun onDrawDoubleBufferedLayer(
        eglManager: GLSurfaceControlManager,
        width: Int,
        height: Int,
        params: Collection<StrokePoint>
    ) {
        // Full composition pass on stroke completion or viewport invalidation
        compositor.compositeAllLayersToTarget(document, 0)
    }
}

// Typealias bridge for callback signatures
typealias GLSurfaceControlManager = GLRenderer.RenderCallback
