# Ubuntu 24.04

Supported target is Ubuntu 24.04 LTS x86_64. Verify with `cat /etc/os-release`, `uname -m`, `lscpu`, `free -h`, `df -h /`, and `timedatectl status`. The preflight script checks distro, architecture, resources, DNS, open listeners, Docker and NVIDIA driver.

Host package and Docker repository installation scripts are online operations. In restricted networks, use only the Ministry-maintained signed apt mirror and approved package versions. Coordinate kernel/driver updates and reboot windows with IT. Do not install a Windows runtime or Docker Desktop.
