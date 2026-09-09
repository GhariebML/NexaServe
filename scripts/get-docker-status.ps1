$procs = Get-Process | Where-Object { $_.ProcessName -match "docker" }
if ($procs) {
    Write-Host "Found Docker processes:"
    $procs | Format-Table Id, ProcessName, Path
} else {
    Write-Host "No docker processes running."
}

Write-Host "Checking WSL distros:"
wsl -l -v
