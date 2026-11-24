# Android Procreate-Style Tablet App Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a production-ready, native Android tablet digital illustration application featuring an ultra-low latency S-Pen/touch drawing engine, Procreate-style minimalist UI, dynamic edge sliders, multi-layer compositing, gesture undo/redo, DropFill, ShapeSnap, and `.canvas` export, compiling to an installable APK.

**Architecture:** The application pairs a Jetpack Compose tablet interface (borderless canvas, docked size/opacity pill sliders, top action bar, and layer/color sheets) with a high-performance OpenGL ES 3.0 rendering core using `androidx.graphics.opengl.GLFrontBufferedRenderer`. S-Pen input is predicted and projected directly to the display front buffer for `<15ms` response, while committed strokes are composited through custom GLSL blend shaders onto an off-heap memory-budgeted layer stack.

**Tech Stack:** Kotlin 1.9+, Android SDK (minSdk 29, targetSdk 34), Jetpack Compose, AndroidX Graphics (`androidx.graphics:graphics-core`), AndroidX Motion Prediction, OpenGL ES 3.0 / GLSL, LZ4 compression, Coroutines & Flow.

**Spec:** `docs/superpowers/specs/2026-11-24-android-procreate-clone-design.md`

---

## Global Constraints
- Target platform: Android Tablets (minSdk 29, targetSdk 34).
- Input precision: Active stylus (`TOOL_TYPE_STYLUS` / Samsung S-Pen) with 4096 pressure levels and tilt (`AXIS_TILT`), plus toggleable finger drawing mode.
- Latency floor: Motion-to-photon latency `<20ms` via `GLFrontBufferedRenderer` and `MotionEventPredictor`.
- Pure clean-room terminology: **ShapeSnap** (not QuickShape), **DropFill** (not ColorDrop), **StrokeStabilizer** (not Streamline).
- Memory budget: Never allocate unmanaged monolithic textures without consulting `ActivityManager.getMemoryInfo()` and `ComponentCallbacks2.onTrimMemory()`.

## Review Focus
1. **Palm Slips during Drawing:** When an artist rests their palm on the screen while inking with the S-Pen, the engine must discard finger events with zero canvas paint drops or gesture jitter.
2. **Second Finger Landing Mid-Stroke (Finger Mode):** If drawing in Finger Mode and a second finger touches down, the in-flight stroke must immediately cancel cleanly via `ACTION_CANCEL` without leaving orphan dots.
3. **Rapid Multi-Layer Memory Pressure:** Loading or creating 16+ layers on a device with limited free RAM must gracefully throttle layer caps or swap hidden layer textures to disk rather than throwing an unhandled `OutOfMemoryError`.
4. **Front-Buffer to Back-Buffer Blend Handshake:** Strokes drawn in Normal mode on the front buffer must resolve correctly against non-Normal layer blend modes (e.g. Multiply, Color Dodge) upon stroke commit without visual popping.
5. **DropFill Contour Leakage & White Halos:** Filling an anti-aliased hand-drawn shape must not leak through diagonal 1px gaps and must dilate 1.5–2px to eliminate white fringing around stroke borders.

---

## Task Decomposition

### Task 1: Project Scaffolding & Build Configuration
**Files:**
- Create: `procreate-tablet/settings.gradle.kts`
- Create: `procreate-tablet/build.gradle.kts`
- Create: `procreate-tablet/app/build.gradle.kts`
- Create: `procreate-tablet/app/src/main/AndroidManifest.xml`
- Create: `procreate-tablet/app/src/main/res/values/strings.xml`
- Create: `procreate-tablet/app/src/main/res/values/themes.xml`

**Interfaces:**
- Produces: Gradle buildable Android application module with Jetpack Compose, OpenGL ES, and AndroidX Graphics dependencies.

- [ ] **Step 1: Create Gradle settings and root build configuration**
- [ ] **Step 2: Configure `app/build.gradle.kts` with minSdk 29, targetSdk 34, Compose compiler, and `androidx.graphics:graphics-core:1.0.1`**
- [ ] **Step 3: Define AndroidManifest.xml with hardware acceleration, largeHeap, tablet landscape default, and full-screen theme**
- [ ] **Step 4: Verify Gradle sync / build scripts**

