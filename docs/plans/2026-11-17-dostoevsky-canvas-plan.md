# Dostoevsky Canvas Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create an exhaustive, novelistic Marathi literary canvas (in the style of Achyut Godbole's 'Zhapurza') on Fyodor Dostoevsky and compile it into a publication-grade, monochrome A4 PDF using Typst.

**Architecture:** Monolithic Typst compilation pipeline where `dostoevsky_canvas.typ` houses all 7 exhaustive narrative chapters, authentic letters, contemporary literary clashes, psychological breakdowns, chronological summary table, timeless quotes, reflection questions, and a Python compiler script with strict UTF-8 handling.

**Tech Stack:** Typst 0.15.1, Python 3, Tiro Devanagari Marathi + Times New Roman + Nirmala UI font stack.

**Spec:** `docs/specs/2026-11-17-dostoevsky-canvas-design.md`

## Global Constraints
- Strict monochrome palette: text `#000000`, table header `luma(240)`, hairline dividers `0.5pt + luma(180)`, blockquotes `stroke: (left: 2pt + black), fill: luma(248)`.
- Typst 0.15+ syntax: `context { counter(page).get().first() }`, single scalar table alignments.
- Pure Devanagari narrative with zero cluttering parenthetical English words in running body sentences.
- 7 comprehensive chapters covering youth, mock execution, Siberian katorga, gambling addiction & Anna, major novels, Pushkin speech & death, synthesis/table/quotes/questions.

## Review Focus
- Proper rendering of Devanagari conjuncts and matras without decomposition.
- Natural page flow without forced premature pagebreaks except for major logical divisions.
- Zero compile errors with Typst 0.15.1.
- Complete fidelity to Achyut Godbole's novelistic, poignant, and gripping Marathi style.

---

### Task 1: Environment & Test Typst Runner Setup
**Files:**
- Create: `scripts/compile_dostoevsky.py`

- [ ] **Step 1: Create Python runner with UTF-8 encoding**
- [ ] **Step 2: Verify runner with test typst snippet**

### Task 2: Draft Master Typst Document (`dostoevsky_canvas.typ`)
**Files:**
- Create: `dostoevsky_canvas.typ`

- [ ] **Step 1: Define page geometry, typography, running headers, and styling**
- [ ] **Step 2: Implement Chapters 1 to 3 (Youth, Mock Execution, Siberian Katorga)**
- [ ] **Step 3: Implement Chapters 4 to 6 (Gambling, Major Works, Pushkin Speech & Death)**
- [ ] **Step 4: Implement Chapter 7 (Philosophy, Master Timeline Table, Quotes, Reflection Questions)**

### Task 3: Compile and Verify Output PDF
**Files:**
- Output: `dostoevsky_canvas.pdf`

- [ ] **Step 1: Run `scripts/compile_dostoevsky.py`**
- [ ] **Step 2: Verify PDF page count, layout, and visual fidelity**
