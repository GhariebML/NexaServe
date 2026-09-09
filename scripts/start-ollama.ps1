# scripts/start-ollama.ps1
$ErrorActionPreference = "Stop"

$ollamaExe = "C:\Users\LAPTOPS HOUSE\AppData\Local\Programs\Ollama\ollama.exe"
if (-not (Test-Path $ollamaExe)) {
    $found = Get-Command ollama -ErrorAction SilentlyContinue
    if ($found) { $ollamaExe = $found.Source }
}

# Stop any existing ollama
Get-Process -Name "ollama*", "ollama app*" -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 1

Write-Host "[*] Launching detached Ollama serve via WMI..." -ForegroundColor Cyan

$cmdLine = "cmd.exe /c set OLLAMA_HOST=0.0.0.0:11434&& set OLLAMA_ORIGINS=*&& `"$ollamaExe`" serve"

$res = Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{ CommandLine = $cmdLine }
if ($res.ReturnValue -ne 0) {
    Write-Error "Failed to launch Ollama via WMI: $($res.ReturnValue)"
    exit 1
}

Write-Host "[*] Waiting for Ollama API to respond..."
$ready = $false
for ($i = 0; $i -lt 20; $i++) {
    Start-Sleep -Seconds 1
    try {
        $resp = Invoke-RestMethod -Uri "http://127.0.0.1:11434/api/tags" -TimeoutSec 2 -ErrorAction Stop
        if ($resp) {
            $ready = $true
            break
        }
    } catch {}
}

if ($ready) {
    Write-Host "[+] Ollama is online and detached!" -ForegroundColor Green
    $models = (Invoke-RestMethod -Uri "http://127.0.0.1:11434/api/tags").models
    foreach ($m in $models) {
        Write-Host "    - $($m.name)" -ForegroundColor Cyan
    }
} else {
    Write-Error "Ollama failed to respond"
}
