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

$python = (Get-Command python -ErrorAction SilentlyContinue).Source
if (-not $python) {
    Write-Error "Python 3 is required but not found in PATH."
    exit 1
}

$env:PYTHONPATH = "$PSScriptRoot\.."
Write-Host "[*] Booting FastAPI WebSocket Gateway on 0.0.0.0:$Port..." -ForegroundColor Yellow
python -c "
from tools.antigravity_bridge.server import run_bridge_server
run_bridge_server(port=$Port)
"