---

### Task 2: Core Data Models & Command-Based Undo History
**Files:**
- Create: `procreate-tablet/app/src/main/java/com/artflow/tablet/model/CanvasDocument.kt`
- Create: `procreate-tablet/app/src/main/java/com/artflow/tablet/model/ArtLayer.kt`
- Create: `procreate-tablet/app/src/main/java/com/artflow/tablet/model/BlendMode.kt`
- Create: `procreate-tablet/app/src/main/java/com/artflow/tablet/undo/UndoCommand.kt`
- Create: `procreate-tablet/app/src/main/java/com/artflow/tablet/undo/UndoManager.kt`
- Test: `procreate-tablet/app/src/test/java/com/artflow/tablet/undo/UndoManagerTest.kt`

**Interfaces:**
- Produces: `CanvasDocument`, `ArtLayer`, `BlendMode`, `UndoManager` managing stack of `UndoCommand` (pixel deltas and structural changes).

- [ ] **Step 1: Write unit test for `UndoManager` pushing pixel deltas and structural actions (layer reorder, add, opacity)**
- [ ] **Step 2: Run test to verify failure**
- [ ] **Step 3: Implement `BlendMode` enum with GLSL equations (Normal, Multiply, Screen, Overlay, Add, ColorDodge)**
- [ ] **Step 4: Implement `ArtLayer` and `CanvasDocument` with layer limit calculations**
- [ ] **Step 5: Implement `UndoManager` with maximum 30-step cap and direct byte buffer storage**
- [ ] **Step 6: Run test to verify pass**

---

### Task 3: Brush Engine & Spline Math with StrokeStabilizer
**Files:**
- Create: `procreate-tablet/app/src/main/java/com/artflow/tablet/brush/BrushType.kt`
- Create: `procreate-tablet/app/src/main/java/com/artflow/tablet/brush/BrushConfig.kt`
- Create: `procreate-tablet/app/src/main/java/com/artflow/tablet/brush/StrokePoint.kt`
- Create: `procreate-tablet/app/src/main/java/com/artflow/tablet/brush/CatmullRomSpline.kt`
- Create: `procreate-tablet/app/src/main/java/com/artflow/tablet/brush/StrokeStabilizer.kt`
- Test: `procreate-tablet/app/src/test/java/com/artflow/tablet/brush/BrushSplineTest.kt`

**Interfaces:**
- Consumes: Raw `MotionEvent` coordinates, pressure, and tilt.
- Produces: Interpolated stamp points with smoothed positions, dynamic radius, and alpha for 6B Pencil, Studio Pen, Soft Airbrush, and Flat Brush.

- [ ] **Step 1: Write unit test for `CatmullRomSpline` and `StrokeStabilizer` smoothing calculations**
- [ ] **Step 2: Run test to verify failure**
- [ ] **Step 3: Implement `StrokePoint` with x, y, pressure, tilt, and timestamp**
- [ ] **Step 4: Implement `CatmullRomSpline` curve interpolation generator**
- [ ] **Step 5: Implement `StrokeStabilizer` with dual-path smoothing (raw predicted front stroke vs committed smoothed spline)**
- [ ] **Step 6: Define `BrushConfig` presets for Pencil, Inking Studio Pen, Airbrush, Flat Brush, Smudge, and Eraser**
- [ ] **Step 7: Run test to verify pass**

---

### Task 4: Low-Latency OpenGL ES 3.0 Rendering Core
**Files:**
- Create: `procreate-tablet/app/src/main/java/com/artflow/tablet/graphics/ShaderUtils.kt`
- Create: `procreate-tablet/app/src/main/java/com/artflow/tablet/graphics/LayerCompositor.kt`
- Create: `procreate-tablet/app/src/main/java/com/artflow/tablet/graphics/FrontBufferInkRenderer.kt`
- Create: `procreate-tablet/app/src/main/java/com/artflow/tablet/graphics/CanvasSurfaceView.kt`

