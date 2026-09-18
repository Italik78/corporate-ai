# DOCKER

Existing images/services are preserved after the latest update. Containers are currently stopped.

Important existing images: nvcr.io/nvidia/vllm:26.03-py3; vllm/vllm-openai; office-tools:1.0.0; qdrant/qdrant:latest; ghcr.io/open-webui/open-webui:v0.11.3; python:3.11-slim; caddy:2-alpine.

Existing Docker network: ai-net.

Do not use floating latest tags for new production definitions without documenting the resolved version.