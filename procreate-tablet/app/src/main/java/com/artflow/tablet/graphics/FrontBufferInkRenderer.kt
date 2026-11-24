package com.artflow.tablet.graphics

import androidx.graphics.lowlatency.BufferInfo
import androidx.graphics.lowlatency.GLFrontBufferedRenderer
import androidx.graphics.opengl.egl.EGLManager
import com.artflow.tablet.brush.BrushConfig
import com.artflow.tablet.brush.StrokePoint
import com.artflow.tablet.model.CanvasDocument

class FrontBufferInkRenderer(
    private val document: CanvasDocument,
    private val compositor: () -> LayerCompositor?,
    private val activeBrushConfig: () -> BrushConfig,
    private val activeColorRgba: () -> FloatArray
) : GLFrontBufferedRenderer.Callback<StrokePoint> {

    override fun onDrawFrontBufferedLayer(
        eglManager: EGLManager,
        width: Int,
        height: Int,
        bufferInfo: BufferInfo,
        transform: FloatArray,
        param: StrokePoint
    ) {
        val comp = compositor() ?: return
        val layer = document.activeLayer
        val config = activeBrushConfig()
        val color = activeColorRgba()
        comp.renderStamp(
            layer = layer,
            point = param,
            config = config,
            colorRgba = color,
            frontBufferFbo = bufferInfo.frameBufferId,
            bufferWidth = width,
            bufferHeight = height
        )
    }

    override fun onDrawMultiBufferedLayer(
        eglManager: EGLManager,
        width: Int,
        height: Int,
        bufferInfo: BufferInfo,
        transform: FloatArray,
        params: Collection<StrokePoint>
    ) {
        val comp = compositor() ?: return
        // Full composition pass on stroke completion or viewport invalidation
        comp.compositeAllLayersToTarget(
            document = document,
            targetFbo = bufferInfo.frameBufferId,
            targetWidth = width,
            targetHeight = height
        )
    }
}
