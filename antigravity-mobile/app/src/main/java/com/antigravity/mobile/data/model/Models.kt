package com.antigravity.mobile.data.model

data class ChatMessage(
    val id: String,
    val sender: Sender,
    val content: String,
    val timestamp: Long = System.currentTimeMillis(),
    val isStreaming: Boolean = false,
    val toolCalls: List<ToolCall> = emptyList(),
    val pendingApproval: ActionApproval? = null
)

enum class Sender {
    USER,
    AGENT
}

data class ToolCall(
    val id: String,
    val toolName: String,
    val summary: String,
    val command: String = "",
    val status: ToolStatus = ToolStatus.RUNNING,
    val output: String = "",
    val isExpanded: Boolean = false
)

enum class ToolStatus {
    RUNNING,
    COMPLETED,
    FAILED
}

data class ActionApproval(
    val id: String,
    val description: String,
    val status: ApprovalStatus = ApprovalStatus.PENDING
)

enum class ApprovalStatus {
    PENDING,
    APPROVED,
    DENIED
}

data class ConversationItem(
    val id: String,
    val title: String,
    val lastSnippet: String,
    val totalSteps: Int,
    val updatedAt: Long
)

sealed class ConnectionState {
    object Disconnected : ConnectionState()
    object Discovering : ConnectionState()
    object Connecting : ConnectionState()
    data class PairingRequired(val host: String, val port: Int) : ConnectionState()
    data class Connected(val host: String, val port: Int, val deviceName: String) : ConnectionState()
    data class Error(val message: String) : ConnectionState()
}
