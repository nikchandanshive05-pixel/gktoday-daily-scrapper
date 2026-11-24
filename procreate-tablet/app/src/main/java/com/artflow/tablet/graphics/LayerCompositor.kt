package com.artflow.tablet.graphics

import android.opengl.GLES30
import android.opengl.Matrix
import android.util.Log
import com.artflow.tablet.brush.BrushConfig
import com.artflow.tablet.brush.StrokePoint
import com.artflow.tablet.model.ArtLayer
import com.artflow.tablet.model.CanvasDocument
import java.nio.ByteBuffer
import java.nio.ByteOrder
import java.nio.FloatBuffer

class LayerCompositor(val width: Int, val height: Int) {
    private val TAG = "LayerCompositor"

    private var brushProgram: Int = 0
    private var compositeProgram: Int = 0

    private val projectionMatrix = FloatArray(16)
    private var quadVao: Int = 0
    private var quadVbo: Int = 0

    // Framebuffer storage mapped to layer ID
    private val layerFbos = mutableMapOf<String, Int>()
    private val layerTextures = mutableMapOf<String, Int>()

    // PBO for asynchronous pixel readback without pipeline stalls
    private var readbackPbo: Int = 0

    init {
        Matrix.orthoM(projectionMatrix, 0, 0f, width.toFloat(), height.toFloat(), 0f, -1f, 1f)
    }

    fun initializeGl() {
        brushProgram = ShaderUtils.createProgram(
            ShaderUtils.BRUSH_STAMP_VERTEX_SHADER,
            ShaderUtils.BRUSH_STAMP_FRAGMENT_SHADER
        )
        compositeProgram = ShaderUtils.createProgram(
            ShaderUtils.LAYER_COMPOSITE_VERTEX_SHADER,
            ShaderUtils.LAYER_COMPOSITE_FRAGMENT_SHADER
        )

        setupQuadBuffers()
        setupPbo()
    }

    private fun setupQuadBuffers() {
        val quadVertices = floatArrayOf(
            // Positions (NDC)  // TexCoords
            -1.0f,  1.0f,       0.0f, 1.0f,
            -1.0f, -1.0f,       0.0f, 0.0f,
             1.0f, -1.0f,       1.0f, 0.0f,

            -1.0f,  1.0f,       0.0f, 1.0f,
             1.0f, -1.0f,       1.0f, 0.0f,
             1.0f,  1.0f,       1.0f, 1.0f
        )

        val vao = IntArray(1)
        val vbo = IntArray(1)
        GLES30.glGenVertexArrays(1, vao, 0)
        GLES30.glGenBuffers(1, vbo, 0)

        quadVao = vao[0]
        quadVbo = vbo[0]

        val buffer = ByteBuffer.allocateDirect(quadVertices.size * 4)
            .order(ByteOrder.nativeOrder())
            .asFloatBuffer()
            .put(quadVertices)
        buffer.position(0)

        GLES30.glBindVertexArray(quadVao)
        GLES30.glBindBuffer(GLES30.GL_ARRAY_BUFFER, quadVbo)
        GLES30.glBufferData(GLES30.GL_ARRAY_BUFFER, quadVertices.size * 4, buffer, GLES30.GL_STATIC_DRAW)

        GLES30.glEnableVertexAttribArray(0)
        GLES30.glVertexAttribPointer(0, 2, GLES30.GL_FLOAT, false, 4 * 4, 0)

        GLES30.glEnableVertexAttribArray(1)
        GLES30.glVertexAttribPointer(1, 2, GLES30.GL_FLOAT, false, 4 * 4, 2 * 4)

        GLES30.glBindVertexArray(0)
    }

    private fun setupPbo() {
        val pbos = IntArray(1)
        GLES30.glGenBuffers(1, pbos, 0)
        readbackPbo = pbos[0]

        // Allocate PBO buffer matching viewport RGBA
        GLES30.glBindBuffer(GLES30.GL_PIXEL_PACK_BUFFER, readbackPbo)
        GLES30.glBufferData(
            GLES30.GL_PIXEL_PACK_BUFFER,
            width * height * 4,
            null,
            GLES30.GL_STREAM_READ
        )
        GLES30.glBindBuffer(GLES30.GL_PIXEL_PACK_BUFFER, 0)
    }

