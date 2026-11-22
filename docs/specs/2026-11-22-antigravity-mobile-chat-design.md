# Antigravity Mobile: Full Remote Companion Specification

**Date:** 2026-11-22  
**Status:** Ready for User Approval (Brainstorming Phase)  
**File Path:** `docs/specs/2026-11-22-antigravity-mobile-chat-design.md`

---

## 1. Intent and Vision
**Antigravity Mobile** brings 1:1 functional parity of the Antigravity desktop experience to an Android device. It delivers a native, buttery 120Hz ChatGPT/Gemini/Claude-styled interface over local Wi-Fi, allowing the user to manage projects, start new conversations, review historical sessions, monitor live tool execution, and approve commands anywhere in the house, with an emergency/out-of-home Telegram relay.

---

## 2. Scope & Capabilities

### Core Features (1:1 Antigravity Desktop Parity on Mobile)
1. **Navigation Drawer (Antigravity Sidebar on Mobile):**
   - **Workspace / Project Switcher:** Select from configured PC directories and projects.
   - **Conversation History:** Categorized list of past conversations (Today, Previous 7 Days, Older) read directly from `<appDataDir>/brain/`.
   - **New Conversation (+):** Instant button to spawn a new clean chat session in the selected workspace.
   - **Artifacts & Transcripts Browser:** Quick inspection of generated plans, markdown reports, and media.
2. **ChatGPT / Claude / Gemini-Style Chat Canvas:**
   - **Real-Time Streaming:** Live token rendering as the agent generates thought and responses.
   - **Collapsible Tool Execution Cards:** Visual cards for terminal runs, file diffs/edits, and subagents with step badges (`running`, `done`, `failed`) and expandable outputs.
   - **Interactive Action Approvals:** Sticky card when terminal commands or actions require user sign-off (`[ Approve ]` / `[ Deny ]`), synchronized across devices.
   - **Rich Markdown & Code Highlighting:** Formatted tables, alerts, and syntax-highlighted code blocks with 1-tap copy.
3. **Connectivity & Security:**
   - **Zero-Config Wi-Fi Pairing:** mDNS/Zeroconf discovery (`_antigravity._tcp`) finds the PC automatically.
   - **Pairing PIN:** One-time 4-digit code shown on the desktop terminal on first connect, saved securely in Android `EncryptedSharedPreferences`.
   - **Android Foreground Service:** Persistent local connection with interactive lock-screen notifications to approve actions without unlocking the phone.
4. **Dual-Channel Telegram Relay:**
   - Built-in bot in the PC daemon that sends high-priority notifications when away from Wi-Fi.
   - Inline keyboard approval (`[ Approve ]` / `[ Deny ]`) that atomically resolves actions across both Android and Telegram.

---

## 3. Architecture Overview

```
 ┌──────────────────────────────────────────────────────────────┐
 │                      Android Phone (Client)                  │
 │  - Jetpack Compose + Material 3 (120Hz Fluid UI)            │
 │  - Navigation Drawer: Workspaces + Conversation History      │
 │  - WebSocket Client (Ktor) + mDNS Discovery (NsdManager)     │
 │  - Foreground Service for Instant Lock-Screen Approvals     │
 └──────────────────────────────┬───────────────────────────────┘
                                │ Local Wi-Fi (WebSocket + REST)
                                ▼
 ┌──────────────────────────────────────────────────────────────┐
 │                    PC Host Daemon (Python)                   │
 │  - FastAPI / WebSockets Server + Zeroconf mDNS Broadcaster  │
 │  - Antigravity Bridge: Session Supervisor + Transcript Watch │
 │  - Workspace & History Indexer (<appDataDir>/brain/)         │
 │  - Atomic Action State Machine (Resolves approvals)          │
 └──────────────────────────────┬───────────────────────────────┘
                                │ Telegram Bot API (HTTPS)
                                ▼
 ┌──────────────────────────────────────────────────────────────┐
 │                  Telegram (Cellular / Remote)                │
 │  - Push alerts on task completion or pending approval        │
 │  - Inline keyboard [Approve] / [Deny]                        │
 └──────────────────────────────────────────────────────────────┘
```

---

## 4. Key Technical Decisions (Builder Calls)
- **Session Supervision:** The PC daemon acts as a full supervisor. It monitors `<appDataDir>/brain/` for active transcript streaming and can invoke the Antigravity agent CLI/SDK for new conversations.
- **Atomic State Machine:** When an approval prompt triggers, both the Android app and the Telegram bot display approval buttons. Whichever channel is clicked first atomically resolves the request, updates the Telegram message (`✅ Approved via Android`), and dismisses the mobile card.
- **Doze Mode Resilience:** Android client uses a low-overhead foreground service when connected to local Wi-Fi to keep the WebSocket connection responsive without being killed by Android battery management.

---

## 5. Next Steps
Upon user approval of this specification, the next step is to invoke `writing-plans` to produce a step-by-step implementation plan covering the PC Python daemon, Telegram integration, and Android Jetpack Compose application.
