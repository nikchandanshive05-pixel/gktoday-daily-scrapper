package com.artflow.tablet.ui.components

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.artflow.tablet.model.ArtLayer
import com.artflow.tablet.model.BlendMode
import com.artflow.tablet.ui.theme.*

@Composable
fun LayerPanel(
    layers: List<ArtLayer>,
    activeLayerIndex: Int,
    onSelectLayer: (Int) -> Unit,
    onAddLayer: () -> Unit,
    onDeleteLayer: (Int) -> Unit,
    onToggleVisibility: (Int) -> Unit,
    onOpacityChange: (Int, Float) -> Unit,
    onBlendModeChange: (Int, BlendMode) -> Unit,
    onToggleAlphaLock: (Int) -> Unit,
    onClose: () -> Unit,
    modifier: Modifier = Modifier
) {
    Card(
        modifier = modifier
            .width(320.dp)
            .heightIn(max = 480.dp)
            .clip(RoundedCornerShape(16.dp))
            .border(1.dp, ProBorder, RoundedCornerShape(16.dp)),
        colors = CardDefaults.cardColors(containerColor = ProSurface.copy(alpha = 0.95f))
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            // Header: "Layers" + Add Button + Close
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(
                    text = "Layers (${layers.size})",
                    color = ProTextPrimary,
                    fontSize = 16.sp
                )
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    IconButton(onClick = onAddLayer, modifier = Modifier.size(32.dp)) {
                        Icon(Icons.Default.Add, contentDescription = "Add Layer", tint = ProAccentBlue)
                    }
                    IconButton(onClick = onClose, modifier = Modifier.size(32.dp)) {
                        Icon(Icons.Default.Close, contentDescription = "Close", tint = ProTextSecondary)
                    }
                }
            }

            Spacer(modifier = Modifier.height(12.dp))

            // Layer Stack (Top-to-Bottom)
            LazyColumn(
                modifier = Modifier.weight(1f, fill = false),
                verticalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                // Reverse to display top-most layer at top of UI
                itemsIndexed(layers.reversed()) { revIdx, layer ->
                    val actualIdx = layers.size - 1 - revIdx
                    val isSelected = actualIdx == activeLayerIndex

                    LayerRowItem(
                        layer = layer,
                        isSelected = isSelected,
                        onSelect = { onSelectLayer(actualIdx) },
                        onToggleVisibility = { onToggleVisibility(actualIdx) },
                        onOpacityChange = { onOpacityChange(actualIdx, it) },
                        onBlendModeChange = { onBlendModeChange(actualIdx, it) },
                        onToggleAlphaLock = { onToggleAlphaLock(actualIdx) },
                        onDelete = { onDeleteLayer(actualIdx) }
                    )
                }
            }
        }
    }
}

@Composable
fun LayerRowItem(
    layer: ArtLayer,
    isSelected: Boolean,
    onSelect: () -> Unit,
    onToggleVisibility: () -> Unit,
    onOpacityChange: (Float) -> Unit,
    onBlendModeChange: (BlendMode) -> Unit,
    onToggleAlphaLock: () -> Unit,
    onDelete: () -> Unit
) {
    var expandedMenu by remember { mutableStateOf(false) }

    Column(
        modifier = Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(10.dp))
            .background(if (isSelected) ProAccentBlue.copy(alpha = 0.2f) else ProSurfaceVariant)
            .border(
                1.dp,
                if (isSelected) ProAccentBlue else Color.Transparent,
                RoundedCornerShape(10.dp)
            )
            .clickable { onSelect() }
            .padding(8.dp)
    ) {
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Row(
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                // Visibility Eye Checkbox
                IconButton(onClick = onToggleVisibility, modifier = Modifier.size(24.dp)) {
                    Icon(
                        imageVector = if (layer.isVisible) Icons.Default.Visibility else Icons.Default.VisibilityOff,
                        contentDescription = "Visibility",
                        tint = if (layer.isVisible) ProTextPrimary else ProTextSecondary.copy(alpha = 0.4f),
                        modifier = Modifier.size(16.dp)
                    )
                }

                Text(
                    text = layer.name,
                    color = ProTextPrimary,
                    fontSize = 13.sp
                )

                if (layer.isAlphaLocked) {
                    Icon(
                        imageVector = Icons.Default.Lock,
                        contentDescription = "Alpha Lock",
                        tint = ProAccentBlue,
                        modifier = Modifier.size(12.dp)
                    )
                }
            }

            // Blend Mode & Options
            Row(verticalAlignment = Alignment.CenterVertically) {
                TextButton(onClick = { expandedMenu = true }) {
                    Text(
                        text = layer.blendMode.displayName,
                        color = ProAccentBlue,
                        fontSize = 12.sp
                    )
                }

                DropdownMenu(
                    expanded = expandedMenu,
                    onDismissRequest = { expandedMenu = false },
                    modifier = Modifier.background(ProSurface)
                ) {
                    BlendMode.entries.forEach { mode ->
                        DropdownMenuItem(
                            text = { Text(mode.displayName, color = ProTextPrimary) },
                            onClick = {
                                onBlendModeChange(mode)
                                expandedMenu = false
                            }
                        )
                    }
                    Divider(color = ProBorder)
                    DropdownMenuItem(
                        text = { Text(if (layer.isAlphaLocked) "Unlock Alpha" else "Alpha Lock", color = ProTextPrimary) },
                        onClick = {
                            onToggleAlphaLock()
                            expandedMenu = false
                        }
                    )
                    DropdownMenuItem(
                        text = { Text("Delete Layer", color = Color(0xFFFF453A)) },
                        onClick = {
                            onDelete()
                            expandedMenu = false
                        }
                    )
                }
            }
        }

        // Opacity Slider
        if (isSelected) {
            Row(
                verticalAlignment = Alignment.CenterVertically,
                modifier = Modifier.padding(horizontal = 4.dp, vertical = 2.dp)
            ) {
                Text(
                    text = "Opacity: ${(layer.opacity * 100).toInt()}%",
                    color = ProTextSecondary,
                    fontSize = 11.sp,
                    modifier = Modifier.width(80.dp)
                )
                Slider(
                    value = layer.opacity,
                    onValueChange = onOpacityChange,
                    valueRange = 0f..1f,
                    colors = SliderDefaults.colors(
                        thumbColor = ProTextPrimary,
                        activeTrackColor = ProAccentBlue,
                        inactiveTrackColor = ProSliderTrack
                    ),
                    modifier = Modifier.weight(1f)
                )
            }
        }
    }
}
