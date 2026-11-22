# Antigravity Mobile & Remote Bridge Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a complete mobile companion system for Antigravity consisting of a Python PC Host Daemon (mDNS discovery, WebSocket streaming, session supervisor, Telegram relay) and a native Android Jetpack Compose app featuring a ChatGPT/Gemini/Claude-style chat canvas, full sidebar drawer (workspaces, past history, new chats), collapsible tool-call cards, and lock-screen command approvals.

**Architecture:**
- **PC Host Daemon (`tools/antigravity_bridge/`):** FastAPI + WebSockets + Zeroconf mDNS service broadcasting `_antigravity._tcp.local.`. Reads and supervises Antigravity transcript files in `<appDataDir>/brain/`, exposing streaming tokens, tool state, and an atomic action approval state machine. Embedded Telegram bot relays urgent alerts and allows remote approvals over cellular data.
- **Android App (`antigravity-mobile/`):** Kotlin + Jetpack Compose + Material 3 app targeting 120Hz fluid rendering. Discovers the PC automatically via Android `NsdManager`, pairs via 4-digit PIN, renders Markdown/syntax-highlighted code, and runs a lightweight `ForegroundService` for lock-screen interactive approval notifications.

**Tech Stack:**
- **Host:** Python 3.10+, `fastapi`, `uvicorn`, `websockets`, `zeroconf`, `python-telegram-bot` (or standard `urllib` polling).
- **Client:** Android 11+ (API 30–35), Kotlin 2.0+, Jetpack Compose, Material 3, Ktor Client (WebSocket), Kotlinx Serialization, Android `NsdManager`.

**Spec:** `docs/specs/2026-11-22-antigravity-mobile-chat-design.md`

---

## Global Constraints

- **Host OS & Shell:** Windows 11 / PowerShell. Python scripts enforce UTF-8 output (`sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')`).
- **File Paths Protocol:** All file/folder paths formatted in single-line code blocks for one-tap copy.
- **Network Boundary:** Local Wi-Fi for direct phone-to-PC WebSocket; HTTPS for Telegram Bot API.
- **Zero Polling UI:** Pure reactive event flows via Kotlin `StateFlow` and WebSocket events.

---

## Review Focus

1. **mDNS Packet Loss / Router Multicast Isolation:** Some home Wi-Fi routers drop UDP multicast packets. If `NsdManager` does not resolve the service within 5 seconds, the app must present a graceful manual IP/Port fallback dialog.
2. **Doze Mode Battery Optimization:** Android OS killing background WebSockets. The Android app must maintain a low-power `ForegroundService` with a sticky notification so action approvals are never missed when the screen turns off.
3. **Atomic Action Resolution Race:** Approving an action via Android while simultaneously clicking approve on Telegram. The daemon must atomically resolve the action on the first tap and broadcast `action_resolved` to revoke the button on all other channels.
4. **Large Transcript Deserialization:** Historical conversation transcripts can reach megabytes. The transcript watcher must tail new lines incrementally rather than reading the entire file on every token.
5. **Session Disconnection Reconnect Loop:** Phone drops Wi-Fi momentarily. Client must use exponential backoff reconnection with state resumption.

---

### Task 1: PC Bridge Daemon - Core Server, Auth & Zeroconf Discovery

**Files:**
- Create: `tools/antigravity_bridge/__init__.py`
- Create: `tools/antigravity_bridge/config.py`
- Create: `tools/antigravity_bridge/discovery.py`
- Create: `tools/antigravity_bridge/auth.py`
- Create: `tools/antigravity_bridge/server.py`
- Test: `tests/test_bridge_auth_and_discovery.py`

**Interfaces:**
- Produces: `start_bridge_server(port: int = 8765)` running FastAPI + WebSocket gateway and advertising mDNS `_antigravity._tcp.local.`.
- Produces: `verify_pin(pin: str) -> bool` and `generate_pairing_pin() -> str`.

