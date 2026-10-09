# ARCH MAP

## Runtime

Snapshot: 2026-10-09 (read-only, `docker ps` + health probes). Няма compose файл в корена; единственият е `deploy/paperless/docker-compose.yml`, така че `docker compose ps` не се ползва — контейнерите са пуснати отделно.

| Container | Status | Host port |
|---|---|---|
| corporate-ai-gateway-0.3.3 | Up 4d | 127.0.0.1:8096→8080 |
| corporate-ai-orchestrator-0.1.0 | Up 2d | — (8097 вътрешен) |
| corporate-ai-knowledge-engine-0.3.1-test | Up 4d | 127.0.0.1:8093→8090 |
| corporate-ai-document-ingestion | Up 2d | 127.0.0.1:8095 |
| corporate-ai-qwen36 | Up 9d | — |
| corporate-ai-embedding-test | Up 9d | — |
| corporate-ai-qdrant | Up 9d | — (6333) |
| corporate-ai-postgres | Up 9d (healthy) | — |
| corporate-ai-searxng | Up 8d | — |
| corporate-ai-nextcloud-poller | Up 8d | — |
| open-webui | Up 6d (healthy) | 127.0.0.1:8080 |
| caddy | Up 9d | 0.0.0.0:80/443 |

Health (HTTP): gateway 200 · knowledge-engine 200 · document-ingestion 200 · open-webui 200 · orchestrator /health 200 (in-container).
Connectivity (in-container): orchestrator→qwen36 /v1/models 200 · gateway→qwen36 200 · orchestrator→searxng 200 · knowledge-engine→qdrant /readyz 200.

Бележки: `-test` суфикс в имената на knowledge-engine и embedding (за проверка дали са production). Orchestrator няма host порт. Не е проверена свързаност gateway→orchestrator и open-webui→gateway.
