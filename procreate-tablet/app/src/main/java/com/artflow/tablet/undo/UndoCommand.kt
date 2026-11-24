package com.artflow.tablet.undo

import com.artflow.tablet.model.ArtLayer
import com.artflow.tablet.model.BlendMode
import java.nio.ByteBuffer

sealed class UndoCommand {
    data class PixelStrokeDelta(
        val layerId: String,
        val x: Int,
        val y: Int,
        val width: Int,
        val height: Int,
        val beforeBytes: ByteBuffer,
        val afterBytes: ByteBuffer
    ) : UndoCommand()

    data class LayerAdded(
        val layer: ArtLayer,
        val index: Int
    ) : UndoCommand()

    data class LayerRemoved(
        val layer: ArtLayer,
        val index: Int
    ) : UndoCommand()

    data class LayerReordered(
        val fromIndex: Int,
        val toIndex: Int
    ) : UndoCommand()

    data class LayerPropertyChanged(
        val layerId: String,
        val oldOpacity: Float,
        val newOpacity: Float,
        val oldBlendMode: BlendMode,
        val newBlendMode: BlendMode,
        val oldVisibility: Boolean,
        val newVisibility: Boolean
    ) : UndoCommand()
}
