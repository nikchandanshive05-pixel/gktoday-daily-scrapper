package com.artflow.tablet.ui.components

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.gestures.detectDragGestures
import androidx.compose.foundation.gestures.detectTapGestures
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Close
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.SweepGradient
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.artflow.tablet.ui.theme.*
import kotlin.math.*

@Composable
fun ColorDiscPicker(
    currentColor: Color,
    onColorChanged: (Color) -> Unit,
    onClose: () -> Unit,
    modifier: Modifier = Modifier
) {
    var hue by remember { mutableStateOf(0f) } // 0..360
    var saturation by remember { mutableStateOf(1f) } // 0..1
    var value by remember { mutableStateOf(1f) } // 0..1

    val rainbowColors = remember {
        listOf(
            Color.Red, Color.Yellow, Color.Green,
            Color.Cyan, Color.Blue, Color.Magenta, Color.Red
        )
    }

    val defaultPalette = remember {
        listOf(
            Color(0xFF000000), Color(0xFFFFFFFF), Color(0xFFFF3B30),
            Color(0xFFFF9500), Color(0xFFFFCC00), Color(0xFF34C759),
            Color(0xFF007AFF), Color(0xFF5856D6), Color(0xFFAF52DE),
            Color(0xFF8E8E93), Color(0xFF636366), Color(0xFF48484A)
        )
    }

    Card(
        modifier = modifier
            .width(280.dp)
            .clip(RoundedCornerShape(16.dp))
            .border(1.dp, ProBorder, RoundedCornerShape(16.dp)),
        colors = CardDefaults.cardColors(containerColor = ProSurface.copy(alpha = 0.95f))
    ) {
        Column(
            modifier = Modifier.padding(16.dp),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            // Header
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(text = "Colors", color = ProTextPrimary, fontSize = 16.sp)
                IconButton(onClick = onClose, modifier = Modifier.size(28.dp)) {
                    Icon(Icons.Default.Close, contentDescription = "Close", tint = ProTextSecondary)
                }
            }

            Spacer(modifier = Modifier.height(12.dp))

            // Procreate Circular Hue Ring + Saturation Disc Canvas
            Box(
                modifier = Modifier
                    .size(200.dp)
                    .pointerInput(Unit) {
                        detectTapGestures { offset ->
                            val center = Offset(100f * density, 100f * density)
                            val dx = offset.x - center.x
                            val dy = offset.y - center.y
                            val dist = hypot(dx, dy)
                            val radius = 100f * density

                            if (dist in (radius * 0.70f)..radius) {
                                // Tapped on outer Hue ring
                                val angle = Math.toDegrees(atan2(dy.toDouble(), dx.toDouble())).toFloat()
                                hue = (angle + 360f) % 360f
                                onColorChanged(Color.hsv(hue, saturation, value))
                            } else if (dist < radius * 0.65f) {
                                // Tapped inside inner Saturation/Value disc
                                saturation = (dist / (radius * 0.65f)).coerceIn(0f, 1f)
                                onColorChanged(Color.hsv(hue, saturation, value))
                            }
                        }
                    },
                contentAlignment = Alignment.Center
            ) {
                Canvas(modifier = Modifier.fillMaxSize()) {
                    val center = Offset(size.width / 2f, size.height / 2f)
                    val outerRadius = size.width / 2f
                    val innerRadius = outerRadius * 0.72f

                    // Draw Hue Ring
                    drawCircle(
                        brush = Brush.sweepGradient(rainbowColors, center),
                        radius = outerRadius
                    )

                    // Knock out inner space to make ring
                    drawCircle(
                        color = ProSurface,
                        radius = innerRadius
                    )

                    // Draw inner saturation disc matching active hue
                    drawCircle(
                        brush = Brush.radialGradient(
                            colors = listOf(Color.White, Color.hsv(hue, 1f, 1f)),
                            center = center,
                            radius = innerRadius * 0.90f
                        ),
                        radius = innerRadius * 0.90f
                    )
                }

                // Active Color center dot
                Box(
                    modifier = Modifier
                        .size(36.dp)
                        .clip(CircleShape)
                        .background(currentColor)
                        .border(2.dp, Color.White, CircleShape)
                )
            }

            Spacer(modifier = Modifier.height(16.dp))

            // Swatches Palette Row
            Text(
                text = "Palettes",
                color = ProTextSecondary,
                fontSize = 12.sp,
                modifier = Modifier.align(Alignment.Start)
            )

            Spacer(modifier = Modifier.height(6.dp))

            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween
            ) {
                defaultPalette.take(6).forEach { color ->
                    Box(
                        modifier = Modifier
                            .size(28.dp)
                            .clip(CircleShape)
                            .background(color)
                            .border(1.dp, ProBorder, CircleShape)
                            .clickable {
                                onColorChanged(color)
                            }
                    )
                }
            }

            Spacer(modifier = Modifier.height(6.dp))

            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween
            ) {
                defaultPalette.drop(6).take(6).forEach { color ->
                    Box(
                        modifier = Modifier
                            .size(28.dp)
                            .clip(CircleShape)
                            .background(color)
                            .border(1.dp, ProBorder, CircleShape)
                            .clickable {
                                onColorChanged(color)
                            }
                    )
                }
            }
        }
    }
}
