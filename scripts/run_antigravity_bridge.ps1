<#
.SYNOPSIS
    Launches the Antigravity Mobile PC Bridge Daemon.
#>

param(
    [int]$Port = 8765
)

$ErrorActionPreference = "Stop"

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "       🚀 ANTIGRAVITY MOBILE - PC BRIDGE DAEMON           " -ForegroundColor Green
Write-Host "==========================================================" -ForegroundColor Cyan

# Check Python environment
$python = (Get-Command python -ErrorAction SilentlyContinue).Source
if (-not $python) {
    Write-Error "Python 3 is required but not found in PATH."
    exit 1
}

# Run the bridge
$env:PYTHONPATH = "$PSScriptRoot\.."
Write-Host "[*] Starting Bridge Service on port $Port..." -ForegroundColor Yellow
python -c "
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from tools.antigravity_bridge.server import BridgeServer

server = BridgeServer(port=$Port)
server.start_discovery()
status = server.get_status()

print('==========================================================')
print(f' Host IP      : {status[\"ip\"]}')
print(f' Port         : {status[\"port\"]}')
print(f' Pairing PIN  : \033[1;32m{status[\"pin\"]}\033[0m')
print(f' Brain Dir    : {status[\"brain_dir\"]}')
print(f' Telegram Sync: {\"Active\" if status[\"telegram_active\"] else \"Not Configured\"}')
print('==========================================================')
print('Listening for mobile connection... (Press Ctrl+C to stop)')

import time
try:
    while True:
        if server.telegram_relay:
            server.telegram_relay.poll_updates()
        time.sleep(1)
except KeyboardInterrupt:
    server.stop_discovery()
    print('\nBridge stopped cleanly.')
"
