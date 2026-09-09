$exe = "C:\Users\LAPTOPS HOUSE\AppData\Local\Programs\DockerDesktop\Docker Desktop.exe"
Write-Host "Launching Docker Desktop via Win32_Process::Create..."
$proc = Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{CommandLine = "`"$exe`""}
Write-Host "Return value: $($proc.ReturnValue), ProcessId: $($proc.ProcessId)"

Write-Host "Waiting 25 seconds for Docker engine and named pipe to initialize..."
Start-Sleep -Seconds 25

$procs = Get-Process | Where-Object { $_.ProcessName -match "docker" }
$procs | Format-Table Id, ProcessName

Write-Host "Testing docker version..."
docker version