- [ ] **Step 1: Write the failing test for PIN generation, verification, and mDNS payload formatting**

```python
# tests/test_bridge_auth_and_discovery.py
from tools.antigravity_bridge.auth import PairingManager
from tools.antigravity_bridge.discovery import get_service_info_payload

def test_pin_verification():
    mgr = PairingManager(secret_file="test_pin.json")
    pin = mgr.get_or_create_pin()
    assert len(pin) == 4 and pin.isdigit()
    assert mgr.verify_pin(pin) is True
    assert mgr.verify_pin("9999") is False

def test_discovery_payload():
    payload = get_service_info_payload("Nikhil-PC", 8765)
    assert payload["type"] == "_antigravity._tcp.local."
    assert payload["port"] == 8765
```

- [ ] **Step 2: Run test to verify it fails**
Run: `python -m pytest tests/test_bridge_auth_and_discovery.py`  
Expected: FAIL (modules not found)

- [ ] **Step 3: Implement `PairingManager`, `discovery.py`, and `server.py`**
Implement the FastAPI app with endpoints `/api/health`, `/api/pair`, and `/ws/client` using `zeroconf` and `websockets`.

- [ ] **Step 4: Run test to verify it passes**
Run: `python -m pytest tests/test_bridge_auth_and_discovery.py`  
Expected: PASS

- [ ] **Step 5: Commit**
```bash
git add tools/antigravity_bridge/ tests/test_bridge_auth_and_discovery.py
git commit -m "feat(bridge): implement core server, pin auth, and mdns discovery"
```

---

### Task 2: PC Bridge Daemon - Workspace Indexer, Transcript Streamer & Action State Machine

**Files:**
- Create: `tools/antigravity_bridge/indexer.py`
- Create: `tools/antigravity_bridge/transcript_tailer.py`
- Create: `tools/antigravity_bridge/action_state.py`
- Modify: `tools/antigravity_bridge/server.py`
- Test: `tests/test_bridge_indexer_and_actions.py`

**Interfaces:**
- Consumes: `PairingManager` from Task 1.
- Produces: `get_conversations_index(brain_dir: str) -> list[dict]`
- Produces: `ActionStateMachine` with `register_action(id, prompt) -> dict`, `resolve_action(id, status: str) -> bool`.
- Produces: `TranscriptTailer` streaming incremental JSONL steps to WebSocket clients.

- [ ] **Step 1: Write the failing test for indexer and atomic action resolution**

```python
# tests/test_bridge_indexer_and_actions.py
import pytest
from tools.antigravity_bridge.action_state import ActionStateMachine

def test_atomic_action_resolution():
    state = ActionStateMachine()
    action = state.register_action(action_id="act-1", description="Run git commit")
    assert action["status"] == "pending"
    assert state.resolve_action("act-1", "approved") is True
    assert state.get_action("act-1")["status"] == "approved"
    # Duplicate resolution returns False (atomic guard)
    assert state.resolve_action("act-1", "denied") is False
```

- [ ] **Step 2: Run test to verify it fails**
Run: `python -m pytest tests/test_bridge_indexer_and_actions.py`  
Expected: FAIL

- [ ] **Step 3: Implement `ActionStateMachine`, `indexer.py`, and `transcript_tailer.py`**
Implement indexing of `<appDataDir>/brain/<id>/` transcripts, parsing steps (`PLANNER_RESPONSE`, `USER_INPUT`, tool calls), and streaming deltas.

- [ ] **Step 4: Run test to verify it passes**
Run: `python -m pytest tests/test_bridge_indexer_and_actions.py`  
Expected: PASS

- [ ] **Step 5: Commit**
```bash
git add tools/antigravity_bridge/ tests/test_bridge_indexer_and_actions.py
git commit -m "feat(bridge): add conversation indexer, transcript tailer, and action state machine"
```

---

### Task 3: PC Bridge Daemon - Telegram Bot Dual-Channel Relay