    fun ensureLayerTexture(layer: ArtLayer): Int {
        if (layerTextures.containsKey(layer.id)) {
            return layerTextures[layer.id]!!
        }

        val textures = IntArray(1)
        val fbos = IntArray(1)
        GLES30.glGenTextures(1, textures, 0)
        GLES30.glGenFramebuffers(1, fbos, 0)

        val texId = textures[0]
        val fboId = fbos[0]

        GLES30.glBindTexture(GLES30.GL_TEXTURE_2D, texId)
        GLES30.glTexImage2D(
            GLES30.GL_TEXTURE_2D, 0, GLES30.GL_RGBA8, width, height,
            0, GLES30.GL_RGBA, GLES30.GL_UNSIGNED_BYTE, null
        )
        GLES30.glTexParameteri(GLES30.GL_TEXTURE_2D, GLES30.GL_TEXTURE_MIN_FILTER, GLES30.GL_LINEAR)
        GLES30.glTexParameteri(GLES30.GL_TEXTURE_2D, GLES30.GL_TEXTURE_MAG_FILTER, GLES30.GL_LINEAR)
        GLES30.glTexParameteri(GLES30.GL_TEXTURE_2D, GLES30.GL_TEXTURE_WRAP_S, GLES30.GL_CLAMP_TO_EDGE)
        GLES30.glTexParameteri(GLES30.GL_TEXTURE_2D, GLES30.GL_TEXTURE_WRAP_T, GLES30.GL_CLAMP_TO_EDGE)

        GLES30.glBindFramebuffer(GLES30.GL_FRAMEBUFFER, fboId)
        GLES30.glFramebufferTexture2D(
            GLES30.GL_FRAMEBUFFER, GLES30.GL_COLOR_ATTACHMENT0,
            GLES30.GL_TEXTURE_2D, texId, 0
        )

        // Clear newly created layer to transparent
        GLES30.glClearColor(0f, 0f, 0f, 0f)
        GLES30.glClear(GLES30.GL_COLOR_BUFFER_BIT)
        GLES30.glBindFramebuffer(GLES30.GL_FRAMEBUFFER, 0)

        layerTextures[layer.id] = texId
        layerFbos[layer.id] = fboId
        layer.textureId = texId
        return texId
    }

    fun renderStamp(
        layer: ArtLayer,
        point: StrokePoint,
        config: BrushConfig,
        colorRgba: FloatArray
    ) {
        val fbo = layerFbos[layer.id] ?: return
        val radius = config.calculateRadius(point.pressure)
        val alpha = config.calculateAlpha(point.pressure)

        GLES30.glBindFramebuffer(GLES30.GL_FRAMEBUFFER, fbo)
        GLES30.glViewport(0, 0, width, height)

        GLES30.glEnable(GLES30.GL_BLEND)
        // Premultiplied alpha blending equation
        GLES30.glBlendFunc(GLES30.GL_ONE, GLES30.GL_ONE_MINUS_SRC_ALPHA)

        GLES30.glUseProgram(brushProgram)

        val uProj = GLES30.glGetUniformLocation(brushProgram, "uProjectionMatrix")
        val uColor = GLES30.glGetUniformLocation(brushProgram, "uColor")
        val uHardness = GLES30.glGetUniformLocation(brushProgram, "uHardness")

        GLES30.glUniformMatrix4fv(uProj, 1, false, projectionMatrix, 0)
        GLES30.glUniform4f(uColor, colorRgba[0], colorRgba[1], colorRgba[2], colorRgba[3] * alpha)
        GLES30.glUniform1f(uHardness, config.hardness)

        // Draw point quad
        val x0 = point.x - radius
        val y0 = point.y - radius
        val x1 = point.x + radius
        val y1 = point.y + radius

        val stampVertices = floatArrayOf(
            x0, y1,   0f, 1f,
            x0, y0,   0f, 0f,
            x1, y0,   1f, 0f,

            x0, y1,   0f, 1f,
            x1, y0,   1f, 0f,
            x1, y1,   1f, 1f
        )

        val vbo = IntArray(1)
        GLES30.glGenBuffers(1, vbo, 0)
        val buffer = ByteBuffer.allocateDirect(stampVertices.size * 4)
            .order(ByteOrder.nativeOrder())
            .asFloatBuffer()
            .put(stampVertices)
        buffer.position(0)

        GLES30.glBindBuffer(GLES30.GL_ARRAY_BUFFER, vbo[0])
        GLES30.glBufferData(GLES30.GL_ARRAY_BUFFER, stampVertices.size * 4, buffer, GLES30.GL_DYNAMIC_DRAW)

        GLES30.glEnableVertexAttribArray(0)
        GLES30.glVertexAttribPointer(0, 2, GLES30.GL_FLOAT, false, 4 * 4, 0)

        GLES30.glEnableVertexAttribArray(1)
        GLES30.glVertexAttribPointer(1, 2, GLES30.GL_FLOAT, false, 4 * 4, 2 * 4)

        GLES30.glDrawArrays(GLES30.GL_TRIANGLES, 0, 6)

        GLES30.glDeleteBuffers(1, vbo, 0)
        GLES30.glBindFramebuffer(GLES30.GL_FRAMEBUFFER, 0)
    }

