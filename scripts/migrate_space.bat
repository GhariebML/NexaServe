@echo off
echo [*] Moving System Backup(1) to E:\HostData...
robocopy "C:\System Backup(1)" "E:\HostData\System Backup(1)" /MOVE /E /R:1 /W:1
mklink /J "C:\System Backup(1)" "E:\HostData\System Backup(1)"

echo [*] Moving SWSetup to E:\HostData...
robocopy "C:\SWSetup" "E:\HostData\SWSetup" /MOVE /E /R:1 /W:1
mklink /J "C:\SWSetup" "E:\HostData\SWSetup"

echo [*] Done. Current drive C space:
dir C:\ | findstr "bytes free"
