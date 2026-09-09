Write-Host "[*] Shutting down WSL to apply .wslconfig 3.5GB memory cap..." -ForegroundColor Yellow
wsl --shutdown

Write-Host "[*] Waiting 10 seconds for WSL and Docker Desktop to reload..." -ForegroundColor Yellow
Start-Sleep -Seconds 10

$maxRetries = 20
$dockerUp = $false
for ($i = 1; $i -le $maxRetries; $i++) {
    Write-Host "[*] Checking Docker daemon status (attempt $i/$maxRetries)..."
    docker version 2>$null | Out-Null
    if ($LASTEXITCODE -eq 0) {
        $dockerUp = $true
        Write-Host "[OK] Docker daemon is UP and responding." -ForegroundColor Green
        break
    }
    Start-Sleep -Seconds 3
}

if (-not $dockerUp) {
    Write-Host "[WARN] Docker daemon not yet ready. Starting Docker Desktop..."
    Start-Process "C:\Program Files\Docker\Docker\Docker Desktop.exe"
    Start-Sleep -Seconds 15
}

Write-Host "[*] Ensuring all stack containers are running..."
docker compose -f E:\NexaServe\docker-compose.yml up -d

Write-Host "[*] Waiting 10 seconds for containers to stabilize..."
Start-Sleep -Seconds 10

docker ps
