package com.antigravity.mobile.data.network

import android.util.Log
import com.antigravity.mobile.data.model.*
import kotlinx.coroutines.channels.BufferOverflow
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.SharedFlow
import kotlinx.coroutines.flow.asSharedFlow
import okhttp3.*
import org.json.JSONObject
import java.util.concurrent.TimeUnit

sealed class SocketEvent {
    object Connected : SocketEvent()
    data class Authenticated(val token: String) : SocketEvent()
    data class AuthFailed(val reason: String) : SocketEvent()
    data class TokenChunk(val delta: String) : SocketEvent()
    data class MessageReceived(val message: ChatMessage) : SocketEvent()
    data class ToolUpdated(val toolCall: ToolCall) : SocketEvent()
    data class ActionRequested(val action: ActionApproval) : SocketEvent()
    data class ActionResolved(val actionId: String, val status: ApprovalStatus) : SocketEvent()
    data class ConversationsList(val items: List<ConversationItem>) : SocketEvent()
    data class Disconnected(val reason: String) : SocketEvent()
}

class AntigravitySocketClient {
    private val client = OkHttpClient.Builder()
        .pingInterval(15, TimeUnit.SECONDS)
        .connectTimeout(10, TimeUnit.SECONDS)
        .build()

    private var webSocket: WebSocket? = null
    private val _events = MutableSharedFlow<SocketEvent>(
        replay = 1,
        onBufferOverflow = BufferOverflow.DROP_OLDEST
    )
    val events: SharedFlow<SocketEvent> = _events.asSharedFlow()

    fun connect(host: String, port: Int, pin: String) {
        val url = "ws://$host:$port/ws"
        val request = Request.Builder().url(url).build()

        webSocket = client.newWebSocket(request, object : WebSocketListener() {
            override fun onOpen(webSocket: WebSocket, response: Response) {
                Log.d("WebSocket", "Connected to $url, sending auth handshake...")
                _events.tryEmit(SocketEvent.Connected)
                // Send PIN authentication
                val authPayload = JSONObject().apply {
                    put("type", "auth")
                    put("pin", pin)
                }
                webSocket.send(authPayload.toString())
            }

            override fun onMessage(webSocket: WebSocket, text: String) {
                try {
                    val json = JSONObject(text)
                    when (json.optString("type")) {
                        "auth_success" -> {
                            val token = json.optString("token", "")
                            _events.tryEmit(SocketEvent.Authenticated(token))
                        }
                        "auth_failed" -> {
                            _events.tryEmit(SocketEvent.AuthFailed(json.optString("reason", "Invalid PIN")))
                        }
                        "token" -> {
                            _events.tryEmit(SocketEvent.TokenChunk(json.optString("delta", "")))
                        }
                        "action_pending" -> {
                            val act = ActionApproval(
                                id = json.optString("action_id"),
                                description = json.optString("description"),
                                status = ApprovalStatus.PENDING
                            )
                            _events.tryEmit(SocketEvent.ActionRequested(act))
                        }
                        "action_resolved" -> {
                            val id = json.optString("action_id")
                            val statusStr = json.optString("status")
                            val status = if (statusStr == "approved") ApprovalStatus.APPROVED else ApprovalStatus.DENIED
                            _events.tryEmit(SocketEvent.ActionResolved(id, status))
                        }
                        "conversations" -> {
                            val arr = json.optJSONArray("items") ?: return
                            val items = mutableListOf<ConversationItem>()
                            for (i in 0 until arr.length()) {
                                val obj = arr.getJSONObject(i)
                                items.add(
                                    ConversationItem(
                                        id = obj.optString("id"),
                                        title = obj.optString("first_user_prompt", "New Conversation"),
                                        lastSnippet = obj.optString("last_snippet", ""),
                                        totalSteps = obj.optInt("total_steps", 0),
                                        updatedAt = obj.optLong("updated_at", 0)
                                    )
                                )
                            }
                            _events.tryEmit(SocketEvent.ConversationsList(items))
                        }
                    }
                } catch (e: Exception) {
                    Log.e("WebSocket", "Failed to parse message: $text", e)
                }
            }

            override fun onFailure(webSocket: WebSocket, t: Throwable, response: Response?) {
                Log.e("WebSocket", "Connection error: ${t.message}")
                _events.tryEmit(SocketEvent.Disconnected(t.message ?: "Connection failure"))
            }

            override fun onClosed(webSocket: WebSocket, code: Int, reason: String) {
                Log.d("WebSocket", "Closed: $code $reason")
                _events.tryEmit(SocketEvent.Disconnected(reason))
            }
        })
    }

    fun sendPrompt(prompt: String, conversationId: String? = null) {
        val payload = JSONObject().apply {
            put("type", "user_input")
            put("content", prompt)
            conversationId?.let { put("conversation_id", it) }
        }
        webSocket?.send(payload.toString())
    }

    fun resolveAction(actionId: String, approve: Boolean) {
        val payload = JSONObject().apply {
            put("type", "resolve_action")
            put("action_id", actionId)
            put("status", if (approve) "approved" else "denied")
        }
        webSocket?.send(payload.toString())
    }

    fun requestConversations() {
        val payload = JSONObject().apply {
            put("type", "list_conversations")
        }
        webSocket?.send(payload.toString())
    }

    fun selectConversation(conversationId: String) {
        val payload = JSONObject().apply {
            put("type", "attach_conversation")
            put("conversation_id", conversationId)
        }
        webSocket?.send(payload.toString())
    }

    fun disconnect() {
        webSocket?.close(1000, "Client disconnect")
        webSocket = null
    }
}
