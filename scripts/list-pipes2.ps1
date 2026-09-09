Get-ChildItem -Path "\\.\pipe\" -ErrorAction SilentlyContinue | Where-Object { $_.Name -match "docker" } | Select-Object Name
