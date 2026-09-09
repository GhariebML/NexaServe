# ==============================================================================
# NexaServe - n8n Admin Credential & Password Management Utility
# ==============================================================================

[CmdletBinding()]
param (
    [string]$Email = "moghariebai@gmail.com",
    [string]$NewPassword = "NexaServe2026!"
)

$ErrorActionPreference = "Stop"

Write-Host "==================================================" -ForegroundColor Cyan
Write-Host " NexaServe: Updating n8n Administrator Password" -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan

# 1. Generate standard bcrypt hash ($2a$ format)
$hash = python -c "import bcrypt; print(bcrypt.hashpw(b'$NewPassword', bcrypt.gensalt(10, prefix=b'2a')).decode())"
if (-not $hash) {
    Write-Error "Failed to generate bcrypt hash using local python runtime."
    exit 1
}

# 2. Update user table in n8n database
$sql = "UPDATE ""user"" SET password = '$hash' WHERE email = '$Email'; SELECT email, ""firstName"", ""lastName"", ""roleSlug"" FROM ""user"" WHERE email = '$Email';"
$tmpFile = "E:\NexaServe\infra\postgres\temp-reset.sql"
Set-Content -Path $tmpFile -Value $sql -Encoding UTF8

docker cp $tmpFile cs-postgres:/tmp/temp-reset.sql
$res = docker exec cs-postgres psql -U postgres -d n8n -f /tmp/temp-reset.sql
Remove-Item -Path $tmpFile -Force -ErrorAction SilentlyContinue

Write-Host "`n[+] Updated User Record:" -ForegroundColor Green
Write-Host $res

Write-Host "`n==================================================" -ForegroundColor Cyan
Write-Host " [OK] Credentials successfully updated!" -ForegroundColor Green
Write-Host " Login URL: http://localhost:5678" -ForegroundColor Green
Write-Host " Email:     $Email" -ForegroundColor White
Write-Host " Password:  $NewPassword" -ForegroundColor White
Write-Host "==================================================" -ForegroundColor Cyan
