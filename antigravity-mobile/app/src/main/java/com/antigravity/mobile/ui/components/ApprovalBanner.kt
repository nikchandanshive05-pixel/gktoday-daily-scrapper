package com.antigravity.mobile.ui.components

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Check
import androidx.compose.material.icons.filled.Close
import androidx.compose.material.icons.filled.Warning
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.antigravity.mobile.data.model.ActionApproval
import com.antigravity.mobile.data.model.ApprovalStatus
import com.antigravity.mobile.ui.theme.ApprovedGreen
import com.antigravity.mobile.ui.theme.DeniedRed

@Composable
fun ApprovalBanner(
    approval: ActionApproval,
    onApprove: (String) -> Unit,
    onDeny: (String) -> Unit,
    modifier: Modifier = Modifier
) {
    Card(
        modifier = modifier
            .fillMaxWidth()
            .padding(vertical = 8.dp),
        colors = CardDefaults.cardColors(containerColor = Color(0xFF1E1B4B)),
        shape = RoundedCornerShape(16.dp)
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Icon(
                    imageVector = Icons.Default.Warning,
                    contentDescription = null,
                    tint = Color(0xFFF59E0B),
                    modifier = Modifier.size(24.dp)
                )
                Spacer(modifier = Modifier.width(8.dp))
                Text(
                    text = "Permission Requested",
                    style = MaterialTheme.typography.titleMedium.copy(fontWeight = FontWeight.Bold),
                    color = Color.White
                )
            }

            Spacer(modifier = Modifier.height(8.dp))

            Text(
                text = approval.description,
                style = MaterialTheme.typography.bodyMedium,
                color = Color(0xFFE2E8F0)
            )

            Spacer(modifier = Modifier.height(12.dp))

            when (approval.status) {
                ApprovalStatus.PENDING -> {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.End
                    ) {
                        OutlinedButton(
                            onClick = { onDeny(approval.id) },
                            colors = ButtonDefaults.outlinedButtonColors(contentColor = DeniedRed),
                            shape = RoundedCornerShape(8.dp)
                        ) {
                            Icon(Icons.Default.Close, contentDescription = null, modifier = Modifier.size(16.dp))
                            Spacer(modifier = Modifier.width(4.dp))
                            Text("Deny")
                        }

                        Spacer(modifier = Modifier.width(12.dp))

                        Button(
                            onClick = { onApprove(approval.id) },
                            colors = ButtonDefaults.buttonColors(containerColor = ApprovedGreen),
                            shape = RoundedCornerShape(8.dp)
                        ) {
                            Icon(Icons.Default.Check, contentDescription = null, modifier = Modifier.size(16.dp))
                            Spacer(modifier = Modifier.width(4.dp))
                            Text("Proceed")
                        }
                    }
                }
                ApprovalStatus.APPROVED -> {
                    Text(
                        text = "✓ Approved",
                        style = MaterialTheme.typography.labelMedium.copy(fontWeight = FontWeight.Bold),
                        color = ApprovedGreen
                    )
                }
                ApprovalStatus.DENIED -> {
                    Text(
                        text = "✕ Denied",
                        style = MaterialTheme.typography.labelMedium.copy(fontWeight = FontWeight.Bold),
                        color = DeniedRed
                    )
                }
            }
        }
    }
}
