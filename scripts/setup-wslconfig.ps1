$content = @"
[wsl2]
memory=2200MB
processors=4
swap=0
localhostForwarding=true
"@

$targetPath = Join-Path $env:USERPROFILE ".wslconfig"
[System.IO.File]::WriteAllText($targetPath, $content)
Write-Host "[OK] Written .wslconfig to $targetPath"
Get-Content $targetPath
