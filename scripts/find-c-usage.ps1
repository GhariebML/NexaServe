$dirs = Get-ChildItem -Path "C:\" -Directory -Force -ErrorAction SilentlyContinue
foreach ($d in $dirs) {
    try {
        $size = (Get-ChildItem -Path $d.FullName -Recurse -File -Force -ErrorAction SilentlyContinue | Measure-Object -Property Length -Sum).Sum
        if ($size -gt 1GB) {
            Write-Host "$($d.FullName): $([math]::round($size / 1GB, 2)) GB"
        }
    } catch {
        # ignore access denied
    }
}

$userDirs = Get-ChildItem -Path "C:\Users\LAPTOPS HOUSE" -Directory -Force -ErrorAction SilentlyContinue
foreach ($d in $userDirs) {
    try {
        $size = (Get-ChildItem -Path $d.FullName -Recurse -File -Force -ErrorAction SilentlyContinue | Measure-Object -Property Length -Sum).Sum
        if ($size -gt 1GB) {
            Write-Host "$($d.FullName): $([math]::round($size / 1GB, 2)) GB"
        }
    } catch {
        # ignore
    }
}
