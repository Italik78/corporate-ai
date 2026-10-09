# ARCH MAP

Snapshot 2026-10-09, HEAD `b56f84a` (= origin). Само четене; без промени в кода. Редове са `файл:ред` към този HEAD.
Пътищата `services/…` са съкратени: **GW**=`services/corporate-ai-gateway/app`, **ORC**=`services/ai-orchestrator/app`, **KE**=`services/knowledge-engine/app`, **ING**=`services/document-ingestion/app`.

## 1. Runtime и откъде се стартира

Compose project `compose`, working_dir `deploy/compose` (`docker inspect` labels). Няма compose в корена → `docker compose ps` не се ползва; ползвай `docker ps` или `-f deploy/compose/<f>.yaml`.

| Container | Image/build | Compose източник | Host порт | Бележка |
|---|---|---|---|---|
| corporate-ai-gateway-0.3.3 | build services/corporate-ai-gateway | `corporate-ai-gateway.yaml` | 127.0.0.1:8096→8080 | alias `corporate-ai-gateway` |
| corporate-ai-orchestrator-0.1.0 | build services/ai-orchestrator | `ai-orchestrator.yaml` | — (8097) | read_only, cap_drop ALL |
| corporate-ai-knowledge-engine-0.3.1-test | build services/knowledge-engine | `knowledge-engine.yaml` | 127.0.0.1:8093→8090 | **production** (виж по-долу) |
| corporate-ai-document-ingestion | build services/document-ingestion | `document-ingestion.yaml` | 127.0.0.1:8095 | томове: repository, staging |
| corporate-ai-nextcloud-poller | build services/nextcloud-poller | `document-ingestion.yaml` | — | state vol `compose_corporate_ai_nextcloud_poller_state` |
| corporate-ai-postgres | postgres:16.15-alpine | `document-ingestion.yaml` | — | metadata/versions |
| corporate-ai-searxng | searxng/searxng:**latest** | `web-search.yaml` | — | конфиг `deploy/config/searxng` |
| corporate-ai-qdrant | qdrant:v1.15.5 | **няма в repo** (docker run) | — | bind `data/qdrant` |
| corporate-ai-qwen36 | vllm-openai@sha256:61fc8a… | **няма в repo** | — | `:8000`, untouchable (memory) |
| corporate-ai-embedding-test | vllm-openai:**latest** | **няма в repo**, restart=no | — | Qwen3-Embedding-4B, `:8001` |
| open-webui | open-webui:v0.11.4 | **няма в repo** | 127.0.0.1:8080 | vol `open-webui` |
| caddy | caddy:2-alpine | **няма в repo** (само `caddy/Caddyfile`) | 0.0.0.0:80/443 | `ai.local`→open-webui:8080 |

Всички на мрежа `ai-net` (external). Проект-label на KE и gateway изброява и 4-те yaml-а (пускани заедно с `-f`); orchestrator/ingestion — само своя.

**Изясняване `-test` суфикс:** `knowledge-engine-0.3.1-test` е **production зависимост** — hard-coded в `ai-orchestrator.yaml` (KNOWLEDGE_ENGINE_URL), `corporate-ai-gateway.yaml:8`, `document-ingestion.yaml:31`. `embedding-test` е **production зависимост** — `knowledge-engine.yaml` EMBEDDING_BASE_URL=`…embedding-test:8001`; без него няма embed на заявки/ingest. Рискове: restart=no (няма авто-старт), `:latest` образ, няма compose/запис в repo (виж §10).

