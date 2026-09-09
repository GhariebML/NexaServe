Write-Host "Stopping host Ollama to safely migrate model data to Drive E:..."
Get-Process -Name "ollama*", "ollama app*" -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 2

$src = "C:\Users\LAPTOPS HOUSE\.ollama"
$destDir = "E:\HostData"
$dest = "E:\HostData\.ollama"

if (-not (Test-Path $destDir)) {
    New-Item -ItemType Directory -Path $destDir -Force | Out-Null
}

if (Test-Path $src) {
    # Verify if src is already a junction or reparse point
    $item = Get-Item $src -Force
    if ($item.Attributes -band [System.IO.FileAttributes]::ReparsePoint) {
        Write-Host "Already a junction/symlink. Target: $($item.Target)"
    } else {
        Write-Host "Moving $src to $dest (preserving all existing model weights)..."
        Move-Item -Path $src -Destination $dest -Force
        Write-Host "Creating NTFS junction from $src -> $dest..."
        $cmdOutput = cmd /c "mklink /J `"$src`" `"$dest`""
        Write-Host $cmdOutput
    }
}

Write-Host "Checking Drive Space after migration:"
$c = Get-PSDrive C
Write-Host "C Free: $([math]::round($c.Free / 1GB, 2)) GB ($([math]::round($c.Free / 1MB, 2)) MB)"
Write-Host "E Free: $([math]::round((Get-PSDrive E).Free / 1GB, 2)) GB"
