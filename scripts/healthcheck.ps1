# ==============================================================================
# Customer Service AI Automation System - Health Check Script
# ==============================================================================

[CmdletBinding()]
param (
    [string]$ProjectDir = "E:\NexaServe"
)

$ErrorActionPreference = "Continue"

Write-Host "==================================================" -ForegroundColor Cyan
Write-Host " Customer Service AI - System Health Audit" -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan

$results = [System.Collections.Generic.List[PSCustomObject]]::new()

function Add-Result($service, $target, $status, $details) {
    $results.Add([PSCustomObject]@{
        Service = $service
        Target  = $target
        Status  = $status
        Details = $details
    })
}

# 1. Docker Daemon
try {
    $dockerVersion = docker version --format '{{.Server.Version}}' 2>$null
    if ($dockerVersion) {
        Add-Result "Docker Daemon" "Engine" "HEALTHY" "Version $dockerVersion"
    } else {
        Add-Result "Docker Daemon" "Engine" "UNHEALTHY" "Daemon not responding"
    }
} catch {
    Add-Result "Docker Daemon" "Engine" "UNHEALTHY" $_.Exception.Message
}

# 2. Container Status
$containers = @("cs-postgres", "cs-n8n", "cs-redis")
foreach ($c in $containers) {
    $inspect = docker inspect --format '{{.State.Status}} (Health: {{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}})' $c 2>$null
    if ($LASTEXITCODE -eq 0 -and $inspect) {
        $status = if ($inspect -match "healthy|running") { "HEALTHY" } else { "STOPPED" }
        Add-Result "Container" $c $status $inspect
    } else {
        Add-Result "Container" $c "MISSING" "Container not created"
    }
}

# 3. PostgreSQL Database
try {
    $pgTest = docker exec cs-postgres pg_isready -U postgres 2>&1
    if ($LASTEXITCODE -eq 0) {
        Add-Result "PostgreSQL" "Port 5432" "HEALTHY" "Accepting connections"
    } else {
        Add-Result "PostgreSQL" "Port 5432" "UNHEALTHY" "$pgTest"
    }
} catch {
    Add-Result "PostgreSQL" "Port 5432" "ERROR" $_.Exception.Message
}

# 4. n8n HTTP Service
try {
    $n8nResp = Invoke-WebRequest -Uri "http://localhost:5678/healthz" -UseBasicParsing -TimeoutSec 5 2>&1
    if ($n8nResp.StatusCode -eq 200) {
        Add-Result "n8n Webhook/UI" "http://localhost:5678" "HEALTHY" "HTTP 200 OK"
    } else {
        Add-Result "n8n Webhook/UI" "http://localhost:5678" "DEGRADED" "HTTP $($n8nResp.StatusCode)"
    }
} catch {
    Add-Result "n8n Webhook/UI" "http://localhost:5678" "UNHEALTHY" $_.Exception.Message
}

# 5. Ollama LLM API (Host & Docker Internal Gateway)
try {
    $ollamaResp = Invoke-RestMethod -Uri "http://127.0.0.1:11434/api/tags" -TimeoutSec 5 2>&1
    if ($ollamaResp.models -ne $null) {
        $modelNames = ($ollamaResp.models | ForEach-Object { $_.name }) -join ", "
        Add-Result "Ollama API" "http://127.0.0.1:11434" "HEALTHY" "Online ($modelNames)"
    } else {
        Add-Result "Ollama API" "http://127.0.0.1:11434" "HEALTHY" "API responding (0 models)"
    }
} catch {
    Add-Result "Ollama API" "http://127.0.0.1:11434" "UNHEALTHY" $_.Exception.Message
}

# 6. Redis
try {
    $redisPong = docker exec cs-redis redis-cli ping 2>&1
    if ($redisPong -match "PONG|NOAUTH") {
        Add-Result "Redis Cache" "Port 6379" "HEALTHY" "Responding ($redisPong)"
    } else {
        Add-Result "Redis Cache" "Port 6379" "UNHEALTHY" "$redisPong"
    }
} catch {
    Add-Result "Redis Cache" "Port 6379" "ERROR" $_.Exception.Message
}

# Output Table
Write-Host ""
$results | Format-Table -AutoSize

$allHealthy = -not ($results | Where-Object { $_.Status -in "UNHEALTHY", "MISSING", "ERROR" })
if ($allHealthy) {
    Write-Host "[OK] All core services are HEALTHY and OPERATIONAL." -ForegroundColor Green
    exit 0
} else {
    Write-Host "[WARN] Some services require attention." -ForegroundColor Red
    exit 1
}