**Interfaces:**
- Consumes: `CanvasDocument`, `ArtLayer`, `GLFrontBufferedRenderer.Callback`.
- Produces: Double-buffered full-screen OpenGL ES canvas surface with front-buffer projection and FBO multi-layer compositing.

- [ ] **Step 1: Implement `ShaderUtils` compiling vertex and fragment shaders with error checking**
- [ ] **Step 2: Implement GLSL shaders for brush stamp rasterization and multi-layer premultiplied alpha blend modes**
- [ ] **Step 3: Implement `LayerCompositor` managing layer FBO textures, ping-pong smudge buffers, and PBO async readback**
- [ ] **Step 4: Implement `FrontBufferInkRenderer` with `GLFrontBufferedRenderer` and `MotionEventPredictor`**
- [ ] **Step 5: Implement `CanvasSurfaceView` binding front-buffered pipeline to Android surface lifecycle**

---

### Task 5: Touch, S-Pen & Gesture Disambiguation Engine
**Files:**
- Create: `procreate-tablet/app/src/main/java/com/artflow/tablet/input/InputMode.kt`
- Create: `procreate-tablet/app/src/main/java/com/artflow/tablet/input/CanvasGestureListener.kt`
- Create: `procreate-tablet/app/src/main/java/com/artflow/tablet/input/TouchInputHandler.kt`
- Test: `procreate-tablet/app/src/test/java/com/artflow/tablet/input/GestureDisambiguationTest.kt`

**Interfaces:**
- Consumes: Android `MotionEvent` stream from `CanvasSurfaceView`.
- Produces: Dispatched drawing events, viewport transform matrix (pan/zoom/rotate), and discrete Undo/Redo gesture triggers.

- [ ] **Step 1: Write unit tests verifying 2-finger tap (<200ms, <10dp) triggers Undo, 3-finger triggers Redo, and palm rejection discards touches in Stylus-Only mode**
- [ ] **Step 2: Run test to verify failure**
- [ ] **Step 3: Implement `CanvasGestureListener` evaluating multi-touch pan, pinch-to-zoom, and rotation matrix**
- [ ] **Step 4: Implement `TouchInputHandler` with strict S-Pen hardware detection, S-Pen button toggle, `FLAG_CANCELED` handling, and mode switching**
- [ ] **Step 5: Run test to verify pass**

---

### Task 6: Creative Feature Algorithms: ShapeSnap & DropFill
**Files:**
- Create: `procreate-tablet/app/src/main/java/com/artflow/tablet/features/ShapeSnapDetector.kt`
- Create: `procreate-tablet/app/src/main/java/com/artflow/tablet/features/DropFillEngine.kt`
- Test: `procreate-tablet/app/src/test/java/com/artflow/tablet/features/ShapeSnapTest.kt`
- Test: `procreate-tablet/app/src/test/java/com/artflow/tablet/features/DropFillTest.kt`

**Interfaces:**
- Consumes: Stroke point collection (for ShapeSnap) and target coordinates + color (for DropFill).
- Produces: Geometric primitive replacement (straight line, ellipse, rect) and dilated flood-filled layer region.

- [ ] **Step 1: Write unit tests for ShapeSnap point cloud classification (line vs ellipse vs rect)**
- [ ] **Step 2: Write unit test for DropFill scanline flood-fill and 1.5px dilation**
- [ ] **Step 3: Implement `ShapeSnapDetector` with 400ms steady hold detector and geometric fitting algorithms**
- [ ] **Step 4: Implement `DropFillEngine` with scanline fill, color tolerance threshold, and boundary dilation**
- [ ] **Step 5: Run tests to verify pass**

---

