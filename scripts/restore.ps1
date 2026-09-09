# ==============================================================================
# Customer Service AI Automation System - Restore Script
# ==============================================================================

[CmdletBinding()]
param (
    [string]$ProjectDir = "E:\NexaServe",
    [string]$BackupDir = "E:\NexaServe\backups",
    [string]$BackupFolder = ""
)

$ErrorActionPreference = "Stop"

Write-Host "==================================================" -ForegroundColor Cyan
Write-Host " Customer Service AI - System Restore Initiated" -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan

# 1. Determine backup folder
if (-not $BackupFolder) {
    $latest = Get-ChildItem -Path $BackupDir -Directory | Sort-Object CreationTime -Descending | Select-Object -First 1
    if (-not $latest) {
        Write-Error "No backup folders found in $BackupDir."
        exit 1
    }
    $targetFolder = $latest.FullName
} else {
    if (Test-Path $BackupFolder) {
        $targetFolder = $BackupFolder
    } else {
        $targetFolder = Join-Path $BackupDir $BackupFolder
    }
}

if (-not (Test-Path $targetFolder)) {
    Write-Error "Target backup folder does not exist: $targetFolder"
    exit 1
}

Write-Host "[+] Restoring from: $targetFolder" -ForegroundColor Yellow

# Parse .env
$envFile = Join-Path $ProjectDir ".env"
$envVars = @{}
Get-Content $envFile | ForEach-Object {
    $line = $_.Trim()
    if ($line -and -not $line.StartsWith("#") -and $line.Contains("=")) {
        $parts = $line.Split("=", 2)
        $envVars[$parts[0].Trim()] = $parts[1].Trim()
    }
}
$pgUser = if ($envVars["POSTGRES_USER"]) { $envVars["POSTGRES_USER"] } else { "postgres" }

# 2. Stop n8n to prevent database locks during restoration
Write-Host "[+] Stopping n8n service temporarily..." -ForegroundColor Yellow
docker compose -f (Join-Path $ProjectDir "docker-compose.yml") stop n8n

# 3. Restore PostgreSQL
$clusterDump = Join-Path $targetFolder "postgres_cluster_all.sql"
if (Test-Path $clusterDump) {
    Write-Host "[+] Restoring full cluster from $clusterDump..." -ForegroundColor Yellow
    Get-Content $clusterDump | docker exec -i cs-postgres psql -U $pgUser -d postgres
    Write-Host "    ✓ Full cluster restored successfully." -ForegroundColor Green
} else {
    Write-Host "[+] Full cluster dump not found, checking individual dumps..." -ForegroundColor Yellow
    $n8nDb = if ($envVars["N8N_DB_NAME"]) { $envVars["N8N_DB_NAME"] } else { "n8n" }
    $csDb = if ($envVars["CS_DB_NAME"]) { $envVars["CS_DB_NAME"] } else { "customerservice" }

    $n8nDump = Join-Path $targetFolder "postgres_${n8nDb}.sql"
    if (Test-Path $n8nDump) {
        Get-Content $n8nDump | docker exec -i cs-postgres psql -U $pgUser -d $n8nDb
        Write-Host "    ✓ Database $n8nDb restored." -ForegroundColor Green
    }
    $csDump = Join-Path $targetFolder "postgres_${csDb}.sql"
    if (Test-Path $csDump) {
        Get-Content $csDump | docker exec -i cs-postgres psql -U $pgUser -d $csDb
        Write-Host "    ✓ Database $csDb restored." -ForegroundColor Green
    }
}

# 4. Restart n8n
Write-Host "[+] Restarting n8n service..." -ForegroundColor Yellow
docker compose -f (Join-Path $ProjectDir "docker-compose.yml") start n8n
Start-Sleep -Seconds 5

# 5. Restore n8n workflows if export exists
$workflowsExport = Join-Path $targetFolder "n8n_workflows_export.json"
if (Test-Path $workflowsExport) {
    Write-Host "[+] Importing n8n workflows from $workflowsExport..." -ForegroundColor Yellow
    docker cp $workflowsExport "cs-n8n:/tmp/restore_workflows.json"
    docker exec cs-n8n n8n import:workflow --input=/tmp/restore_workflows.json
    docker exec cs-n8n rm -f /tmp/restore_workflows.json
    Write-Host "    ✓ n8n workflows imported." -ForegroundColor Green
}

Write-Host "==================================================" -ForegroundColor Cyan
Write-Host " Restore Completed Successfully!" -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan
