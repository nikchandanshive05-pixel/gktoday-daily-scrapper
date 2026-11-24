package com.artflow.tablet.undo

import java.util.ArrayDeque

class UndoManager(private val maxUndoSteps: Int = 30) {
    private val undoStack = ArrayDeque<UndoCommand>()
    private val redoStack = ArrayDeque<UndoCommand>()

    val canUndo: Boolean
        get() = undoStack.isNotEmpty()

    val canRedo: Boolean
        get() = redoStack.isNotEmpty()

    val undoCount: Int
        get() = undoStack.size

    val redoCount: Int
        get() = redoStack.size

    fun pushCommand(command: UndoCommand) {
        if (undoStack.size >= maxUndoSteps) {
            undoStack.removeFirst()
        }
        undoStack.addLast(command)
        redoStack.clear()
    }

    fun popUndo(): UndoCommand? {
        if (undoStack.isEmpty()) return null
        val cmd = undoStack.removeLast()
        redoStack.addLast(cmd)
        return cmd
    }

    fun popRedo(): UndoCommand? {
        if (redoStack.isEmpty()) return null
        val cmd = redoStack.removeLast()
        undoStack.addLast(cmd)
        return cmd
    }

    fun clear() {
        undoStack.clear()
        redoStack.clear()
    }
}
