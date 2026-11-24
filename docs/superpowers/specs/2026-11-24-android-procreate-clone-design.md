# Design Document: Procreate-Style Digital Painting App for Android Tablets

**Date:** 2026-11-24  
**Author:** Antigravity & User  
**Status:** Approved Architecture Draft (Incorporating Technical Review Revisions)  
**Target Platform:** Android Tablets (minSdk 29 / Android 10+, targetSdk 34+, optimized for 90Hz/120Hz active stylus devices)

---

## 1. Intent and the "Why"
Procreate is the industry benchmark for tablet digital illustration because of its distraction-free UI, instant gesture workflow (two-finger tap undo, three-finger redo), responsive low-latency stylus engine, and fluid canvas navigation. Because Procreate is strictly locked to Apple's iOS ecosystem, Android tablet users with high-performance hardware and active styluses (e.g., Samsung S-Pen) lack a dedicated, bloat-free creative equivalent.

The goal is to build a bespoke native Android tablet application that authentically recreates the speed, feel, minimalism, and core creative workflow of Procreate with zero desktop clutter.

---

## 2. Goals, Non-Goals, and Anti-Goals

### Goals
- **Minimalist Canvas-Centric UI:** Border-to-border canvas, auto-dimming top toolbar (Gallery, Actions, Adjustments, Select, Transform, Brush, Smudge, Eraser, Layers, Active Color), and docked edge sliders for Brush Size and Brush Opacity.
- **Gesture Workflow:**
  - 2-finger single tap: Undo (discrete tap evaluated on release: `<200ms`, movement `<10dp`).
  - 3-finger single tap: Redo (evaluated on release: `<200ms`, movement `<10dp`).
  - 2-finger drag/pinch/rotate: Butter-smooth viewport transform (translation, zoom, continuous canvas rotation).
  - 2-finger quick-pinch: Reset/fit canvas to viewport.
  - ShapeSnap (clean-room QuickShape equivalent): Drawing and holding steady at stroke terminus (`>400ms`) snaps stroke into a crisp vector primitive (straight line, ellipse, rectangle, triangle).
- **Stylus & S-Pen Precision:**
  - Full Samsung S-Pen support via `MotionEvent.TOOL_TYPE_STYLUS` and `TOOL_TYPE_ERASER`.
  - Continuous pressure sensitivity (4096 levels) and tilt dynamics (`AXIS_TILT`, `AXIS_ORIENTATION`).
  - S-Pen hardware button (`BUTTON_STYLUS_PRIMARY`) mapped to quick-eyedropper or secondary eraser.
  - Dedicated toggle between **Stylus-Only Mode** (hardware-guaranteed palm rejection; fingers only navigate) and **Finger Drawing Mode** (single finger draws with velocity simulation; landing a second finger mid-stroke immediately cancels the stroke and transitions to pan/zoom).
  - Handle `ACTION_CANCEL` and `FLAG_CANCELED` explicitly to discard accidental palm slips.
- **Rendering & Low-Latency Pipeline:**
  - Ultra-low latency target (`<15ms` touch-to-screen) using `androidx.graphics.opengl.GLFrontBufferedRenderer` on `minSdk 29+`.
  - Unbuffered touch dispatch (`View.requestUnbufferedDispatch(MotionEvent)`).
  - Stroke prediction via `androidx.input.motionprediction.MotionEventPredictor` to project stroke directly under the pen nib.
  - StrokeStabilizer (clean-room Streamline): Dual-path rendering—draws raw predicted strokes into the front buffer for instantaneous visual response, then commits the smoothed Catmull-Rom spline on stroke commit to avoid smoothing lag.
- **Layer & Compositing Engine:**
  - Multi-layer stack with reordering, visibility toggle, opacity slider, Alpha Lock, and Clipping Masks.
  - Layer blend modes executed via GLSL fragment shaders with premultiplied alpha: Normal, Multiply, Screen, Overlay, Add, Darken, Lighten, Color Dodge.
  - Smudge tool using ping-pong FBO textures to sample and drag wet pigment across the active layer.
  - Basic layer transform (single-finger drag / two-finger pinch to translate, scale, and rotate selected layer contents).
