package com.antigravity.mobile.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.antigravity.mobile.data.model.*
import com.antigravity.mobile.ui.components.ApprovalBanner
import com.antigravity.mobile.ui.components.ToolCard
import com.antigravity.mobile.ui.theme.*
import kotlinx.coroutines.launch

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ChatScreen(
    messages: List<ChatMessage>,
    connectionState: ConnectionState,
    onSendMessage: (String) -> Unit,
    onApproveAction: (String) -> Unit,
    onDenyAction: (String) -> Unit,
    onOpenDrawer: () -> Unit,
    onManualConnect: (String, Int, String) -> Unit,
    modifier: Modifier = Modifier
) {
    var inputText by remember { mutableStateOf("") }
    val listState = rememberLazyListState()
    val coroutineScope = rememberCoroutineScope()
    var showPairingDialog by remember { mutableStateOf(false) }

    LaunchedEffect(messages.size) {
        if (messages.isNotEmpty()) {
            listState.animateScrollToItem(messages.size - 1)
        }
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Column {
                            Text(
                                text = "Antigravity",
                                style = MaterialTheme.typography.titleMedium.copy(fontWeight = FontWeight.Bold),
                                color = Color.White
                            )
                            Row(verticalAlignment = Alignment.CenterVertically) {
                                // Status Dot
                                Box(
                                    modifier = Modifier
                                        .size(8.dp)
                                        .background(
                                            when (connectionState) {
                                                is ConnectionState.Connected -> ApprovedGreen
                                                is ConnectionState.Discovering -> Color(0xFFF59E0B)
                                                else -> DeniedRed
                                            },
                                            shape = CircleShape
                                        )
                                )
                                Spacer(modifier = Modifier.width(6.dp))
                                Text(
                                    text = when (connectionState) {
                                        is ConnectionState.Connected -> "Connected"
                                        is ConnectionState.Discovering -> "Searching PC..."
                                        is ConnectionState.PairingRequired -> "Enter PIN"
                                        else -> "Disconnected"
                                    },
                                    style = MaterialTheme.typography.labelSmall,
                                    color = Color.LightGray
                                )
                            }
                        }
                    }
                },
                navigationIcon = {
                    IconButton(onClick = onOpenDrawer) {
                        Icon(Icons.Default.Menu, contentDescription = "Menu", tint = Color.White)
                    }
                },
                actions = {
                    // Model Badge
                    Surface(
                        shape = RoundedCornerShape(16.dp),
                        color = PrimaryPurple.copy(alpha = 0.2f),
                        border = ButtonDefaults.outlinedButtonBorder
                    ) {
                        Text(
                            text = "Gemini 3.8 Flash",
                            style = MaterialTheme.typography.labelSmall.copy(fontWeight = FontWeight.SemiBold),
                            color = ElectricCyan,
                            modifier = Modifier.padding(horizontal = 10.dp, vertical = 4.dp)
                        )
                    }
                    IconButton(onClick = { showPairingDialog = true }) {
                        Icon(Icons.Default.Wifi, contentDescription = "Connect", tint = Color.White)
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(containerColor = DarkBackground)
            )
        },
        containerColor = DarkBackground,
        modifier = modifier
    ) { innerPadding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(innerPadding)
        ) {
            // Chat Messages List
            LazyColumn(
                state = listState,
                modifier = Modifier
                    .weight(1f)
                    .fillMaxWidth()
                    .padding(horizontal = 16.dp)
            ) {
                items(messages) { msg ->
                    ChatBubble(
                        message = msg,
                        onApproveAction = onApproveAction,
                        onDenyAction = onDenyAction
                    )
                    Spacer(modifier = Modifier.height(12.dp))
                }
            }

            // Input Bar
            Surface(
                color = SurfaceDark,
                shape = RoundedCornerShape(topStart = 20.dp, topEnd = 20.dp),
                modifier = Modifier.fillMaxWidth()
            ) {
                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    modifier = Modifier
                        .padding(horizontal = 12.dp, vertical = 8.dp)
                        .fillMaxWidth()
                ) {
                    IconButton(onClick = { inputText += "/" }) {
                        Text(
                            text = "/",
                            style = MaterialTheme.typography.titleLarge.copy(fontWeight = FontWeight.Bold),
                            color = ElectricCyan
                        )
                    }

                    TextField(
                        value = inputText,
                        onValueChange = { inputText = it },
                        placeholder = { Text("Message Antigravity...", color = Color.Gray) },
                        colors = TextFieldDefaults.colors(
                            focusedContainerColor = Color.Transparent,
                            unfocusedContainerColor = Color.Transparent,
                            disabledContainerColor = Color.Transparent,
                            focusedTextColor = Color.White,
                            unfocusedTextColor = Color.White,
                            focusedIndicatorColor = Color.Transparent,
                            unfocusedIndicatorColor = Color.Transparent
                        ),
                        modifier = Modifier.weight(1f)
                    )

                    IconButton(
                        onClick = {
                            if (inputText.isNotBlank()) {
                                onSendMessage(inputText.trim())
                                inputText = ""
                            }
                        },
                        enabled = inputText.isNotBlank()
                    ) {
                        Surface(
                            shape = CircleShape,
                            color = if (inputText.isNotBlank()) PrimaryPurple else Color.Gray.copy(alpha = 0.3f),
                            modifier = Modifier.size(36.dp)
                        ) {
                            Box(contentAlignment = Alignment.Center) {
                                Icon(
                                    imageVector = Icons.Default.ArrowUpward,
                                    contentDescription = "Send",
                                    tint = Color.White,
                                    modifier = Modifier.size(20.dp)
                                )
                            }
                        }
                    }
                }
            }
        }
    }

    if (showPairingDialog) {
        ManualPairingDialog(
            onDismiss = { showPairingDialog = false },
            onConnect = { host, port, pin ->
                showPairingDialog = false
                onManualConnect(host, port, pin)
            }
        )
    }
}

