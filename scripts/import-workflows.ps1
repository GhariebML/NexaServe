# ==============================================================================
# Customer Service AI Platform - Automated Workflow Deployment Script
# ==============================================================================

[CmdletBinding()]
param (
    [string]$ProjectDir = "E:\NexaServe"
)

$ErrorActionPreference = "Stop"

Write-Host "==================================================" -ForegroundColor Cyan
Write-Host " Deploying Customer Service Modular Workflow Suite" -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan

$workflowsDir = Join-Path $ProjectDir "infra\n8n\workflows"
if (-not (Test-Path $workflowsDir)) {
    Write-Error "Workflows directory not found at $workflowsDir"
    exit 1
}

# 1. Fetch Project ID from n8n database
$projectIdQuery = docker exec cs-postgres psql -U postgres -d n8n -t -c "SELECT id FROM project LIMIT 1;" 2>&1
$projectId = ($projectIdQuery -join "").Trim()
Write-Host "[+] Target n8n Project ID: $projectId" -ForegroundColor Green

# 2. Create temp directory in container
docker exec cs-n8n mkdir -p /tmp/workflows

# 3. Import each workflow
$workflowFiles = Get-ChildItem -Path $workflowsDir -Filter "*.json" | Sort-Object Name
foreach ($wf in $workflowFiles) {
    $containerDest = "/tmp/workflows/$($wf.Name)"
    Write-Host "[+] Copying and importing: $($wf.Name)..." -ForegroundColor Yellow
    docker cp $wf.FullName "cs-n8n:$containerDest"
    
    $importOut = docker exec cs-n8n n8n import:workflow --input=$containerDest --projectId=$projectId 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "    [OK] Imported $($wf.Name)" -ForegroundColor Green
    } else {
        Write-Warning "    [WARN] Error importing $($wf.Name): $importOut"
    }
}

# 4. Activate Master Dispatcher Workflow
Write-Host "[+] Publishing Master Gateway Dispatcher (CSWF000000000001)..." -ForegroundColor Yellow
docker exec cs-n8n n8n publish:workflow --id=CSWF000000000001 | Out-Null

# 5. Restart n8n container to register active webhooks in memory
Write-Host "[+] Reloading n8n to register active webhook listeners..." -ForegroundColor Yellow
docker compose -f (Join-Path $ProjectDir "docker-compose.yml") restart n8n | Out-Null
Start-Sleep -Seconds 6

$activeWfs = docker exec cs-postgres psql -U postgres -d n8n -c "SELECT id, name, active FROM workflow_entity ORDER BY id;"
Write-Host "`nDeployed Workflows in n8n:" -ForegroundColor Cyan
Write-Host $activeWfs

Write-Host "`n==================================================" -ForegroundColor Cyan
Write-Host " [OK] All modular workflows deployed successfully!" -ForegroundColor Green
Write-Host " Webhook Endpoint: http://localhost:5678/webhook/customer-service" -ForegroundColor Green
Write-Host "==================================================" -ForegroundColor Cyan
