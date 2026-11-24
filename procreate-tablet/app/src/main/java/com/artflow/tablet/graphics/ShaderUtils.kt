package com.artflow.tablet.graphics

import android.opengl.GLES30
import android.util.Log

object ShaderUtils {
    private const val TAG = "ShaderUtils"

    fun compileShader(type: Int, shaderCode: String): Int {
        val shader = GLES30.glCreateShader(type)
        if (shader == 0) {
            Log.e(TAG, "Error creating shader of type: $type")
            return 0
        }

        GLES30.glShaderSource(shader, shaderCode)
        GLES30.glCompileShader(shader)

        val compileStatus = IntArray(1)
        GLES30.glGetShaderiv(shader, GLES30.GL_COMPILE_STATUS, compileStatus, 0)
        if (compileStatus[0] == 0) {
            val log = GLES30.glGetShaderInfoLog(shader)
            Log.e(TAG, "Shader compilation error: $log")
            GLES30.glDeleteShader(shader)
            return 0
        }
        return shader
    }

    fun createProgram(vertexCode: String, fragmentCode: String): Int {
        val vertexShader = compileShader(GLES30.GL_VERTEX_SHADER, vertexCode)
        if (vertexShader == 0) return 0

        val fragmentShader = compileShader(GLES30.GL_FRAGMENT_SHADER, fragmentCode)
        if (fragmentShader == 0) {
            GLES30.glDeleteShader(vertexShader)
            return 0
        }

        val program = GLES30.glCreateProgram()
        if (program == 0) {
            Log.e(TAG, "Error creating GL program")
            return 0
        }

        GLES30.glAttachShader(program, vertexShader)
        GLES30.glAttachShader(program, fragmentShader)
        GLES30.glLinkProgram(program)

        val linkStatus = IntArray(1)
        GLES30.glGetProgramiv(program, GLES30.GL_LINK_STATUS, linkStatus, 0)
        if (linkStatus[0] == 0) {
            val log = GLES30.glGetProgramInfoLog(program)
            Log.e(TAG, "Program linking error: $log")
            GLES30.glDeleteProgram(program)
            return 0
        }
        return program
    }

    const val BRUSH_STAMP_VERTEX_SHADER = """#version 300 es
        layout(location = 0) in vec2 aPosition;
        layout(location = 1) in vec2 aTexCoord;
        uniform mat4 uProjectionMatrix;
        out vec2 vTexCoord;

        void main() {
            vTexCoord = aTexCoord;
            gl_Position = uProjectionMatrix * vec4(aPosition, 0.0, 1.0);
        }
    """

    const val BRUSH_STAMP_FRAGMENT_SHADER = """#version 300 es
        precision mediump float;
        in vec2 vTexCoord;
        uniform vec4 uColor;
        uniform float uHardness;
        out vec4 fragColor;

        void main() {
            vec2 center = vec2(0.5, 0.5);
            float dist = distance(vTexCoord, center) * 2.0; // 0.0 at center, 1.0 at edge
            if (dist > 1.0) {
                discard;
            }

            // Falloff based on brush hardness
            float alpha = 1.0;
            if (dist > uHardness) {
                alpha = 1.0 - smoothstep(uHardness, 1.0, dist);
            }

            // Premultiplied alpha output
            float finalAlpha = uColor.a * alpha;
            fragColor = vec4(uColor.rgb * finalAlpha, finalAlpha);
        }
    """

    const val LAYER_COMPOSITE_VERTEX_SHADER = """#version 300 es
        layout(location = 0) in vec2 aPosition;
        layout(location = 1) in vec2 aTexCoord;
        out vec2 vTexCoord;

        void main() {
            vTexCoord = aTexCoord;
            gl_Position = vec4(aPosition, 0.0, 1.0);
        }
    """

    const val LAYER_COMPOSITE_FRAGMENT_SHADER = """#version 300 es
        precision mediump float;
        in vec2 vTexCoord;
        uniform sampler2D uLayerTexture;
        uniform float uOpacity;
        uniform int uBlendMode;
        uniform bool uIsClippingMask;
        uniform sampler2D uMaskTexture;
        out vec4 fragColor;

        // Premultiplied blend functions
        vec3 blendNormal(vec3 base, vec3 blend) {
            return blend;
        }

        vec3 blendMultiply(vec3 base, vec3 blend) {
            return base * blend;
        }

        vec3 blendScreen(vec3 base, vec3 blend) {
            return 1.0 - (1.0 - base) * (1.0 - blend);
        }

        vec3 blendOverlay(vec3 base, vec3 blend) {
            return mix(2.0 * base * blend, 1.0 - 2.0 * (1.0 - base) * (1.0 - blend), step(0.5, base));
        }

        void main() {
            vec4 src = texture(uLayerTexture, vTexCoord);
            if (src.a <= 0.001) {
                discard;
            }

            if (uIsClippingMask) {
                vec4 mask = texture(uMaskTexture, vTexCoord);
                src *= mask.a;
            }

            float appliedAlpha = src.a * uOpacity;
            fragColor = vec4(src.rgb * uOpacity, appliedAlpha);
        }
    """
}
