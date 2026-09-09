# ==============================================================================
# Customer Service AI Automation System - Automated Backup Script
# ==============================================================================

[CmdletBinding()]
param (
    [string]$ProjectDir = "E:\NexaServe",
    [string]$BackupDir = "E:\NexaServe\backups"
)

$ErrorActionPreference = "Stop"

Write-Host "==================================================" -ForegroundColor Cyan
Write-Host " Customer Service AI - System Backup Initiated" -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan

# 1. Validate environment
$envFile = Join-Path $ProjectDir ".env"
if (-not (Test-Path $envFile)) {
    Write-Error "Error: .env file not found at $envFile"
    exit 1
}

# Parse .env
$envVars = @{}
Get-Content $envFile | ForEach-Object {
    $line = $_.Trim()
    if ($line -and -not $line.StartsWith("#") -and $line.Contains("=")) {
        $parts = $line.Split("=", 2)
        $envVars[$parts[0].Trim()] = $parts[1].Trim()
    }
}

$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$targetBackupFolder = Join-Path $BackupDir "backup_$timestamp"
New-Item -ItemType Directory -Force -Path $targetBackupFolder | Out-Null
Write-Host "[+] Target backup folder: $targetBackupFolder" -ForegroundColor Green

# 2. Backup PostgreSQL Databases
Write-Host "[+] Dumping PostgreSQL databases..." -ForegroundColor Yellow
$pgUser = if ($envVars["POSTGRES_USER"]) { $envVars["POSTGRES_USER"] } else { "postgres" }
$n8nDb = if ($envVars["N8N_DB_NAME"]) { $envVars["N8N_DB_NAME"] } else { "n8n" }
$csDb = if ($envVars["CS_DB_NAME"]) { $envVars["CS_DB_NAME"] } else { "customerservice" }

# Full cluster dump
$clusterDumpFile = Join-Path $targetBackupFolder "postgres_cluster_all.sql"
docker exec cs-postgres pg_dumpall -U $pgUser > $clusterDumpFile
if ($LASTEXITCODE -eq 0 -and (Test-Path $clusterDumpFile)) {
    $size = (Get-Item $clusterDumpFile).Length / 1KB
    Write-Host "    [OK] Full cluster dump saved: postgres_cluster_all.sql ($([math]::Round($size, 2)) KB)" -ForegroundColor Green
} else {
    Write-Warning "    [WARN] Failed to complete full cluster dump."
}

# Individual database dumps
$n8nDumpFile = Join-Path $targetBackupFolder "postgres_${n8nDb}.sql"
docker exec cs-postgres pg_dump -U $pgUser -d $n8nDb -F p > $n8nDumpFile
if ($LASTEXITCODE -eq 0) {
    Write-Host "    [OK] n8n database dump saved: postgres_${n8nDb}.sql" -ForegroundColor Green
}

$csDumpFile = Join-Path $targetBackupFolder "postgres_${csDb}.sql"
docker exec cs-postgres pg_dump -U $pgUser -d $csDb -F p > $csDumpFile
if ($LASTEXITCODE -eq 0) {
    Write-Host "    [OK] Customer Service database dump saved: postgres_${csDb}.sql" -ForegroundColor Green
}

# 3. Export n8n Workflows and Credentials via n8n CLI
Write-Host "[+] Exporting n8n workflows and credentials..." -ForegroundColor Yellow
$n8nWorkflowsExport = Join-Path $targetBackupFolder "n8n_workflows_export.json"
docker exec cs-n8n n8n export:workflow --all --output=/tmp/workflows_export.json 2>$null
if ($LASTEXITCODE -eq 0) {
    docker cp "cs-n8n:/tmp/workflows_export.json" $n8nWorkflowsExport
    docker exec cs-n8n rm -f /tmp/workflows_export.json
    Write-Host "    [OK] Exported n8n workflows to $n8nWorkflowsExport" -ForegroundColor Green
} else {
    Write-Host "    [INFO] No active workflows to export or n8n export returned empty." -ForegroundColor Gray
}

# 4. Backup configuration files
Write-Host "[+] Archiving configuration and metadata..." -ForegroundColor Yellow
Copy-Item (Join-Path $ProjectDir "docker-compose.yml") -Destination $targetBackupFolder
Copy-Item (Join-Path $ProjectDir ".env.example") -Destination $targetBackupFolder

# Write manifest
$manifest = [PSCustomObject]@{
    timestamp = (Get-Date).ToString("o")
    version = "1.0.0"
    files = Get-ChildItem $targetBackupFolder | Select-Object Name, Length
}
$manifest | ConvertTo-Json -Depth 3 | Set-Content (Join-Path $targetBackupFolder "manifest.json")

Write-Host "==================================================" -ForegroundColor Cyan
Write-Host " Backup Completed Successfully!" -ForegroundColor Cyan
Write-Host " Saved to: $targetBackupFolder" -ForegroundColor Green
Write-Host "==================================================" -ForegroundColor Cyan
