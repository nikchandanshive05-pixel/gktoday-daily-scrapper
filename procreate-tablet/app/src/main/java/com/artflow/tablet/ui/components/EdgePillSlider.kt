package com.artflow.tablet.ui.components

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.gestures.detectVerticalDragGestures
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Colorize
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.Text
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.artflow.tablet.ui.theme.*

@Composable
fun EdgePillSliderGroup(
    brushSizePercent: Float,
    brushOpacityPercent: Float,
    onSizeChange: (Float) -> Unit,
    onOpacityChange: (Float) -> Unit,
    onEyedropperClick: () -> Unit,
    modifier: Modifier = Modifier
) {
    Column(
        modifier = modifier
            .padding(start = 16.dp)
            .width(44.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        // Top Pill: Brush Size
        VerticalPillSlider(
            value = brushSizePercent,
            onValueChange = onSizeChange,
            label = "${(brushSizePercent * 100).toInt()}%"
        )

        // Center Button: Quick Eyedropper
        Box(
            modifier = Modifier
                .size(40.dp)
                .clip(RoundedCornerShape(10.dp))
                .background(ProSurface.copy(alpha = 0.85f))
                .border(1.dp, ProBorder, RoundedCornerShape(10.dp)),
            contentAlignment = Alignment.Center
        ) {
            IconButton(
                onClick = onEyedropperClick,
                modifier = Modifier.size(40.dp)
            ) {
                Icon(
                    imageVector = Icons.Default.Colorize,
                    contentDescription = "Eyedropper",
                    tint = ProTextPrimary,
                    modifier = Modifier.size(20.dp)
                )
            }
        }

        // Bottom Pill: Brush Opacity
        VerticalPillSlider(
            value = brushOpacityPercent,
            onValueChange = onOpacityChange,
            label = "${(brushOpacityPercent * 100).toInt()}%"
        )
    }
}

@Composable
fun VerticalPillSlider(
    value: Float,
    onValueChange: (Float) -> Unit,
    label: String,
    modifier: Modifier = Modifier
) {
    var isDragging by remember { mutableStateOf(false) }

    Box(
        modifier = modifier
            .width(36.dp)
            .height(130.dp)
            .clip(RoundedCornerShape(18.dp))
            .background(ProSurface.copy(alpha = 0.85f))
            .border(1.dp, ProBorder, RoundedCornerShape(18.dp))
            .pointerInput(Unit) {
                detectVerticalDragGestures(
                    onDragStart = { isDragging = true },
                    onDragEnd = { isDragging = false },
                    onDragCancel = { isDragging = false }
                ) { change, dragAmount ->
                    change.consume()
                    // Drag up increases value, drag down decreases value
                    val delta = -dragAmount / 130f
                    val newValue = (value + delta).coerceIn(0.01f, 1.0f)
                    onValueChange(newValue)
                }
            },
        contentAlignment = Alignment.BottomCenter
    ) {
        // Fill indicator
        Box(
            modifier = Modifier
                .fillMaxWidth()
                .fillMaxHeight(value.coerceIn(0f, 1f))
                .clip(RoundedCornerShape(18.dp))
                .background(ProSliderTrack.copy(alpha = 0.6f))
        )

        // Thumb indicator line
        Box(
            modifier = Modifier
                .align(Alignment.BottomCenter)
                .padding(bottom = (120f * value.coerceIn(0f, 1f)).dp)
                .width(26.dp)
                .height(4.dp)
                .clip(CircleShape)
                .background(ProSliderThumb)
        )

        // Percentage readout badge when dragging
        if (isDragging) {
            Box(
                modifier = Modifier
                    .align(Alignment.Center)
                    .background(Color.Black.copy(alpha = 0.8f), RoundedCornerShape(6.dp))
                    .padding(horizontal = 4.dp, vertical = 2.dp)
            ) {
                Text(
                    text = label,
                    color = ProTextPrimary,
                    fontSize = 10.sp
                )
            }
        }
    }
}
