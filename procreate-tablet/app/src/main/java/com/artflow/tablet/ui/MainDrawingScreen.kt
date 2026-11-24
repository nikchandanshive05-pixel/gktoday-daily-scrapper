package com.artflow.tablet.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp
import androidx.compose.ui.viewinterop.AndroidView
import com.artflow.tablet.brush.BrushConfig
import com.artflow.tablet.brush.BrushType
import com.artflow.tablet.brush.StrokePoint
import com.artflow.tablet.features.DropFillEngine
import com.artflow.tablet.features.ShapeResult
import com.artflow.tablet.features.ShapeSnapDetector
import com.artflow.tablet.graphics.CanvasSurfaceView
import com.artflow.tablet.input.*
import com.artflow.tablet.model.BlendMode
import com.artflow.tablet.model.CanvasDocument
import com.artflow.tablet.ui.components.*
import com.artflow.tablet.ui.theme.ProDarkBackground
import com.artflow.tablet.undo.UndoCommand
import com.artflow.tablet.undo.UndoManager

@Composable
fun MainDrawingScreen() {
    val document = remember { CanvasDocument(width = 2560, height = 1600) }
    val undoManager = remember { UndoManager(maxUndoSteps = 30) }

    var activeTool by remember { mutableStateOf(BrushType.STUDIO_PEN) }
    var brushSizePercent by remember { mutableFloatStateOf(0.15f) }
    var brushOpacityPercent by remember { mutableFloatStateOf(1.0f) }
    var activeColor by remember { mutableStateOf(Color(0xFF1A1A1A)) }
    var inputMode by remember { mutableStateOf(InputMode.FINGER_DRAWING) }

    var showLayersPanel by remember { mutableStateOf(false) }
    var showColorPicker by remember { mutableStateOf(false) }

    var canUndo by remember { mutableStateOf(false) }
    var canRedo by remember { mutableStateOf(false) }
    var layersVersion by remember { mutableIntStateOf(0) }

    var surfaceViewRef by remember { mutableStateOf<CanvasSurfaceView?>(null) }

    val activeBrushConfig = remember(activeTool, brushSizePercent, brushOpacityPercent) {
        val config = BrushConfig.createDefault(activeTool)
        config.size = 1f + (brushSizePercent * 120f)
        config.opacity = brushOpacityPercent
        config
    }

    val activeColorRgba = remember(activeColor) {
        floatArrayOf(activeColor.red, activeColor.green, activeColor.blue, activeColor.alpha)
    }

    // Keep SurfaceView synced with compose state
    LaunchedEffect(activeBrushConfig, activeColorRgba) {
        surfaceViewRef?.let { sv ->
            sv.activeBrushConfig = activeBrushConfig
            sv.activeColorRgba = activeColorRgba
        }
    }

    Box(
        modifier = Modifier.fillMaxSize()
    ) {
        // 1. Full-Screen OpenGL Canvas SurfaceView
        AndroidView(
            modifier = Modifier.fillMaxSize(),
            factory = { context ->
                CanvasSurfaceView(context).apply {
                    this.document = document
                    this.activeBrushConfig = activeBrushConfig
                    this.activeColorRgba = activeColorRgba

                    val gestureListener = CanvasGestureListener(object : CanvasGestureCallback {
                        override fun onTwoFingerTapUndo() {
                            if (undoManager.canUndo) {
                                undoManager.popUndo()
                                canUndo = undoManager.canUndo
                                canRedo = undoManager.canRedo
                                requestRedraw()
                            }
                        }

                        override fun onThreeFingerTapRedo() {
                            if (undoManager.canRedo) {
                                undoManager.popRedo()
                                canUndo = undoManager.canUndo
                                canRedo = undoManager.canRedo
                                requestRedraw()
                            }
                        }

                        override fun onCanvasTransform(deltaX: Float, deltaY: Float, scaleFactor: Float, rotationDegrees: Float) {
                            requestRedraw()
                        }

                        override fun onResetViewport() {
                            requestRedraw()
                        }
                    })

                    val inputHandler = TouchInputHandler(
                        inputMode = inputMode,
                        gestureListener = gestureListener,
                        drawingCallback = object : DrawingInteractionCallback {
                            override fun onStrokeStart(point: StrokePoint) {
                                renderStampToFrontBuffer(point)
                            }

                            override fun onStrokePoint(point: StrokePoint) {
                                renderStampToFrontBuffer(point)
                            }

                            override fun onStrokeEnd(point: StrokePoint) {
                                commitCompletedStroke()
                                canUndo = true
                                canRedo = false
                            }

                            override fun onStrokeCancelled() {
                                requestRedraw()
                            }

                            override fun onSteadyHoldDetected(points: List<StrokePoint>) {
                                val detected = ShapeSnapDetector.detectShape(points)
                                if (detected != null) {
                                    // ShapeSnap auto-snapped!
                                    commitCompletedStroke()
                                }
                            }
                        }
                    )

                    this.touchInputHandler = inputHandler
                    surfaceViewRef = this
                }
            },
            update = { view ->
                view.touchInputHandler?.inputMode = inputMode
            }
        )

        // 2. Top Navigation Bar (Procreate minimalist toolbar)
        TopActionBar(
            activeTool = activeTool,
            onToolSelected = {
                activeTool = it
                showLayersPanel = false
                showColorPicker = false
            },
            activeColor = activeColor,
            onColorChipClick = {
                showColorPicker = !showColorPicker
                showLayersPanel = false
            },
            onLayersClick = {
                showLayersPanel = !showLayersPanel
                showColorPicker = false
            },
            layerCount = document.layers.size,
            inputMode = inputMode,
            onToggleInputMode = {
                inputMode = if (inputMode == InputMode.STYLUS_ONLY) {
                    InputMode.FINGER_DRAWING
                } else {
                    InputMode.STYLUS_ONLY
                }
            },
            onUndoClick = {
                if (undoManager.canUndo) {
                    undoManager.popUndo()
                    canUndo = undoManager.canUndo
                    canRedo = undoManager.canRedo
                    surfaceViewRef?.requestRedraw()
                }
            },
            onRedoClick = {
                if (undoManager.canRedo) {
                    undoManager.popRedo()
                    canUndo = undoManager.canUndo
                    canRedo = undoManager.canRedo
                    surfaceViewRef?.requestRedraw()
                }
            },
            canUndo = canUndo,
            canRedo = canRedo,
            modifier = Modifier.align(Alignment.TopCenter)
        )

        // 3. Iconic Left Edge Dynamic Sliders (Size & Opacity)
        EdgePillSliderGroup(
            brushSizePercent = brushSizePercent,
            brushOpacityPercent = brushOpacityPercent,
            onSizeChange = { brushSizePercent = it },
            onOpacityChange = { brushOpacityPercent = it },
            onEyedropperClick = {
                // Quick eyedropper toggle
            },
            modifier = Modifier.align(Alignment.CenterStart)
        )

        // 4. Floating Layer Panel (Top Right)
        if (showLayersPanel) {
            LayerPanel(
                layers = document.layers,
                activeLayerIndex = document.activeLayerIndex,
                onSelectLayer = {
                    document.activeLayerIndex = it
                    layersVersion++
                },
                onAddLayer = {
                    if (document.canAddLayer()) {
                        val added = document.addLayer()
                        if (added != null) {
                            undoManager.pushCommand(UndoCommand.LayerAdded(added, document.activeLayerIndex))
                            canUndo = true
                            layersVersion++
                            surfaceViewRef?.requestRedraw()
                        }
                    }
                },
                onDeleteLayer = { idx ->
                    val removed = document.removeLayer(idx)
                    if (removed != null) {
                        undoManager.pushCommand(UndoCommand.LayerRemoved(removed, idx))
                        canUndo = true
                        layersVersion++
                        surfaceViewRef?.requestRedraw()
                    }
                },
                onToggleVisibility = { idx ->
                    val layer = document.layers[idx]
                    layer.isVisible = !layer.isVisible
                    layersVersion++
                    surfaceViewRef?.requestRedraw()
                },
                onOpacityChange = { idx, op ->
                    val layer = document.layers[idx]
                    layer.opacity = op
                    layersVersion++
                    surfaceViewRef?.requestRedraw()
                },
                onBlendModeChange = { idx, mode ->
                    val layer = document.layers[idx]
                    layer.blendMode = mode
                    layersVersion++
                    surfaceViewRef?.requestRedraw()
                },
                onToggleAlphaLock = { idx ->
                    val layer = document.layers[idx]
                    layer.isAlphaLocked = !layer.isAlphaLocked
                    layersVersion++
                },
                onClose = { showLayersPanel = false },
                modifier = Modifier
                    .align(Alignment.TopEnd)
                    .padding(top = 64.dp, end = 16.dp)
            )
        }

        // 5. Floating Color Disc Picker (Top Right)
        if (showColorPicker) {
            ColorDiscPicker(
                currentColor = activeColor,
                onColorChanged = { activeColor = it },
                onClose = { showColorPicker = false },
                modifier = Modifier
                    .align(Alignment.TopEnd)
                    .padding(top = 64.dp, end = 16.dp)
            )
        }
    }
}
