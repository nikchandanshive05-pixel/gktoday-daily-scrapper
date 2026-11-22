# 🚀 Antigravity Mobile: Android Remote Companion

**Antigravity Mobile** brings 1:1 parity of the Antigravity desktop experience to Android, featuring a native ChatGPT/Gemini/Claude-style chat UI, real-time token streaming, full sidebar navigation (workspaces and conversation history), collapsible tool execution cards, lock-screen approvals, and out-of-home Telegram bot synchronization.

---

## ⚡ Quick Start: 3 Steps to Run

### Step 1: Start the PC Bridge Daemon
Run the launch script from PowerShell:
```powershell
.\scripts\run_antigravity_bridge.ps1
```
The terminal displays your PC's IP address, active port, and a **4-Digit Pairing PIN** (e.g. `4829`).

### Step 2: Open the Mobile App
1. Install and open **Antigravity Mobile** on your Android phone connected to the same Wi-Fi.
2. The app uses **mDNS / Zeroconf** (`_antigravity._tcp`) to detect your PC automatically within seconds.
3. If prompted, enter the 4-digit PIN displayed on your PC terminal.
4. Once paired, the connection status indicator turns 🟢 **Connected**.

*(Optional fallback: If your router isolates Wi-Fi multicast packets, tap the Wi-Fi icon in the top app bar to enter your PC IP address manually).*

### Step 3: Build & Install the APK
To compile the APK locally:
```powershell
.\scripts\build_mobile_apk.ps1
```
The generated APK will be placed at:
```
c:\Users\Nikhil-Arun\Documents\antigravity\resilient-hertz\build_apk\antigravity-mobile.apk
```

---

## 📱 Mobile Interface Features

- **Sidebar Drawer (1:1 Desktop Parity):**
  - **New Conversation (+):** Instantly start a new clean session on your PC.
  - **Conversations & History:** Browse, search, and switch between previous conversations indexed directly from your PC's `<appDataDir>/brain/`.
  - **Workspace Indicator:** Displays the active repository (`resilient-hertz`).
- **ChatGPT / Claude / Gemini Chat Canvas:**
  - Real-time token streaming with 120Hz smooth animations.
  - Collapsible tool cards for terminal runs (`run_command`), file modifications, and web searches with status badges (`RUNNING`, `COMPLETED`, `FAILED`).
  - Terminal code block expansion with 1-tap copy.
- **Interactive Action Approvals:**
  - Sticky in-chat card and heads-up lock-screen notification when Antigravity requests permission.
  - Tap `[ Proceed ]` or `[ Deny ]` without needing to sit at your desk.

---

## 🤖 Dual-Channel Telegram Setup (Away-from-Home)

When you leave home Wi-Fi and are on mobile data:
1. Create a bot with `@BotFather` on Telegram and obtain your Bot Token.
2. Find your personal Telegram Chat ID (via `@userinfobot`).
3. Create `~/.antigravity_bridge/telegram_config.json`:
```json
{
  "token": "YOUR_BOT_TOKEN",
  "chat_id": "YOUR_CHAT_ID"
}
```
4. Restart `.\scripts\run_antigravity_bridge.ps1`.
5. When Antigravity requests approval or completes a goal, you will receive an alert on Telegram with inline `[ ✅ Approve ]` and `[ ❌ Deny ]` buttons that atomically sync back to your desktop.