**Files:**
- Create: `tools/antigravity_bridge/telegram_relay.py`
- Modify: `tools/antigravity_bridge/server.py`
- Test: `tests/test_telegram_relay.py`

**Interfaces:**
- Consumes: `ActionStateMachine` from Task 2.
- Produces: `TelegramRelay(token: str, chat_id: str, action_state: ActionStateMachine)`
- Methods: `send_alert(title: str, body: str, action_id: str | None = None)`, `handle_callback_query(callback_data: str)`.

- [ ] **Step 1: Write the failing test for Telegram callback resolution**

```python
# tests/test_telegram_relay.py
from tools.antigravity_bridge.action_state import ActionStateMachine
from tools.antigravity_bridge.telegram_relay import TelegramRelay

def test_telegram_action_callback():
    state = ActionStateMachine()
    state.register_action("act-test", "Run bash")
    relay = TelegramRelay(token="mock", chat_id="123", action_state=state)
    result = relay.process_simulated_callback("approve:act-test")
    assert result == "Action approved"
    assert state.get_action("act-test")["status"] == "approved"
```

- [ ] **Step 2: Run test to verify it fails**
Run: `python -m pytest tests/test_telegram_relay.py`  
Expected: FAIL

- [ ] **Step 3: Implement `telegram_relay.py`**
Implement the Telegram notification engine with inline keyboards for approvals and polling for user replies.

- [ ] **Step 4: Run test to verify it passes**
Run: `python -m pytest tests/test_telegram_relay.py`  
Expected: PASS

- [ ] **Step 5: Commit**
```bash
git add tools/antigravity_bridge/telegram_relay.py tests/test_telegram_relay.py
git commit -m "feat(bridge): add telegram bot relay with atomic inline keyboard approval"
```

---

### Task 4: Android App - Project Scaffold, mDNS Discovery & WebSocket Engine

**Files:**
- Create: `antigravity-mobile/settings.gradle.kts`
- Create: `antigravity-mobile/app/build.gradle.kts`
- Create: `antigravity-mobile/app/src/main/AndroidManifest.xml`
- Create: `antigravity-mobile/app/src/main/java/com/antigravity/mobile/data/model/Models.kt`
- Create: `antigravity-mobile/app/src/main/java/com/antigravity/mobile/data/discovery/NsdDiscoveryManager.kt`
- Create: `antigravity-mobile/app/src/main/java/com/antigravity/mobile/data/network/AntigravitySocketClient.kt`

**Interfaces:**
- Produces: `NsdDiscoveryManager.discoverService(): Flow<DiscoveryState>`
- Produces: `AntigravitySocketClient.connect(host: String, port: int, pin: String): Flow<SocketEvent>`

- [ ] **Step 1: Create Gradle configuration and models for messages, tools, and actions**
Define data classes: `ChatMessage`, `ToolStep`, `ActionApproval`, `ConversationMeta`.

- [ ] **Step 2: Implement `NsdDiscoveryManager` using Android `NsdManager`**
Listens for service `_antigravity._tcp`, resolves host address and port, and emits `Discovered(host, port)`.

- [ ] **Step 3: Implement `AntigravitySocketClient` with Ktor / OkHttp WebSockets**
Handles authentication handshake (`{"type": "auth", "pin": "..."}`), sends outgoing prompts, and receives streaming tokens.

- [ ] **Step 4: Verification**
Verify Gradle sync / syntax of discovery and socket models.

- [ ] **Step 5: Commit**
```bash
git add antigravity-mobile/
git commit -m "feat(android): scaffold android project with mDNS discovery and websocket client"
```

---

### Task 5: Android App - ChatGPT/Claude-Style Chat Canvas & Navigation Drawer

