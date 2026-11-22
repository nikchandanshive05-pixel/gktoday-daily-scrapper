<#
.SYNOPSIS
    Builds the Antigravity Mobile Android APK.
#>

$ErrorActionPreference = "Stop"

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "       📱 BUILDING ANTIGRAVITY MOBILE APK                 " -ForegroundColor Green
Write-Host "==========================================================" -ForegroundColor Cyan

$projectDir = Join-Path $PSScriptRoot "..\antigravity-mobile"
Set-Location $projectDir

Write-Host "[*] Compiling debug APK via Gradle..." -ForegroundColor Yellow
& ".\gradlew.bat" assembleDebug

$sourceApk = Join-Path $projectDir "app\build\outputs\apk\debug\app-debug.apk"
$targetDir = Join-Path $PSScriptRoot "..\build_apk"

if (Test-Path $sourceApk) {
    New-Item -ItemType Directory -Path $targetDir -Force | Out-Null
    $destApk = Join-Path $targetDir "antigravity-mobile.apk"
    Copy-Item -Path $sourceApk -Destination $destApk -Force
    Write-Host "==========================================================" -ForegroundColor Green
    Write-Host "🎉 Build Successful! APK generated at:" -ForegroundColor Green
    Write-Host "```$destApk```" -ForegroundColor White
    Write-Host "==========================================================" -ForegroundColor Green
} else {
    Write-Error "APK build finished but output file not found at $sourceApk"
}
