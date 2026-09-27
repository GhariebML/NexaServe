#!/usr/bin/env bash
set -Eeuo pipefail
command -v nvidia-smi >/dev/null || { echo 'Install a supported NVIDIA driver first (Ubuntu Additional Drivers/ubuntu-drivers); reboot and verify nvidia-smi.' >&2; exit 1; }
sudo apt-get update
sudo apt-get install -y ca-certificates curl gnupg2
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor --yes -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
curl -fsSL https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list >/dev/null
sudo apt-get update
sudo apt-get install -y nvidia-container-toolkit
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker
echo 'Toolkit installed; verify with scripts/verify_gpu.sh.'
