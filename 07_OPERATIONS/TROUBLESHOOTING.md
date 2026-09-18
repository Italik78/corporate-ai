# TROUBLESHOOTING

First collect: uname -r; cat /etc/os-release; nvidia-smi; docker --version; nvidia-ctk --version; docker ps -a; docker network ls; docker volume ls; df -h; free -h.

GPU validation: docker run --rm --runtime=nvidia nvidia/cuda:13.0.2-base-ubuntu24.04 nvidia-smi.