$c = Get-PSDrive C
Write-Host "C Free: $([math]::round($c.Free / 1MB, 2)) MB ($([math]::round($c.Free / 1GB, 2)) GB)"
Write-Host "D Free: $([math]::round((Get-PSDrive D).Free / 1GB, 2)) GB"
Write-Host "E Free: $([math]::round((Get-PSDrive E).Free / 1GB, 2)) GB"

$dockerVhdx = "C:\Users\LAPTOPS HOUSE\AppData\Local\Docker\wsl\disk\docker_data.vhdx"
if (Test-Path $dockerVhdx) {
    $f = Get-Item $dockerVhdx
    Write-Host "docker_data.vhdx size: $([math]::round($f.Length / 1GB, 2)) GB"
}

$userTemp = "C:\Users\LAPTOPS HOUSE\AppData\Local\Temp"
$userTempSize = (Get-ChildItem -Path $userTemp -Recurse -File -Force -ErrorAction SilentlyContinue | Measure-Object -Property Length -Sum).Sum
Write-Host "User Temp size: $([math]::round($userTempSize / 1GB, 2)) GB ($([math]::round($userTempSize / 1MB, 2)) MB)"

$winTemp = "C:\Windows\Temp"
$winTempSize = (Get-ChildItem -Path $winTemp -Recurse -File -Force -ErrorAction SilentlyContinue | Measure-Object -Property Length -Sum).Sum
Write-Host "Windows Temp size: $([math]::round($winTempSize / 1GB, 2)) GB ($([math]::round($winTempSize / 1MB, 2)) MB)"
