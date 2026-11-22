package com.antigravity.mobile

import android.content.Context
import android.content.Intent
import android.content.SharedPreferences
import android.os.Build
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.lifecycle.lifecycleScope
import com.antigravity.mobile.data.discovery.DiscoveryEvent
import com.antigravity.mobile.data.discovery.NsdDiscoveryManager
import com.antigravity.mobile.data.model.*
import com.antigravity.mobile.data.network.AntigravitySocketClient
import com.antigravity.mobile.data.network.SocketEvent
import com.antigravity.mobile.service.AntigravityForegroundService
import com.antigravity.mobile.ui.components.SidebarDrawer
import com.antigravity.mobile.ui.screens.ChatScreen
import com.antigravity.mobile.ui.screens.ManualPairingDialog
import com.antigravity.mobile.ui.theme.AntigravityTheme
import kotlinx.coroutines.launch

class MainActivity : ComponentActivity() {

    private val socketClient = AntigravitySocketClient()
    private lateinit var discoveryManager: NsdDiscoveryManager
    private lateinit var prefs: SharedPreferences

    companion object {
        var instance: MainActivity? = null
            private set
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        instance = this
        discoveryManager = NsdDiscoveryManager(this)
        prefs = getSharedPreferences("antigravity_prefs", Context.MODE_PRIVATE)

        setContent {
            AntigravityTheme {
                val drawerState = rememberDrawerState(initialValue = DrawerValue.Closed)
                val scope = rememberCoroutineScope()

                var connectionState by remember { mutableStateOf<ConnectionState>(ConnectionState.Discovering) }
                val messages = remember { mutableStateListOf<ChatMessage>() }
                val conversations = remember { mutableStateListOf<ConversationItem>() }
                var currentConversationId by remember { mutableStateOf<String?>(null) }
                var pendingHost by remember { mutableStateOf<String?>(null) }
                var pendingPort by remember { mutableStateOf(8765) }
                var showPinPrompt by remember { mutableStateOf(false) }

                // Add welcome initial message
                LaunchedEffect(Unit) {
                    if (messages.isEmpty()) {
                        messages.add(
                            ChatMessage(
                                id = "welcome",
                                sender = Sender.AGENT,
                                content = "Welcome to Antigravity Mobile. Searching for your PC on local Wi-Fi..."
                            )
                        )
                    }

                    // Start mDNS Discovery
                    launch {
                        discoveryManager.discoverServices().collect { event ->
                            when (event) {
                                is DiscoveryEvent.Found -> {
                                    pendingHost = event.host
                                    pendingPort = event.port
                                    val savedPin = prefs.getString("last_pin", null)
                                    if (!savedPin.isNullOrEmpty()) {
                                        connectionState = ConnectionState.Connecting
                                        socketClient.connect(event.host, event.port, savedPin)
                                    } else {
                                        connectionState = ConnectionState.PairingRequired(event.host, event.port)
                                        showPinPrompt = true
                                    }
                                }
                                is DiscoveryEvent.Lost -> {
                                    connectionState = ConnectionState.Disconnected
                                }
                                is DiscoveryEvent.Error -> {
                                    connectionState = ConnectionState.Error(event.message)
                                }
                            }
                        }
                    }

                    // Collect Socket Events
                    launch {
                        socketClient.events.collect { event ->
                            when (event) {
                                is SocketEvent.Connected -> {
                                    connectionState = ConnectionState.Connected("PC", pendingPort, "Desktop")
                                    socketClient.requestConversations()
                                    startCompanionService()
                                }
                                is SocketEvent.Authenticated -> {
                                    prefs.edit().putString("auth_token", event.token).apply()
                                }
                                is SocketEvent.AuthFailed -> {
                                    connectionState = ConnectionState.Error("Authentication failed: ${event.reason}")
                                    showPinPrompt = true
                                }
                                is SocketEvent.TokenChunk -> {
                                    val last = messages.lastOrNull()
                                    if (last != null && last.sender == Sender.AGENT && last.isStreaming) {
                                        val idx = messages.indexOf(last)
                                        messages[idx] = last.copy(content = last.content + event.delta)
                                    } else {
                                        messages.add(
                                            ChatMessage(
                                                id = "stream-${System.currentTimeMillis()}",
                                                sender = Sender.AGENT,
                                                content = event.delta,
                                                isStreaming = true
                                            )
                                        )
                                    }
                                }
                                is SocketEvent.ActionRequested -> {
                                    messages.add(
                                        ChatMessage(
                                            id = "act-${event.action.id}",
                                            sender = Sender.AGENT,
                                            content = "Action requires permission:",
                                            pendingApproval = event.action
                                        )
                                    )
                                    // Trigger Heads-Up Lock Screen Notification
                                    showApprovalHeadsUp(event.action.id, event.action.description)
                                }
                                is SocketEvent.ActionResolved -> {
                                    val idx = messages.indexOfFirst { it.pendingApproval?.id == event.actionId }
                                    if (idx != -1) {
                                        val m = messages[idx]
                                        messages[idx] = m.copy(
                                            pendingApproval = m.pendingApproval?.copy(status = event.status)
                                        )
                                    }
                                }
                                is SocketEvent.ConversationsList -> {
                                    conversations.clear()
                                    conversations.addAll(event.items)
                                }
                                is SocketEvent.Disconnected -> {
                                    connectionState = ConnectionState.Disconnected
                                }
                                else -> Unit
                            }
                        }
                    }
                }

                ModalNavigationDrawer(
                    drawerState = drawerState,
                    drawerContent = {
                        SidebarDrawer(
                            conversations = conversations,
                            currentConversationId = currentConversationId,
                            onSelectConversation = { convId ->
                                currentConversationId = convId
                                socketClient.selectConversation(convId)
                            },
                            onNewConversation = {
                                currentConversationId = null
                                messages.clear()
                                messages.add(
                                    ChatMessage(
                                        id = "new",
                                        sender = Sender.AGENT,
                                        content = "New conversation started on PC."
                                    )
                                )
                            },
                            onCloseDrawer = {
                                scope.launch { drawerState.close() }
                            }
                        )
                    }
                ) {
                    ChatScreen(
                        messages = messages,
                        connectionState = connectionState,
                        onSendMessage = { prompt ->
                            messages.add(
                                ChatMessage(
                                    id = "usr-${System.currentTimeMillis()}",
                                    sender = Sender.USER,
                                    content = prompt
                                )
                            )
                            socketClient.sendPrompt(prompt, currentConversationId)
                        },
                        onApproveAction = { actionId ->
                            resolveAction(actionId, approve = true)
                        },
                        onDenyAction = { actionId ->
                            resolveAction(actionId, approve = false)
                        },
                        onOpenDrawer = {
                            scope.launch { drawerState.open() }
                        },
                        onManualConnect = { host, port, pin ->
                            connectionState = ConnectionState.Connecting
                            prefs.edit().putString("last_pin", pin).apply()
                            socketClient.connect(host, port, pin)
                        },
                        modifier = Modifier.fillMaxSize()
                    )
                }

                if (showPinPrompt && pendingHost != null) {
                    ManualPairingDialog(
                        onDismiss = { showPinPrompt = false },
                        onConnect = { host, port, pin ->
                            showPinPrompt = false
                            prefs.edit().putString("last_pin", pin).apply()
                            connectionState = ConnectionState.Connecting
                            socketClient.connect(host, port, pin)
                        }
                    )
                }
            }
        }
    }

    fun resolveAction(actionId: String, approve: Boolean) {
        socketClient.resolveAction(actionId, approve)
    }

    private fun showApprovalHeadsUp(actionId: String, description: String) {
        val intent = Intent(this, AntigravityForegroundService::class.java).apply {
            putExtra("action_id", actionId)
            putExtra("action_desc", description)
        }
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            startForegroundService(intent)
        } else {
            startService(intent)
        }
    }

    private fun startCompanionService() {
        val intent = Intent(this, AntigravityForegroundService::class.java)
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            startForegroundService(intent)
        } else {
            startService(intent)
        }
    }

    override fun onDestroy() {
        super.onDestroy()
        instance = null
        socketClient.disconnect()
    }
}
