package com.antigravity.mobile.ui.components

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.antigravity.mobile.data.model.ToolCall
import com.antigravity.mobile.data.model.ToolStatus
import com.antigravity.mobile.ui.theme.ApprovedGreen
import com.antigravity.mobile.ui.theme.DeniedRed
import com.antigravity.mobile.ui.theme.ElectricCyan
import com.antigravity.mobile.ui.theme.ToolCardBg

@Composable
fun ToolCard(
    toolCall: ToolCall,
    modifier: Modifier = Modifier
) {
    var expanded by remember { mutableStateOf(false) }

    Card(
        modifier = modifier
            .fillMaxWidth()
            .padding(vertical = 4.dp),
        colors = CardDefaults.cardColors(containerColor = ToolCardBg),
        shape = RoundedCornerShape(12.dp)
    ) {
        Column(modifier = Modifier.padding(12.dp)) {
            Row(
                verticalAlignment = Alignment.CenterVertically,
                modifier = Modifier
                    .fillMaxWidth()
                    .clickable { expanded = !expanded }
            ) {
                Icon(
                    imageVector = when {
                        toolCall.toolName.contains("command") -> Icons.Default.Terminal
                        toolCall.toolName.contains("file") -> Icons.Default.Description
                        toolCall.toolName.contains("web") -> Icons.Default.Search
                        else -> Icons.Default.Build
                    },
                    contentDescription = null,
                    tint = ElectricCyan,
                    modifier = Modifier.size(20.dp)
                )

                Spacer(modifier = Modifier.width(8.dp))

                Column(modifier = Modifier.weight(1f)) {
                    Text(
                        text = toolCall.summary.ifEmpty { toolCall.toolName },
                        style = MaterialTheme.typography.bodyMedium.copy(fontWeight = FontWeight.SemiBold),
                        color = Color.White
                    )
                    Text(
                        text = toolCall.toolName,
                        style = MaterialTheme.typography.labelSmall,
                        color = Color.Gray
                    )
                }

                // Status Badge
                Surface(
                    shape = RoundedCornerShape(8.dp),
                    color = when (toolCall.status) {
                        ToolStatus.RUNNING -> Color(0xFFF59E0B).copy(alpha = 0.2f)
                        ToolStatus.COMPLETED -> ApprovedGreen.copy(alpha = 0.2f)
                        ToolStatus.FAILED -> DeniedRed.copy(alpha = 0.2f)
                    }
                ) {
                    Text(
                        text = toolCall.status.name,
                        style = MaterialTheme.typography.labelSmall.copy(fontWeight = FontWeight.Bold),
                        color = when (toolCall.status) {
                            ToolStatus.RUNNING -> Color(0xFFF59E0B)
                            ToolStatus.COMPLETED -> ApprovedGreen
                            ToolStatus.FAILED -> DeniedRed
                        },
                        modifier = Modifier.padding(horizontal = 8.dp, vertical = 4.dp)
                    )
                }

                IconButton(
                    onClick = { expanded = !expanded },
                    modifier = Modifier.size(28.dp)
                ) {
                    Icon(
                        imageVector = if (expanded) Icons.Default.ExpandLess else Icons.Default.ExpandMore,
                        contentDescription = "Toggle",
                        tint = Color.LightGray
                    )
                }
            }

            AnimatedVisibility(visible = expanded) {
                Column(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(top = 8.dp)
                ) {
                    if (toolCall.command.isNotEmpty()) {
                        Text(
                            text = "Command:",
                            style = MaterialTheme.typography.labelSmall,
                            color = ElectricCyan,
                            modifier = Modifier.padding(bottom = 2.dp)
                        )
                        Surface(
                            shape = RoundedCornerShape(6.dp),
                            color = Color.Black.copy(alpha = 0.6f),
                            modifier = Modifier.fillMaxWidth()
                        ) {
                            Text(
                                text = toolCall.command,
                                style = MaterialTheme.typography.bodySmall.copy(
                                    fontFamily = FontFamily.Monospace,
                                    fontSize = 12.sp
                                ),
                                color = Color.LightGray,
                                modifier = Modifier.padding(8.dp)
                            )
                        }
                    }

                    if (toolCall.output.isNotEmpty()) {
                        Spacer(modifier = Modifier.height(6.dp))
                        Text(
                            text = "Output:",
                            style = MaterialTheme.typography.labelSmall,
                            color = Color.Gray,
                            modifier = Modifier.padding(bottom = 2.dp)
                        )
                        Surface(
                            shape = RoundedCornerShape(6.dp),
                            color = Color.Black.copy(alpha = 0.4f),
                            modifier = Modifier.fillMaxWidth()
                        ) {
                            Text(
                                text = toolCall.output,
                                style = MaterialTheme.typography.bodySmall.copy(
                                    fontFamily = FontFamily.Monospace,
                                    fontSize = 11.sp
                                ),
                                color = Color.White.copy(alpha = 0.8f),
                                modifier = Modifier.padding(8.dp)
                            )
                        }
                    }
                }
            }
        }
    }
}
