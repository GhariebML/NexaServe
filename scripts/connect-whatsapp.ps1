# ==============================================================================
# NexaServe Customer Service AI - WhatsApp Account Connection Manager
# ==============================================================================

[CmdletBinding()]
param (
    [int]$Port = 8080,
    [switch]$NoBrowser
)

$ErrorActionPreference = "Continue"

Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host " NexaServe AI Customer Service - WhatsApp Real Account Setup" -ForegroundColor Cyan
Write-Host "======================================================================" -ForegroundColor Cyan

$bridgeDir = "E:\NexaServe\infra\whatsapp"
$url = "http://localhost:$Port"

# 1. Check if node is available
$node = Get-Command node -ErrorAction SilentlyContinue
if (-not $node) {
    Write-Error "Node.js is not found on PATH. Please ensure Node.js is installed."
    exit 1
}

# 2. Check if bridge dependencies are installed
if (-not (Test-Path "$bridgeDir\node_modules")) {
    Write-Host "Installing WhatsApp bridge dependencies..." -ForegroundColor Yellow
    Push-Location $bridgeDir
    npm install --silent
    Pop-Location
}

# 3. Check if WhatsApp bridge is already running
$running = $false
try {
    $resp = Invoke-RestMethod -Uri "$url/health" -TimeoutSec 2 -ErrorAction SilentlyContinue
    if ($resp.service -eq "nexaserve-whatsapp-bridge") {
        $running = $true
    }
} catch {}

if (-not $running) {
    $nodeCmd = "cmd.exe /c cd /d `"$bridgeDir`" && node.exe server.js"
    $res = Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{ CommandLine = $nodeCmd }
    if ($res.ReturnValue -ne 0) {
        Write-Error "Failed to launch WhatsApp bridge via WMI: $($res.ReturnValue)"
    }
    
    Write-Host "Waiting for WhatsApp service to initialize..." -ForegroundColor Yellow
    for ($i = 0; $i -lt 15; $i++) {
        Start-Sleep -Seconds 1
        try {
            $resp = Invoke-RestMethod -Uri "$url/health" -TimeoutSec 2 -ErrorAction SilentlyContinue
            if ($resp.service -eq "nexaserve-whatsapp-bridge") {
                $running = $true
                break
            }
        } catch {}
    }
}

if (-not $running) {
    Write-Error "Failed to start WhatsApp bridge service on port $Port."
    exit 1
}

Write-Host "WhatsApp Bridge is active and online at $url" -ForegroundColor Green

# 4. Check connection state
$status = Invoke-RestMethod -Uri "$url/status" -TimeoutSec 5

if ($status.status -eq "CONNECTED") {
    Write-Host ""
    Write-Host "======================================================================" -ForegroundColor Green
    Write-Host " WHATSAPP ACCOUNT IS ALREADY CONNECTED!" -ForegroundColor Green
    Write-Host " Linked Phone Number: +$($status.phone)" -ForegroundColor Cyan
    Write-Host " Account Name:        $($status.name)" -ForegroundColor Cyan
    Write-Host " NexaServe AI is actively listening for incoming inquiries!" -ForegroundColor Green
    Write-Host "======================================================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "To test live, simply send a WhatsApp message to this number, or run:"
    Write-Host "  python scripts/test-real-whatsapp.py" -ForegroundColor Yellow
    exit 0
}

# 5. Open Web QR Code View in Default Browser
Write-Host ""
Write-Host "----------------------------------------------------------------------" -ForegroundColor Yellow
Write-Host " ACTION REQUIRED: Scan the QR Code with your WhatsApp Mobile App" -ForegroundColor Yellow
Write-Host "----------------------------------------------------------------------" -ForegroundColor Yellow
Write-Host " 1. Open WhatsApp on your phone" -ForegroundColor White
Write-Host " 2. Go to Settings (iOS) or Menu (Android) -> Linked Devices" -ForegroundColor White
Write-Host " 3. Tap 'Link a Device'" -ForegroundColor White
Write-Host " 4. Point your camera at the QR code on screen" -ForegroundColor White
Write-Host "----------------------------------------------------------------------" -ForegroundColor Yellow
Write-Host ""

if (-not $NoBrowser) {
    Write-Host "Opening QR code pairing page in your browser: $url/qr" -ForegroundColor Cyan
    Start-Process "$url/qr"
}

Write-Host "Waiting for scan... (Open $url/qr in browser)" -ForegroundColor Gray

$connected = $false
for ($attempt = 1; $attempt -le 60; $attempt++) {
    Start-Sleep -Seconds 2
    try {
        $st = Invoke-RestMethod -Uri "$url/status" -TimeoutSec 2 -ErrorAction SilentlyContinue
        if ($st.status -eq "CONNECTED") {
            $connected = $true
            Write-Host ""
            Write-Host "======================================================================" -ForegroundColor Green
            Write-Host " SUCCESS! WHATSAPP ACCOUNT CONNECTED SUCCESSFULLY!" -ForegroundColor Green
            Write-Host " Phone Number: +$($st.phone)" -ForegroundColor Cyan
            Write-Host " Account Name: $($st.name)" -ForegroundColor Cyan
            Write-Host "======================================================================" -ForegroundColor Green
            Write-Host ""
            Write-Host "Your real WhatsApp account is now linked to the NexaServe AI Agent!" -ForegroundColor Green
            break
        }
        else {
            Write-Host -NoNewline "."
        }
    } catch {}
}

if (-not $connected) {
    Write-Host ""
    Write-Host "QR code page is available at: $url/qr" -ForegroundColor Yellow
    Write-Host "Open this URL anytime in your browser to scan and link your WhatsApp account." -ForegroundColor Yellow
}