Health (2026-10-09): gateway/KE/ingestion/open-webui 200; orchestrator `/health` 200; orchestrator→qwen36, gateway→qwen36, orchestrator→searxng, KE→qdrant 200.
**Проверени връзки (преди непроверени):**
- gateway→orchestrator: `ORCHESTRATOR_URL=…orchestrator-0.1.0:8097` (env), `GET /health` 200 от gateway контейнера; без auth `POST /v1/orchestrate` → 401 `SERVICE_AUTH_REQUIRED`; SHA256 на `ORCHESTRATOR_SERVICE_TOKEN` (gw) == `ORCHESTRATOR_GATEWAY_SERVICE_TOKEN` (orc). Authorized `/v1/orchestrate` НЕ е пуснат (би извикал Qwen).
- open-webui→gateway: OpenAI connection #2 в WebUI DB (`config` key `openai.api_base_urls`) = `http://corporate-ai-gateway:8080/v1`, ключ зададен; от open-webui `GET /health` и `/v1/models` (→ модел `corporate-ai`) 200. Tool server: `http://corporate-ai-gateway-0.3.3:8080`.
- **Мъртва конфигурация:** connection #1 `http://office-tools:8091/v1` — контейнерът `office-tools` е Exited (3 седмици), DNS не се разрешава; модел `qwen36-office` неактивен.
- **Filter `corporate_knowledge_boundary` НЕ е инсталиран** в Open WebUI (таблица `function` = 0 реда), въпреки че е в `integrations/open-webui/filters/`. WebUI има 1 knowledge колекция и 67 файла (потенциални независими `file-*` — DECISIONS #21). `rag.embedding_engine=openai`, `qwen3-embedding-4b`.

## 2. Repo структура и entrypoints

| Път | Роля | Entrypoint |
|---|---|---|
| `services/corporate-ai-gateway` | OpenAI-съвместим gateway + web tools + document proxy | `uvicorn app.main:app :8080` — `GW/main.py` (1596 реда) |
| `services/ai-orchestrator` | Brain + Control Plane + capabilities | `uvicorn app.main:app :8097` — `ORC/main.py` (118) |
| `services/knowledge-engine` | embed + Qdrant search + RAG answer + evidence | `:8090` — `KE/main.py` (516) |
| `services/document-ingestion` | ingest pipeline, PG metadata, canonical storage, structured query | `:8095` — `ING/main.py` (461) |
| `services/nextcloud-poller` | ETag poller → ingestion | `app.py` (294), `asyncio.sleep` цикъл `:290` |
| `integrations/open-webui` | Filter `corporate_knowledge_boundary.py` + config + тест | не е активиран (виж §1) |
| `deploy/{compose,config,paperless,profiles}` | compose yaml, searxng конфиг, Paperless стек | — |
| `caddy/`, `config/`, `runtime/`, `secrets/`, `data/`, `backups/`, `lab/` | локално/gitignored runtime | — |
| `00_…08_*`, `99_MANAGEMENT` | документация; повечето `0[2-3,5-7]_*` са 4–10-редови stub-ове | — |

## 3. Request flow: Open WebUI → LLM

1. Browser → Caddy `ai.local` (TLS) → `open-webui:8080` (`caddy/Caddyfile`).
2. Open WebUI → `POST gateway/v1/chat/completions` (`GW/main.py:1450`), auth Bearer `GATEWAY_API_KEY` (`authorize_tool_request` `GW:1149`). Модел `corporate-ai` (`GW:1372`).
3. `chat_completions`: взима последното user съобщение; **маршрутът е хардкоднат** `route="orchestrator"` (`GW:1479`); клиентските `tools` не дават права (коментар `:1476`). Клон `route == "general"` (`GW:1482+`) е недостижим.
4. `run_orchestrator` (`GW:130`) → `POST orchestrator:8097/v1/orchestrate` `{user_request, messages}` с service token. **Не се предава user/conversation identity** (само текст и messages).
5. `ORC/main.py:61 orchestrate`: `configured_source_policy()` (env `CORPORATE_AI_SOURCE_POLICY`, сега `INTERNAL_FIRST_WEB_FALLBACK`; `source_policy.py`) → `clamp_budget` → `brain.decide()` → `build_task` (`task.py:137`) → `Orchestrator.create_plan` (`orchestrator.py:161`, `planner.py`) → `execute_plan` (`orchestrator.py:243`) → `determine_answer_status` (`main.py:25`) → `OrchestrationResponse`.
6. Gateway връща OpenAI-формат отговор + метаданни (`GW:1522-1557`: answer_status, evidence_status, trace_id = task_id, verification, provenance).
7. Qwen се вика от: orchestrator (`llm_reasoning.py`, `brain.py`, `synthesis.py`, `semantic_verification.py`), KE (`KE/llm.py`, `/v1/query`), gateway (`qwen_chat` `GW:221` — остатъчен general път), ingestion (`vision.py`).

## 4. Brain / Deterministic Control Plane (ORC)

- Модели: `models.py` — `BrainDecision`/`BrainPlanStep`/`TaskType`/`TaskState`/`Budget`/`CapabilityType` (вкл. `STRUCTURED_QUERY`).
- `brain.py:54 validate_decision` (JSON→Pydantic, `BrainDecisionRejected`); проверки: task_type == детерминистичния `classify_task` (`:118`), source class не се изпуска (`:122`), позволени планове по тип (`:146`), web зависи от corporate (`:150`), structured: точно `source_file` XOR `document_id/version` (`:100-104`).
- `brain.py:154 deterministic_decision` = safe fallback; `brain.py:171 decide` вика Qwen; режими на връщане: `brain` | `brain_unavailable` (`:214`) | `deterministic_fallback` (`:218`, всякакво `Exception`).
- `registry.py`/`capabilities.py`: `CapabilityRegistry`; capability-та: corporate retrieval (`corporate_retrieval.py`→KE `/v1/search`), `web_search.py`, `web_fetch.py`, `structured_query.py`.
- `budgets.py`: `clamp_budget`, `BudgetController` (steps, capability_calls, retrieval_rounds, web_searches, web_fetches, verification_rounds, context_chars) — съвпада с §18 на rules.
- Task classification: `task.py` `classify_task` (ключови думи `_CORPORATE_TERMS`, `_STRUCTURED_CORPORATE_TERMS` `:30`, `:85-88` → `CORPORATE_KNOWLEDGE`/`CORPORATE_AND_WEB`/`WEB_RESEARCH`/`GENERAL`).
- Auth към orchestrator: `auth.py` Bearer `ORCHESTRATOR_GATEWAY_SERVICE_TOKEN`, `hmac.compare_digest`, fail-closed 503 при липсващ токен.
- Policy режими: INTERNAL_ONLY / INTERNAL_FIRST_WEB_FALLBACK / EXPLICIT_WEB / RESTRICTED_OFFLINE — **сървърен env, не по заявка** (`source_policy.py`).

## 5. RAG flow (Corporate)

`orchestrate` → `CorporateRetrievalCapability.execute` (`corporate_retrieval.py:33`) → `POST KE /v1/search` (`:54`, токен `KNOWLEDGE_ENGINE_SERVICE_TOKEN`) → KE `main.py:223 search`: `embedding.embed` → `qdrant.search` (`KE/qdrant.py:112`). Филтри в Qdrant: `lifecycle_status=CURRENT` (`:130`), `access_scope ∈ principal.access_scopes` (`:134`), classification, project_id; празни scopes → нищо (fail-closed `:126`).
Оттам: `retrieval_strategy.py`, `retrieval_refinement.py` (до `max_retrieval_rounds`) → `applicability.py` → `evidence.py`/`evidence_evaluation.py` (SUPPORTED/CONFLICT/INSUFFICIENT) → `conflict.py` → `synthesis.py` (Qwen) → `verification.py` + `semantic_verification.py` (574 реда) → answer_status (`main.py:25`).
KE има и собствен `POST /v1/query` (`KE/main.py:282`, `rag.py`, `claims.py`, `evidence.py`) и gateway tool `knowledge_search` (`GW:923`) → пак през orchestrator (`GW:903`).
**ACL е на ниво service principal** (`KNOWLEDGE_ENGINE_SERVICE_CREDENTIALS` → access_scopes на orchestrator-токена), не на краен потребител — понеже identity не се предава (§3.4).

## 6. Web flow

Orchestrator: `web_search.py` (→ **gateway** `/v1/tools/web_search`, `GATEWAY_URL`; official-domain allowlist `:19`, env `CORPORATE_AI_OFFICIAL_DOMAIN_MAP`), `web_research.py` (Qwen избира кои URL да се fetch-нат), `web_fetch.py` (→ gateway `/v1/tools/web_fetch`).
Gateway: `web_search` `GW:703` (`_execute_web_search :621` → SearXNG `corporate-ai-searxng:8080`), `web_fetch` `GW:894` (`_execute_web_fetch :753`; `_web_fetch_url_allowed :522` SSRF/URL проверки, `_web_domain_allowed :502`, `_sanitize_web_content :741`, `_web_evidence :578`). Auth: Bearer `GATEWAY_TOOL_API_KEY`/`GATEWAY_API_KEY`.
Web evidence е отделен provenance клас; fallback зависи от corporate retrieval (`brain.py:150`).

## 7. Context & Memory

**Реално:** `ORC/context.py:8 build_conversation_context` — последните 12 съобщения от заявката, без постоянство, без state/memory/milestones/token budget (само `max_context_chars` в `BudgetController`). `conversation_id` е опционален и не се ползва за storage (`models.py:114`, `task.py:152`). Gateway е stateless; историята идва от Open WebUI.
Дизайн (docs): PG история/state/memory, P0–P6 слоеве, 24–32K бюджет (`CONVERSATION_CONTEXT_MANAGEMENT.md`, DECISIONS #75-84). Roadmap C8.1–C8.4 — **не е имплементирано**.

## 8. Ingestion & Repository (ING)

`POST /v1/documents/ingest` (`ING/main.py:61`), `/process` (`:100`), Paperless webhook (`:140`), `GET …/versions` (`:352,357`), `…/{ingestion_id}/status` (`:365`), admin reconciliation/recovery (`:381-427`, токен `INGESTION_RECOVERY_TOKEN`). Auth: `ING/auth.py` service credentials (B64 env) с permissions и `access_scopes`.
Pipeline `pipeline.py` (728): security (`security.py`) → extract (`extractors.py` 666: TXT/MD/CSV/DOCX/XLSX/XLS/PPTX/PDF) → `vision.py` (скан. PDF, JSON mode) → normalize → `metadata.py` (600, PG) → dedup SHA-256 + scope → version/lifecycle (`repository.py`) → `chunker.py` → `knowledge_client.py` → KE `/v1/ingest` (`KE/main.py:91`) + `/v1/documents/lifecycle` (`:164`) → canonical storage (`storage.py`, vol `/data/repository`).
Poller: `nextcloud-poller/app.py` — ETag→`/v1/documents/ingest`; `STATE_FILE` default `/tmp/nextcloud-poller-state.json` (`:28`), в compose има volume `…poller_state`; durable ли е — **не е потвърдено** (`test_poller_state.py`, DECISIONS #54).
Paperless стек: `deploy/paperless/docker-compose.yml` (отделен, не пуснат в `docker ps`).
Credentials: PG `corporate_ai:corporate_ai` е hard-coded в `document-ingestion.yaml:35`.

## 9. Structured Query

- ING: `POST /v1/documents/structured-query` (`ING/main.py:188`, permission `structured_read`), `ING/structured_query.py` (186), `ING/document_reference.py` (92; `GET /v1/documents/resolve-by-source-file` `:310`). Фикстура `tests/fixtures/structured_query_fixture.xls`.
- ORC: `structured_query.py` (203; клиент → `DOCUMENT_INGESTION_URL`, default `http://corporate-ai-document-ingestion:8095`, токен `KNOWLEDGE_ENGINE_SERVICE_TOKEN`), `structured_query_parser.py` (110).
- **Известен дефект потвърден:** `parse_structured_query` (`structured_query_parser.py:35`) **не се импортира никъде** (`grep` по services/) — мъртъв код; в `decide()` няма детерминистично преди-Brain разклонение. Освен това regex `_FILE_RE` (`:8`) връща `source_file='От файла DfQueryToExcel (7.1).xls'` (с префикс «От файла») — друг дефект от докладвания «(7.1).xls». Roadmap D2.1.

## 10. Тестове

| Сервис | Тестове | Как се пускат | Състояние сега |
|---|---|---|---|
| ai-orchestrator | 17 файла, 80 collected | `cd services/ai-orchestrator && .venv/bin/python -m pytest -q -x --tb=short` | `.venv` (gitignored) работи |
| document-ingestion | 10 файла (`pytest.ini` pythonpath=.; `requirements-dev.txt`) | трябва venv с `requirements*.txt` | системният python: липсва `fitz` → collection error |
| knowledge-engine | 2 файла | същото | липсва `fastapi`/`httpx` |
| gateway | `tests/test_gateway.py` (1049 реда) | същото | липсва `fastapi` |
| open-webui filter | `integrations/open-webui/tests` (6) | `python3 -m pytest` | работи |

Няма CI (`.github` липсва), няма E2E/integration тестове в repo, няма root pytest конфиг. Негативни тестове (§13 rules) — да се одитират; няма тестове за identity propagation.

## 11. Ключови решения (DECISIONS.md)

KE е граница retrieval/evidence (#11); Qwen3-Embedding-4B 2560d, Qdrant (#9,10); Open WebUI без второ авторитетно хранилище/`file-*` (#20,21,23,34); Web = външен източник с отделен provenance, контролиран egress (#24-29); PG е authoritative за metadata, Qdrant е производен (#45,46,78); дедуп по SHA-256+scope (#44); Brain = структуриран Pydantic договор + детерминистичен Control Plane, fallback остава (#85-95); client не вдига собствени права, policy е сървърна (#89,90); structured query: детерминистичен парсер преди Brain, fail-closed при ambiguity (#60-67 от 2026-10-08).

## 12. Разлики docs ↔ code / runtime

1. **DECISIONS номерация:** #60–#67 се повтарят (`DECISIONS.md:82` vs `:132`) → препратки «#60/#61» са двусмислени.
2. **CHECKPOINT 2026-10-08 е остарял:** твърди, че `structured_query_parser.py`/`brain.py` промените не са в GitHub; в `HEAD` (=origin) са (`3e70c5d`). Реално липсва само интеграцията на парсера.
3. `SERVICES.md` е 3 реда («Authoritative list of runtime services on» — недовършено); `NETWORK.md`/`DATA_FLOW.md`/`RAG.md`/`VECTOR_DB.md`/`INGESTION.md`/`SECURITY.md` са 4–8-редови stub-ове; `NETWORK.md` пише «historical ports».
4. **Брой тестове се разминава:** TASK_STATUS «24 passed» / PROJECT_MASTER «38» / CHECKPOINT «58 (без poller)»; orchestrator «78» срещу 80 collected.
5. Код (docs не са сверявани): маршрутът е хардкоднат `orchestrator` (`GW:1479`), `general` клонът е мъртъв, `heuristic_route`/`classify_route`/`rewrite_retrieval_query` (`GW:333-478`) вероятно неизползвани.
6. Docs (C3/#34, Open WebUI doc): boundary filter + Knowledge само през Corporate AI; runtime: filter не е инсталиран, 67 WebUI файла, мъртъв `office-tools` connection.
7. Docs: Conversation/Context persistent (DECISIONS #75-84); код: без persistence (§7).
8. Docs «Brain никога не заобикаля control plane» — вярно за validate_decision; но `decide()` прихваща всякакво `Exception` → `deterministic_fallback` без лог/trace причина (`brain.py:217`).
9. Observability: `trace_id == task_id`, няма трасиране на Brain решения/budget_usage в отговора (само `brain_decision`, `plan`); `print("CHAT_DIAGNOSTIC …")` в GW (`:1465`) логва tool names/ids с `%r` форматиране, което не се интерполира (print, не logger).
10. Image tags: `searxng:latest`, `embedding-test` `vllm:latest` (RISKS «version drift»); `qwen36`, qdrant, open-webui, caddy без compose в repo → «GitHub е source of truth» не важи за тях.
11. Корен `README.md` и `BUILD_PROMPTS/` не са сверявани; `caddy.backup-2026-09-20`, `open-webui*.backup*` са в working tree (gitignore статус не проверен).

## 13. Следващи стъпки (за audit сесиите)
Приоритетно за проверка: identity/ACL propagation (§3.4/§5), парсер интеграция (§9), инсталиране/липса на WebUI filter (§1), prompt-injection изолация на web/doc съдържание, durable poller state, секрети в compose (PG парола, `.env` в `deploy/compose/`), мрежова експозиция на портове (127.0.0.1 ок; caddy 0.0.0.0).
