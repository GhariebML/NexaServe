$pipes = [System.IO.Directory]::GetFiles("\\.\pipe\")
foreach ($p in $pipes) {
    if ($p -match "docker") {
        Write-Host $p
    }
}