### Task 7: Procreate-Style Jetpack Compose Tablet Interface
**Files:**
- Create: `procreate-tablet/app/src/main/java/com/artflow/tablet/ui/theme/Color.kt`
- Create: `procreate-tablet/app/src/main/java/com/artflow/tablet/ui/theme/Theme.kt`
- Create: `procreate-tablet/app/src/main/java/com/artflow/tablet/ui/components/EdgePillSlider.kt`
- Create: `procreate-tablet/app/src/main/java/com/artflow/tablet/ui/components/TopActionBar.kt`
- Create: `procreate-tablet/app/src/main/java/com/artflow/tablet/ui/components/LayerPanel.kt`
- Create: `procreate-tablet/app/src/main/java/com/artflow/tablet/ui/components/ColorDiscPicker.kt`
- Create: `procreate-tablet/app/src/main/java/com/artflow/tablet/ui/MainDrawingScreen.kt`
- Create: `procreate-tablet/app/src/main/java/com/artflow/tablet/MainActivity.kt`

**Interfaces:**
- Consumes: StateFlow from drawing ViewModel (`CanvasDocument`, active tool, brush size, opacity, selected color).
- Produces: Polished full-screen tablet UI matching Procreate's dark minimalist layout.

- [ ] **Step 1: Build `Theme.kt` with dark charcoal palette, borderless styling, and typography**
- [ ] **Step 2: Build `EdgePillSlider.kt` (interactive vertical pill sliders for Brush Size and Opacity with square center Eyedropper)**
- [ ] **Step 3: Build `TopActionBar.kt` with Gallery, Actions, Transform, Brush, Smudge, Eraser, Layers, Color Chip, and Stylus/Finger toggle**
- [ ] **Step 4: Build `LayerPanel.kt` popup with reorderable list, visibility eye toggle, opacity slider, alpha lock, and blend mode picker**
- [ ] **Step 5: Build `ColorDiscPicker.kt` with circular hue ring, inner saturation square, hex input, and palette swatches**
- [ ] **Step 6: Assemble `MainDrawingScreen.kt` layering Compose controls over the `CanvasSurfaceView`**
- [ ] **Step 7: Wire `MainActivity.kt` with edge-to-edge system insets and immersive mode**

---

### Task 8: Document Storage, Crash Recovery & Export Pipeline
**Files:**
- Create: `procreate-tablet/app/src/main/java/com/artflow/tablet/storage/DocumentSerializer.kt`
- Create: `procreate-tablet/app/src/main/java/com/artflow/tablet/storage/WriteAheadJournal.kt`
- Create: `procreate-tablet/app/src/main/java/com/artflow/tablet/storage/ExportEngine.kt`
- Test: `procreate-tablet/app/src/test/java/com/artflow/tablet/storage/DocumentStorageTest.kt`

**Interfaces:**
- Consumes: `CanvasDocument` and active layer bitmaps.
- Produces: `.canvas` project zip archives, crash-recovery WAL logs, and PNG/JPEG/PSD exported files.

- [ ] **Step 1: Write test for saving and restoring `.canvas` zip package with layer metadata and PNGs**
- [ ] **Step 2: Implement `DocumentSerializer` packing/unpacking `manifest.json`, `thumbnail.png`, and layers**
- [ ] **Step 3: Implement `WriteAheadJournal` logging completed strokes to disk for crash recovery**
- [ ] **Step 4: Implement `ExportEngine` flattening visible layers to PNG or JPEG with quality setting**
- [ ] **Step 5: Run tests to verify pass**

---

### Task 9: APK Compilation, Packaging & Verification
**Files:**
- Create: `procreate-tablet/.github/workflows/build-tablet-apk.yml`
- Script: Local and CI build verification

**Interfaces:**
- Produces: Signed debug/release APK ready for one-click installation on Android tablet.

- [ ] **Step 1: Set up GitHub Actions CI workflow for compiling the APK artifact**
- [ ] **Step 2: Run build pipeline and verify zero compilation errors**
- [ ] **Step 3: Verify APK structure (`unzip -l app-debug.apk`) ensuring lib, assets, and AndroidManifest are valid**
- [ ] **Step 4: Deliver the APK file to `build_apk/procreate-tablet-debug.apk` with installation instructions**