@Composable
fun ChatBubble(
    message: ChatMessage,
    onApproveAction: (String) -> Unit,
    onDenyAction: (String) -> Unit,
    modifier: Modifier = Modifier
) {
    if (message.sender == Sender.USER) {
        Row(
            modifier = modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.End
        ) {
            Surface(
                shape = RoundedCornerShape(18.dp, 18.dp, 4.dp, 18.dp),
                color = UserBubbleDark,
                modifier = Modifier.widthIn(max = 300.dp)
            ) {
                Text(
                    text = message.content,
                    style = MaterialTheme.typography.bodyLarge,
                    color = Color.White,
                    modifier = Modifier.padding(14.dp)
                )
            }
        }
    } else {
        Column(modifier = modifier.fillMaxWidth()) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Surface(
                    shape = CircleShape,
                    color = PrimaryPurple,
                    modifier = Modifier.size(24.dp)
                ) {
                    Box(contentAlignment = Alignment.Center) {
                        Icon(
                            imageVector = Icons.Default.AutoAwesome,
                            contentDescription = null,
                            tint = Color.White,
                            modifier = Modifier.size(14.dp)
                        )
                    }
                }
                Spacer(modifier = Modifier.width(8.dp))
                Text(
                    text = "Antigravity",
                    style = MaterialTheme.typography.labelMedium.copy(fontWeight = FontWeight.Bold),
                    color = ElectricCyan
                )
            }

            Spacer(modifier = Modifier.height(6.dp))

            // Main Text / Markdown
            if (message.content.isNotEmpty()) {
                Surface(
                    color = Color.Transparent,
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Text(
                        text = message.content,
                        style = MaterialTheme.typography.bodyLarge.copy(lineHeight = 24.sp),
                        color = AgentText,
                        modifier = Modifier.padding(start = 32.dp)
                    )
                }
            }

            // Embedded Tool Calls
            if (message.toolCalls.isNotEmpty()) {
                Column(modifier = Modifier.padding(start = 32.dp, top = 8.dp)) {
                    message.toolCalls.forEach { tool ->
                        ToolCard(toolCall = tool)
                    }
                }
            }

            // Pending Approval Banner
            message.pendingApproval?.let { approval ->
                Box(modifier = Modifier.padding(start = 32.dp, top = 8.dp)) {
                    ApprovalBanner(
                        approval = approval,
                        onApprove = onApproveAction,
                        onDeny = onDenyAction
                    )
                }
            }
        }
    }
}

@Composable
fun ManualPairingDialog(
    onDismiss: () -> Unit,
    onConnect: (String, Int, String) -> Unit
) {
    var host by remember { mutableStateOf("192.168.1.") }
    var port by remember { mutableStateOf("8765") }
    var pin by remember { mutableStateOf("") }

    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text("Connect to PC Bridge") },
        text = {
            Column {
                OutlinedTextField(
                    value = host,
                    onValueChange = { host = it },
                    label = { Text("PC IP Address") },
                    singleLine = true,
                    modifier = Modifier.fillMaxWidth()
                )
                Spacer(modifier = Modifier.height(8.dp))
                OutlinedTextField(
                    value = port,
                    onValueChange = { port = it },
                    label = { Text("Port") },
                    singleLine = true,
                    modifier = Modifier.fillMaxWidth()
                )
                Spacer(modifier = Modifier.height(8.dp))
                OutlinedTextField(
                    value = pin,
                    onValueChange = { pin = it },
                    label = { Text("4-Digit PIN") },
                    singleLine = true,
                    modifier = Modifier.fillMaxWidth()
                )
            }
        },
        confirmButton = {
            Button(
                onClick = {
                    val p = port.toIntOrNull() ?: 8765
                    onConnect(host.trim(), p, pin.trim())
                }
            ) {
                Text("Connect")
            }
        },
        dismissButton = {
            TextButton(onClick = onDismiss) {
                Text("Cancel")
            }
        }
    )
}
