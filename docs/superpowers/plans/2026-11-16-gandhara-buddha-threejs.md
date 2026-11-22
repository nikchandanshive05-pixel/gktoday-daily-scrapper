# Gandhara 3D Buddha Statue in Three.js - Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

Build a museum-grade interactive 3D Gandhara Buddha statue in Three.js with authentic Greco-Buddhist iconography, procedural dark-schist stone shaders, Hellenistic drapery, interactive studio lighting, camera viewpoints, and external model drag-and-drop support.

## User Review Required

> [!NOTE]
> The implementation uses a dual-engine architectural approach:
> 1. A self-contained, high-detail procedural 3D sculpture capturing all quintessential Gandhara characteristics (ushnisha wavy hair, sanghati drapery folds, Dhyana mudra, lotus pedestal, and prabhamandala halo).
> 2. An integrated GLTF/GLB/OBJ loader allowing any external museum photogrammetry scan to be loaded into the scene seamlessly.

---

## Proposed File Architecture

- `gandhara-buddha/index.html`: Main HTML entry point with modern responsive UI, viewport, lighting/material controls, camera bookmarks, and audio controls.
- `gandhara-buddha/js/sculpture.js`: Procedural geometry builder implementing Gandharan sculptural elements (head, ushnisha, wavy hair coils, elongated ears, torso, sanghati robe with sinusoidal drapery folds, arms in Dhyana mudra, lotus base, halo).
- `gandhara-buddha/js/materials.js`: PBR material factory generating authentic Gandhara Grey-Schist (with quartz/mica fleck procedural noise), Weathered Sandstone, Ancient Patinated Bronze, and Terracotta/Stucco presets using HTML5 canvas-generated normal and roughness maps.
- `gandhara-buddha/js/scene.js`: Three.js scene setup, camera, renderer with tone mapping, studio 3-point lighting rig, environment map, dust particle atmosphere, and orbit controls.
- `gandhara-buddha/js/audio.js`: Synthesized Web Audio API ambient temple soundscape (Tibetan singing bowl resonance and soft harmonic drone, 0 external dependencies).
- `gandhara-buddha/js/app.js`: Main coordinator tying together UI, interaction events, preset switching, camera transitions, and GLTF/OBJ drag-and-drop loader.

---

## Verification Strategy

- Run local HTTP server (`python -m http.server 8080` or Node static server).
- Verify rendering in browser without CORS errors or broken CDN assets.
- Verify smooth 60fps orbit controls and responsive resizing across desktop and mobile.
- Verify all 4 material presets (Schist, Sandstone, Patinated Bronze, Stucco).
- Verify camera transition animations (Face/Ushnisha, Torso/Drapery, Hands/Mudra, Full View).
- Verify drag-and-drop GLB/OBJ loading functionality.

---

## Tasks

- [ ] **Task 1: Project Scaffolding and HTML Structure**
  - Create `gandhara-buddha/index.html` with modern minimalist dark museum theme, UI overlay for controls, camera buttons, material selector, and canvas container.
  - Set up CDN links for Three.js (r128+), OrbitControls, and GLTFLoader/OBJLoader.

- [ ] **Task 2: PBR Texture & Procedural Material Engine (`materials.js`)**
  - Implement programmatic noise generation for normal maps, height maps, and roughness maps on off-screen HTML5 canvases.
  - Implement 4 Gandhara material archetypes: Dark Quartz-Mica Schist (signature Gandharan stone), Mathura Red/Yellow Sandstone, Ancient Gilded Bronze, and Hadda Stucco.

- [ ] **Task 3: Anatomical & Iconographic Sculptural Geometry (`sculpture.js`)**
  - Construct Greco-Buddhist head with serene classical features, urna forehead mark, and pendulous earlobes.
  - Generate the iconic Gandharan wavy hair in concentric rhythmic tiers ascending into the ushnisha topknot.
  - Model seated meditative torso with classical sanghati robe featuring harmonic drapery folds across shoulders, chest, and lap.
  - Construct hands in Dhyana Mudra (meditation gesture) and legs in Padmasana.
  - Add carved multi-tiered Lotus Throne (*Padmapitha*) and radiate circular Halo (*Prabhamandala*).

- [ ] **Task 4: Three.js Environment, Studio Lighting & Atmosphere (`scene.js`, `audio.js`)**
  - Configure ACESFilmicToneMapping, soft shadows, and directional key/fill/rim lights replicating museum exhibition spotlights.
  - Add soft atmospheric floating particle field.
  - Implement procedural singing bowl sound synthesis via Web Audio API.

- [ ] **Task 5: Main Application Coordinator & Interactions (`app.js`)**
  - Bind UI buttons to camera presets with smooth tweening.
  - Implement light rotation and turntable auto-rotate toggle.
  - Implement drag-and-drop file upload for external `.glb`, `.gltf`, or `.obj` museum scans.

- [ ] **Task 6: Verification and Launch**
  - Test server launch and inspect visual aesthetics.
  - Ensure zero console errors, smooth interaction, and authentic Gandharan art hallmarks.