**Files:**
- Create: `antigravity-mobile/app/src/main/java/com/antigravity/mobile/ui/theme/Theme.kt`
- Create: `antigravity-mobile/app/src/main/java/com/antigravity/mobile/ui/components/SidebarDrawer.kt`
- Create: `antigravity-mobile/app/src/main/java/com/antigravity/mobile/ui/components/ToolCard.kt`
- Create: `antigravity-mobile/app/src/main/java/com/antigravity/mobile/ui/components/ApprovalBanner.kt`
- Create: `antigravity-mobile/app/src/main/java/com/antigravity/mobile/ui/screens/ChatScreen.kt`
- Create: `antigravity-mobile/app/src/main/java/com/antigravity/mobile/MainActivity.kt`

**Interfaces:**
- Produces: `ChatScreen(viewModel: ChatViewModel)`
- Features:
  - Material 3 navigation drawer showing workspaces and conversation history.
  - Streaming token chat bubble layout.
  - Collapsible tool execution card with step badges.
  - Sticky approval banner with `[ Proceed ]` and `[ Deny ]` triggers.

- [ ] **Step 1: Implement Theme and Navigation Drawer**
Build drawer with Project Selector, New Chat button, and grouped historical conversation list.

- [ ] **Step 2: Implement Chat Screen & Collapsible Tool Cards**
Build `ToolCard` (showing command line, file diffs, execution output accordion) and `ApprovalBanner`.

- [ ] **Step 3: Implement Markdown message bubbles with copy-to-clipboard code blocks**
Render styled typography, math/code tags, and action buttons.

- [ ] **Step 4: Commit**
```bash
git add antigravity-mobile/app/src/main/java/com/antigravity/mobile/ui/
git commit -m "feat(android): build chatgpt/claude-style chat canvas, sidebar drawer, and tool cards"
```

---

### Task 6: Android App - Foreground Service & Interactive Lock-Screen Approvals

**Files:**
- Create: `antigravity-mobile/app/src/main/java/com/antigravity/mobile/service/AntigravityForegroundService.kt`
- Modify: `antigravity-mobile/app/src/main/AndroidManifest.xml`
- Create: `antigravity-mobile/app/src/main/java/com/antigravity/mobile/service/NotificationReceiver.kt`

**Interfaces:**
- Produces: `AntigravityForegroundService` maintaining low-overhead WebSocket state while screen is locked.
- Produces: Notification with action buttons `[Approve]` and `[Deny]` delivering `PendingIntent` to `NotificationReceiver`.

- [ ] **Step 1: Implement `AntigravityForegroundService` with persistent notification channel**
Configures `FOREGROUND_SERVICE_TYPE_DATA_SYNC` and lifecycle observers.

- [ ] **Step 2: Implement `NotificationReceiver` to handle lock-screen approvals**
Sends approval WebSocket packet directly from notification action without opening the full UI.

- [ ] **Step 3: Commit**
```bash
git add antigravity-mobile/app/src/main/java/com/antigravity/mobile/service/
git commit -m "feat(android): add foreground service with lock-screen action approval buttons"
```

---

### Task 7: End-to-End Build & Automated Packaging Script

**Files:**
- Create: `scripts/run_antigravity_bridge.ps1`
- Create: `scripts/build_mobile_apk.ps1`
- Create: `README_MOBILE.md`

**Interfaces:**
- `run_antigravity_bridge.ps1`: Starts the PC daemon, launches mDNS advertising, displays the 4-digit PIN, and connects Telegram relay.
- `build_mobile_apk.ps1`: Builds the debug APK and places it in `build_apk/antigravity-mobile.apk`.

- [ ] **Step 1: Write `run_antigravity_bridge.ps1`**
Checks dependencies (`fastapi`, `uvicorn`, `zeroconf`), installs if missing, and boots the host server.

- [ ] **Step 2: Write `build_mobile_apk.ps1`**
Invokes Gradle build (`./gradlew assembleDebug`), verifies APK existence, and outputs the install path.

- [ ] **Step 3: Write `README_MOBILE.md` with 1-tap setup guide**

- [ ] **Step 4: Commit**
```bash
git add scripts/ README_MOBILE.md
git commit -m "feat: add bridge launch and mobile apk automated build scripts"
```