- **Color Tools:**
  - Circular Color Disc / Saturation square, HSB sliders, and custom palette swatches.
  - DropFill (clean-room ColorDrop equivalent): Drag active color chip directly onto the canvas to flood-fill closed contours. Fill performed with 1–2px dilation/feathering to eliminate anti-aliasing white halos, with an optional "Sample All Layers" toggle.
- **Document Management & Persistence:**
  - Independent document sizes: Screen Size preset, 4K UHD, A4 300 DPI print preset, Square (2048×2048), and custom user dimensions.
  - Project container file format (`.canvas` / `.art` zip archive containing `manifest.json`, `thumbnail.png`, and lossless layer data).
  - Autosave with write-ahead stroke log for crash recovery.
  - Export to PNG, JPEG, and layered PSD.

### Non-Goals (v1)
- 3D model painting / USDZ import.
- Advanced timeline-based Animation Assist (planned for v2).
- Video time-lapse screen recorder (planned for v2).
- Proprietary Apple `.procreate` file decoding (we use our own open, clean-room container format).

### Anti-Goals
- **Desktop Clutter:** No floating dialog windows, complex menu bars, or desktop-style tool palettes covering artwork.
- **Input Lag / Smoothing Drag:** No lagging brush cursors trailing behind the pen nib.
- **OOM Crashes:** No uncontrolled memory allocation when working with multi-layer high-resolution documents.

---

## 3. Hardware Targets & Success Metrics
- **Target OS:** Android 10+ (API 29+), targeting Android 14+ (API 34).
- **Verified Hardware Profile:** Samsung Galaxy Tab S7 / S8 / S9 / S10 series with S-Pen (120Hz Super AMOLED / LCD).
- **Latency Metric:** `<20ms` end-to-end motion-to-photon latency measured with touch pointer location overlay / high-speed camera.
- **Frame Rate:** Sustained 90Hz / 120Hz canvas rendering during multi-touch canvas transform and high-speed inking.
- **Stability:** Zero OOM crashes across a continuous 2-hour painting session with 12+ layers at 2560×1600.

---

## 4. Architectural Specifications

### 4.1 UI Layout & Interaction Specs
1. **Canvas Viewport:** 100% full-screen immersive view (`WindowInsetsControllerCompat` hiding system bars).
2. **Top Navigation Bar:**
   - Left: `Gallery`, `Actions` (Wrench), `Adjustments` (Wand - v1.1), `Select` (Lasso - v1.1), `Transform` (Freeform arrow - v1).
   - Right: `Brush` (Paintbrush), `Smudge` (Finger), `Eraser` (Eraser), `Layers` (Double square), `Color Chip` (Circular swatch).
   - Quick Toggle: S-Pen / Finger Drawing mode switch.
3. **Edge Dynamic Sliders (Left/Right dockable):**
   - Top Slider: Brush Size (1% to 100% logarithmic scale).
   - Center Button: Quick Eyedropper toggle.
   - Bottom Slider: Brush Opacity (1% to 100%).
4. **Touch & Gesture Disambiguation:**
   - **Mode A (Stylus Only):**
     - S-Pen (`TOOL_TYPE_STYLUS` / `TOOL_TYPE_ERASER`): Inks canvas.
     - 1 Finger: Ignored for painting; used for Eyedropper if tapped on canvas.
     - 2 Fingers: Viewport pan, zoom, rotate.
     - Tap Gestures: 2-finger tap = Undo, 3-finger tap = Redo (evaluated on `ACTION_POINTER_UP` / `ACTION_UP` with `<200ms` timestamp delta and `<10dp` travel).
   - **Mode B (Finger Drawing):**
     - S-Pen: Inks with pressure/tilt.
     - 1 Finger: Inks canvas with velocity-based simulated pressure.
     - 2nd Finger touchdown mid-stroke: Cancels in-flight stroke (`ACTION_CANCEL` semantic) and smoothly promotes gesture to 2-finger viewport navigation.
   - **ShapeSnap:** Holding steady for `400ms` at stroke terminus analyzes touch points, fits to line / ellipse / polygon, and prompts interactive edit handles.

