# ==============================================================================
# NexaServe - Secure n8n Credential Synchronization Utility
# Injects credentials from .env safely into n8n's encrypted vault without storing
# raw secrets in tracked version control files.
# ==============================================================================

[CmdletBinding()]
param (
    [string]$ProjectDir = "E:\NexaServe"
)

$ErrorActionPreference = "Stop"

Write-Host "==================================================" -ForegroundColor Cyan
Write-Host " Synchronizing n8n Credentials from Environment" -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan

$envFile = Join-Path $ProjectDir ".env"
if (-not (Test-Path $envFile)) {
    Write-Error ".env file not found at $envFile"
    exit 1
}

# Parse .env
$envVars = @{}
Get-Content $envFile | ForEach-Object {
    $line = $_.Trim()
    if ($line -and -not $line.StartsWith("#") -and $line.Contains("=")) {
        $idx = $line.IndexOf("=")
        $key = $line.Substring(0, $idx).Trim()
        $val = $line.Substring($idx + 1).Trim().Trim('"').Trim("'")
        $envVars[$key] = $val
    }
}

$templateFile = Join-Path $ProjectDir "infra\n8n\credentials.json.template"
if (-not (Test-Path $templateFile)) {
    Write-Error "Template file not found at $templateFile"
    exit 1
}

$templateContent = Get-Content $templateFile -Raw

$csDbName = if ($envVars.ContainsKey('CS_DB_NAME') -and $envVars['CS_DB_NAME']) { $envVars['CS_DB_NAME'] } else { 'customerservice' }
$csDbUser = if ($envVars.ContainsKey('CS_DB_USER') -and $envVars['CS_DB_USER']) { $envVars['CS_DB_USER'] } else { 'cs_app_user' }
$csDbPass = if ($envVars.ContainsKey('CS_DB_PASSWORD')) { $envVars['CS_DB_PASSWORD'] } else { '' }
$redisPass = if ($envVars.ContainsKey('REDIS_PASSWORD')) { $envVars['REDIS_PASSWORD'] } else { '' }

# Substitute environment variables
$resolvedContent = $templateContent `
    -replace '\$\{CS_DB_NAME\}', $csDbName `
    -replace '\$\{CS_DB_USER\}', $csDbUser `
    -replace '\$\{CS_DB_PASSWORD\}', $csDbPass `
    -replace '\$\{REDIS_PASSWORD\}', $redisPass

$tempFile = Join-Path $ProjectDir "scratch\temp_creds.json"
$scratchDir = Join-Path $ProjectDir "scratch"
if (-not (Test-Path $scratchDir)) {
    New-Item -ItemType Directory -Path $scratchDir | Out-Null
}

try {
    $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllText($tempFile, $resolvedContent, $utf8NoBom)
    
    # Copy to container and import
    docker cp $tempFile cs-n8n:/tmp/credentials.json
    $importOut = docker exec cs-n8n n8n import:credentials --input=/tmp/credentials.json 2>&1
    Write-Host "[+] n8n Credential Import Result: $importOut" -ForegroundColor Green
    
    # Remove from container
    docker exec -u root cs-n8n rm -f /tmp/credentials.json
}
finally {
    if (Test-Path $tempFile) {
        Remove-Item $tempFile -Force -ErrorAction SilentlyContinue
    }
}

Write-Host "==================================================" -ForegroundColor Cyan
Write-Host " [OK] Credentials securely imported into n8n vault!" -ForegroundColor Green
Write-Host "==================================================" -ForegroundColor Cyan
