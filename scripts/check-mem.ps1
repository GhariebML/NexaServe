$os = Get-CimInstance Win32_OperatingSystem
$totalRAM = [math]::Round($os.TotalVisibleMemorySize / 1MB, 2)
$freeRAM = [math]::Round($os.FreePhysicalMemory / 1MB, 2)
$totalPage = [math]::Round($os.TotalVirtualMemorySize / 1MB, 2)
$freePage = [math]::Round($os.FreeVirtualMemory / 1MB, 2)

Write-Host "Total RAM: $totalRAM GB"
Write-Host "Free RAM:  $freeRAM GB"
Write-Host "Total Virtual (Commit Limit): $totalPage GB"
Write-Host "Free Virtual (Commit Available): $freePage GB"

Get-PSDrive C, E | ForEach-Object {
    $freeGB = [math]::Round($_.Free / 1GB, 2)
    Write-Host "Drive $($_.Name): Free Space = $freeGB GB"
}

Write-Host "`nTop Memory Consumers:"
Get-Process | Sort-Object WorkingSet64 -Descending | Select-Object -First 10 -Property Name, Id, @{Name="WorkingSet_MB"; Expression={[math]::Round($_.WorkingSet64 / 1MB, 1)}}, @{Name="VM_MB"; Expression={[math]::Round($_.VirtualMemorySize64 / 1MB, 1)}} | Format-Table -AutoSize
