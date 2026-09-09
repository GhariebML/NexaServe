$ollamaPath = "C:\Users\LAPTOPS HOUSE\.ollama"
if (Test-Path $ollamaPath) {
    $size = (Get-ChildItem -Path $ollamaPath -Recurse -File -Force | Measure-Object -Property Length -Sum).Sum
    Write-Host "Host .ollama size: $([math]::round($size / 1GB, 2)) GB"
    Get-ChildItem -Path "$ollamaPath\models\manifests\registry.ollama.ai\library" -Recurse -File | Select-Object FullName
} else {
    Write-Host "No host .ollama directory found"
}

$recycleBin = 'C:\$Recycle.Bin'
if (Test-Path $recycleBin) {
    $size = (Get-ChildItem -Path $recycleBin -Recurse -File -Force -ErrorAction SilentlyContinue | Measure-Object -Property Length -Sum).Sum
    Write-Host "Recycle bin size: $([math]::round($size / 1GB, 2)) GB"
}