### 4.2 Rendering Engine & Low-Latency Pipeline
- **API & Pipeline:** `androidx.graphics.opengl.GLFrontBufferedRenderer` backed by OpenGL ES 3.0.
- **Front Buffer (Wet Stroke):** In-progress strokes render directly to the front buffer with `MotionEventPredictor` projection for immediate stylus feedback. Because the front buffer cannot evaluate complex underlying blend modes without dropping frames, wet strokes render in Normal blend mode and resolve to their target layer blend equation upon stroke commit.
- **Back Buffer (Compositing Pass):** When `onStrokeEnd` occurs, the committed spline is composited into the target layer texture, and the full layer stack is recomposited into the double-buffered display pipeline.
- **Smudge Pipeline:** Dual ping-pong FBOs; the active layer texture is sampled into a brush stamp shader that blends previous canvas color with current brush color, writing back to the alternate FBO.
- **Blend Modes & Color Space:** GLSL fragment shaders implement blend modes using premultiplied alpha in linear sRGB space. Clipping masks sample the alpha channel of the underlying layer texture to discard outside fragments.

### 4.3 Memory Management & Document Model
- **Document Model:** Non-device-bound. Supports document creation presets:
  - Screen Size (default matching device viewport)
  - 4K UHD (3840×2160)
  - A4 @ 300 DPI (2480×3508)
  - Square (2048×2048)
  - Custom width/height up to GPU `GL_MAX_TEXTURE_SIZE`.
- **Memory Budgeting:** Evaluated using `ActivityManager.getMemoryInfo()` and `ComponentCallbacks2.onTrimMemory()`.
  - Each 2560×1600 RGBA_8888 layer allocates ~16.4MB.
  - Active visible layers remain resident in GPU textures.
  - Inactive / hidden layers are automatically compressed and swapped to local app cache when available memory drops below 25%, and paged back in upon selection or export.

### 4.4 Global Undo/Redo Engine
- **Command Architecture:** Centralized command stack managing both pixel and structural changes (layer add, delete, reorder, visibility, opacity, transform).
- **Asynchronous Pixel Readback:** Pixel deltas are extracted using Pixel Buffer Objects (`GL_PIXEL_PACK_BUFFER`) to prevent synchronous `glReadPixels` GPU pipeline stalls.
- **Compression & Storage:** Only the dirty-bounding-rect tile deltas are extracted, compressed via LZ4, and stored in off-heap native byte buffers (`ByteBuffer.allocateDirect()`), capped at 30 global undo steps.

### 4.5 DropFill (ColorDrop Equivalent)
- **Algorithm:** Scanline flood-fill computed on a downsampled CPU mask or compute shader.
- **Dilation:** Post-fill mask is dilated by 1.5–2.0 pixels to expand beneath anti-aliased stroke outlines, preventing unsightly white fringes.
- **Scope Toggle:** "Active Layer" vs "Sample All Layers" source reference.

---

## 5. File Format & Storage Specification
- **Container Format:** Single-file archive with `.canvas` extension (ZIP container).
- **Structure:**
  ```
  my_artwork.canvas
  ├── manifest.json       (Document dimensions, DPI, color space, layer tree, blend modes, opacities)
  ├── thumbnail.png       (512×512 quick-preview rendering)
  ├── stroke_journal.wal  (Write-ahead stroke log for crash recovery)
  └── layers/
      ├── layer_0.png     (Background layer)
      ├── layer_1.png     (Line art)
      └── ...
  ```
- **Crash Recovery:** Every completed stroke appends a journal entry to `stroke_journal.wal`. Upon unexpected application termination, the app reconstructs uncommitted changes on launch.
- **Export Options:** Flattened PNG, Flattened JPEG (with quality slider), and Multi-layer Adobe Photoshop Document (PSD).
