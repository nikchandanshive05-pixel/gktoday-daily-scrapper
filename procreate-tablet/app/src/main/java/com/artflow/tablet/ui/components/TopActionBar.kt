package com.artflow.tablet.ui.components

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.artflow.tablet.brush.BrushType
import com.artflow.tablet.input.InputMode
import com.artflow.tablet.ui.theme.*

@Composable
fun TopActionBar(
    activeTool: BrushType,
    onToolSelected: (BrushType) -> Unit,
    activeColor: Color,
    onColorChipClick: () -> Unit,
    onLayersClick: () -> Unit,
    layerCount: Int,
    inputMode: InputMode,
    onToggleInputMode: () -> Unit,
    onUndoClick: () -> Unit,
    onRedoClick: () -> Unit,
    canUndo: Boolean,
    canRedo: Boolean,
    modifier: Modifier = Modifier
) {
    Row(
        modifier = modifier
            .fillMaxWidth()
            .height(56.dp)
            .padding(horizontal = 16.dp, vertical = 6.dp),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically
    ) {
        // Left Cluster: Procreate Left Actions
        Row(
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(8.dp),
            modifier = Modifier
                .clip(RoundedCornerShape(12.dp))
                .background(ProSurface.copy(alpha = 0.85f))
                .border(1.dp, ProBorder, RoundedCornerShape(12.dp))
                .padding(horizontal = 8.dp, vertical = 4.dp)
        ) {
            Text(
                text = "Gallery",
                color = ProTextPrimary,
                fontSize = 13.sp,
                modifier = Modifier.padding(horizontal = 8.dp)
            )

            IconButton(onClick = onUndoClick, enabled = canUndo, modifier = Modifier.size(32.dp)) {
                Icon(
                    imageVector = Icons.Default.Undo,
                    contentDescription = "Undo",
                    tint = if (canUndo) ProTextPrimary else ProTextSecondary.copy(alpha = 0.4f),
                    modifier = Modifier.size(18.dp)
                )
            }

            IconButton(onClick = onRedoClick, enabled = canRedo, modifier = Modifier.size(32.dp)) {
                Icon(
                    imageVector = Icons.Default.Redo,
                    contentDescription = "Redo",
                    tint = if (canRedo) ProTextPrimary else ProTextSecondary.copy(alpha = 0.4f),
                    modifier = Modifier.size(18.dp)
                )
            }
        }

        // Center: S-Pen / Finger Drawing Quick Toggle
        Box(
            modifier = Modifier
                .clip(RoundedCornerShape(20.dp))
                .background(ProSurface.copy(alpha = 0.85f))
                .border(1.dp, ProBorder, RoundedCornerShape(20.dp))
                .clickable { onToggleInputMode() }
                .padding(horizontal = 12.dp, vertical = 6.dp)
        ) {
            Row(
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(6.dp)
            ) {
                Icon(
                    imageVector = if (inputMode == InputMode.STYLUS_ONLY) Icons.Default.Edit else Icons.Default.TouchApp,
                    contentDescription = null,
                    tint = if (inputMode == InputMode.STYLUS_ONLY) ProAccentBlue else Color(0xFFFF9F0A),
                    modifier = Modifier.size(16.dp)
                )
                Text(
                    text = if (inputMode == InputMode.STYLUS_ONLY) "S-Pen Only (Palm Rejection)" else "Finger Drawing Mode",
                    color = ProTextPrimary,
                    fontSize = 12.sp
                )
            }
        }

        // Right Cluster: Brush, Smudge, Eraser, Layers, Color Disc
        Row(
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(8.dp),
            modifier = Modifier
                .clip(RoundedCornerShape(12.dp))
                .background(ProSurface.copy(alpha = 0.85f))
                .border(1.dp, ProBorder, RoundedCornerShape(12.dp))
                .padding(horizontal = 8.dp, vertical = 4.dp)
        ) {
            ToolButton(
                icon = Icons.Default.Brush,
                contentDescription = "Paintbrush",
                isSelected = activeTool != BrushType.SMUDGE && activeTool != BrushType.ERASER,
                onClick = { onToolSelected(BrushType.STUDIO_PEN) }
            )

            ToolButton(
                icon = Icons.Default.TouchApp,
                contentDescription = "Smudge",
                isSelected = activeTool == BrushType.SMUDGE,
                onClick = { onToolSelected(BrushType.SMUDGE) }
            )

            ToolButton(
                icon = Icons.Default.AutoFixHigh,
                contentDescription = "Eraser",
                isSelected = activeTool == BrushType.ERASER,
                onClick = { onToolSelected(BrushType.ERASER) }
            )

            // Layers Button with Badge
            Box(
                modifier = Modifier
                    .clip(RoundedCornerShape(8.dp))
                    .clickable { onLayersClick() }
                    .padding(6.dp),
                contentAlignment = Alignment.Center
            ) {
                Icon(
                    imageVector = Icons.Default.Layers,
                    contentDescription = "Layers",
                    tint = ProTextPrimary,
                    modifier = Modifier.size(20.dp)
                )
            }

            // Circular Color Chip (Top-right)
            Box(
                modifier = Modifier
                    .size(28.dp)
                    .clip(CircleShape)
                    .background(activeColor)
                    .border(2.dp, ProBorder, CircleShape)
                    .clickable { onColorChipClick() }
            )
        }
    }
}

@Composable
fun ToolButton(
    icon: ImageVector,
    contentDescription: String,
    isSelected: Boolean,
    onClick: () -> Unit
) {
    Box(
        modifier = Modifier
            .clip(RoundedCornerShape(8.dp))
            .background(if (isSelected) ProAccentBlue.copy(alpha = 0.25f) else Color.Transparent)
            .clickable { onClick() }
            .padding(6.dp),
        contentAlignment = Alignment.Center
    ) {
        Icon(
            imageVector = icon,
            contentDescription = contentDescription,
            tint = if (isSelected) ProAccentBlue else ProTextPrimary,
            modifier = Modifier.size(20.dp)
        )
    }
}
