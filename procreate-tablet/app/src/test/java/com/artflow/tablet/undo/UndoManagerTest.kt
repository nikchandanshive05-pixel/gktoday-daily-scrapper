package com.artflow.tablet.undo

import com.artflow.tablet.model.ArtLayer
import com.artflow.tablet.model.BlendMode
import org.junit.Assert.*
import org.junit.Before
import org.junit.Test
import java.nio.ByteBuffer

class UndoManagerTest {

    private lateinit var undoManager: UndoManager

    @Before
    fun setUp() {
        undoManager = UndoManager(maxUndoSteps = 5)
    }

    @Test
    fun testPushAndUndoRedo() {
        assertFalse(undoManager.canUndo)
        assertFalse(undoManager.canRedo)

        val layer = ArtLayer(name = "Test")
        val cmd = UndoCommand.LayerAdded(layer, 1)
        undoManager.pushCommand(cmd)

        assertTrue(undoManager.canUndo)
        assertFalse(undoManager.canRedo)
        assertEquals(1, undoManager.undoCount)

        val undone = undoManager.popUndo()
        assertEquals(cmd, undone)
        assertFalse(undoManager.canUndo)
        assertTrue(undoManager.canRedo)

        val redone = undoManager.popRedo()
        assertEquals(cmd, redone)
        assertTrue(undoManager.canUndo)
        assertFalse(undoManager.canRedo)
    }

    @Test
    fun testMaxUndoStepsCap() {
        for (i in 1..10) {
            val bufBefore = ByteBuffer.allocate(4)
            val bufAfter = ByteBuffer.allocate(4)
            undoManager.pushCommand(
                UndoCommand.PixelStrokeDelta("L1", 0, 0, 1, 1, bufBefore, bufAfter)
            )
        }

        assertEquals(5, undoManager.undoCount)
    }

    @Test
    fun testPushClearsRedo() {
        val layer = ArtLayer(name = "Test")
        undoManager.pushCommand(UndoCommand.LayerAdded(layer, 0))
        undoManager.popUndo()
        assertTrue(undoManager.canRedo)

        // New action should invalidate redo stack
        undoManager.pushCommand(
            UndoCommand.LayerPropertyChanged(
                "L1", 1.0f, 0.5f, BlendMode.NORMAL, BlendMode.MULTIPLY, true, true
            )
        )
        assertFalse(undoManager.canRedo)
        assertEquals(1, undoManager.undoCount)
    }
}