    fun compositeAllLayersToTarget(document: CanvasDocument, targetFbo: Int = 0) {
        GLES30.glBindFramebuffer(GLES30.GL_FRAMEBUFFER, targetFbo)
        GLES30.glViewport(0, 0, width, height)

        // Clear canvas with background color
        val bg = document.backgroundColor
        val r = ((bg shr 16) and 0xFF) / 255f
        val g = ((bg shr 8) and 0xFF) / 255f
        val b = (bg and 0xFF) / 255f
        GLES30.glClearColor(r, g, b, 1.0f)
        GLES30.glClear(GLES30.GL_COLOR_BUFFER_BIT)

        GLES30.glEnable(GLES30.GL_BLEND)
        GLES30.glBlendFunc(GLES30.GL_ONE, GLES30.GL_ONE_MINUS_SRC_ALPHA)

        GLES30.glUseProgram(compositeProgram)
        GLES30.glBindVertexArray(quadVao)

        val uTexLoc = GLES30.glGetUniformLocation(compositeProgram, "uLayerTexture")
        val uOpacityLoc = GLES30.glGetUniformLocation(compositeProgram, "uOpacity")
        val uBlendLoc = GLES30.glGetUniformLocation(compositeProgram, "uBlendMode")
        val uIsClipLoc = GLES30.glGetUniformLocation(compositeProgram, "uIsClippingMask")
        val uMaskTexLoc = GLES30.glGetUniformLocation(compositeProgram, "uMaskTexture")

        var previousLayerTex = 0

        for (layer in document.layers) {
            if (!layer.isVisible) continue
            val texId = ensureLayerTexture(layer)

            GLES30.glActiveTexture(GLES30.GL_TEXTURE0)
            GLES30.glBindTexture(GLES30.GL_TEXTURE_2D, texId)
            GLES30.glUniform1i(uTexLoc, 0)

            GLES30.glUniform1f(uOpacityLoc, layer.opacity)
            GLES30.glUniform1i(uBlendLoc, layer.blendMode.ordinal)

            if (layer.isClippingMask && previousLayerTex != 0) {
                GLES30.glUniform1i(uIsClipLoc, 1)
                GLES30.glActiveTexture(GLES30.GL_TEXTURE1)
                GLES30.glBindTexture(GLES30.GL_TEXTURE_2D, previousLayerTex)
                GLES30.glUniform1i(uMaskTexLoc, 1)
            } else {
                GLES30.glUniform1i(uIsClipLoc, 0)
            }

            GLES30.glDrawArrays(GLES30.GL_TRIANGLES, 0, 6)
            previousLayerTex = texId
        }

        GLES30.glBindVertexArray(0)
        GLES30.glBindFramebuffer(GLES30.GL_FRAMEBUFFER, 0)
    }

    fun release() {
        for (fbo in layerFbos.values) {
            GLES30.glDeleteFramebuffers(1, intArrayOf(fbo), 0)
        }
        for (tex in layerTextures.values) {
            GLES30.glDeleteTextures(1, intArrayOf(tex), 0)
        }
        layerFbos.clear()
        layerTextures.clear()
        if (quadVao != 0) GLES30.glDeleteVertexArrays(1, intArrayOf(quadVao), 0)
        if (quadVbo != 0) GLES30.glDeleteBuffers(1, intArrayOf(quadVbo), 0)
        if (readbackPbo != 0) GLES30.glDeleteBuffers(1, intArrayOf(readbackPbo), 0)
        if (brushProgram != 0) GLES30.glDeleteProgram(brushProgram)
        if (compositeProgram != 0) GLES30.glDeleteProgram(compositeProgram)
    }
}
