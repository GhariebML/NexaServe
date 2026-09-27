# ==============================================================================
# NexaServe - n8n Admin Credential & Password Management Utility
# ==============================================================================

[CmdletBinding()]
param (
    [string]$Email = "moghariebai@gmail.com",
    [Parameter(Mandatory=$false)]
    [string]$NewPassword = $env:N8N_ADMIN_PASSWORD
)

if ([string]::IsNullOrWhiteSpace($NewPassword)) {
    $secPass = Read-Host -Prompt "Enter new n8n administrator password" -AsSecureString
    $bstr = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($secPass)
    $NewPassword = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto($bstr)
}

$ErrorActionPreference = "Stop"

Write-Host "==================================================" -ForegroundColor Cyan
Write-Host " NexaServe: Updating n8n Administrator Password" -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan

# 1. Generate standard bcrypt hash ($2a$ format)
$hash = python -c "import bcrypt, sys; print(bcrypt.hashpw(sys.argv[1].encode(), bcrypt.gensalt(10, prefix=b'2a')).decode())" $NewPassword
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
Write-Host " Password:  [REDACTED / SECURELY SET]" -ForegroundColor White
Write-Host "==================================================" -ForegroundColor Cyan
