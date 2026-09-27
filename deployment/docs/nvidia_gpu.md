# NVIDIA GPU

Install a supported Ubuntu-packaged NVIDIA driver, reboot, and confirm `nvidia-smi` reports model, VRAM and driver. Then run `scripts/03_install_nvidia_toolkit.sh` and `scripts/verify_gpu.sh`; the latter checks both host and Docker GPU access. Compose GPU overlay assigns devices only to Ollama.

The toolkit script follows NVIDIA's [official installation guide](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html); use an approved signed mirror and record installed package versions.

After model load, watch `nvidia-smi` during actual generation. Ollama tag/list health is not evidence of GPU use. VRAM fit depends on model quantization, context and parallel load. On OOM, stop acceptance and measure resource usage; do not silently fall back to CPU or switch models without comparative testing.
