# AUDIT REPORT — Corporate AI

Дата 2026-10-09 · HEAD `05210ac` (код = `3e70c5d` + audit docs) · branch `feature/corporate-ai-gateway-v0.1`.
Източници: `ARCH_MAP.md`, `AUDIT_FINDINGS.md` (F-01…F-62), `agent_A…F.md`. Одитът е само за четене; в кода няма промени.
Метод на доказване: файл:ред, реални недеструктивни заявки, ефимерни тест контейнери. Автоматизирани тестове: ORC 80 ✔ · KE 14 ✔ · ING 63 ✔ / 2 ✗ (причина: F-58, не е дефект на poller-а) · GW и WebUI filter не са пускани в Сесия 2 (виж §7).

**Обобщение:** 4 × P0 (F-01 ING без auth, F-02 отговор при NO_ANSWER, F-03 няма identity, F-33 Qdrant без ключ), 23 × P1, останалото P2–P3. Системата е добре структурирана (Brain → валидатор → control plane → evidence → verification), но **не е production-ready**: потребителят не е идентифициран никъде, ACL е на ниво service principal, а control plane може да бъде заобиколен на две места (F-01, F-33).

## 1. Current architecture
Caddy (`ai.local`) → Open WebUI v0.11.4 → Gateway 0.3.3 (OpenAI-съвместим, маршрут хардкоднат `orchestrator`) → AI Orchestrator (Brain + Control Plane + capabilities) → Knowledge Engine (Qdrant, `Qwen3-Embedding-4B`) / Document Ingestion (PG, canonical storage, structured query) / web tools през Gateway (SearXNG). Модел `qwen36` (vLLM, untouchable). Всичко на една мрежа `ai-net`. Подробности: `ARCH_MAP.md`.
Две production зависимости са наречени `-test`: `knowledge-engine-0.3.1-test` и `embedding-test` (F-43).

## 2. Working (потвърдено)
- Service auth orchestrator (401 без/с грешен токен, `compare_digest`, fail-closed); Gateway→ORC токени съвпадат.
- Валидация на Brain решения (schema, task_type == детерминистичния, source policy не може да се вдигне от клиента, зависимости, budgets само надолу).
- Бюджети за web search/fetch/verification; клиентски `source_policy` се игнорира.
- SSRF защита на web_fetch: loopback/private/link-local/IPv6/десетични-hex IP/`file://` → 403; редиректи валидирани (3); 256 KB лимит върху декомпресирани байтове; content-type allow-list.
- KE Qdrant филтри: `lifecycle=CURRENT`, `access_scope`, classification, project; празни scopes → нищо (fail-closed).
- Conflict/INSUFFICIENT/semantic verification логика има тестове (ORC).
- Host портове само 127.0.0.1 (освен Caddy 80/443); приложните контейнери: `read_only` + `cap_drop ALL`.
- Няма кеш в GW; ORC stateless → днес няма cross-user leakage от context слоя.
- Open WebUI: signup изключен, secret key зададен; `git ls-files` без .env/ключове.

## 3. Partially implemented
- Structured query: ING endpoint и ORC capability работят, но парсерът не е вързан (F-05), `query` се игнорира (F-06), ACL ред (F-07), непознат sheet (F-21).
- Evidence/provenance: липсват retrieval_score/page/chunk_id/verification_state (F-13); conflict детекторът е мъртъв (F-12).
- Budgets: `max_context_chars`/verification не се прилагат навсякъде (F-09, F-18); `BudgetExceeded` → 500 (F-04).
- Conversation context: само последните 12 съобщения (F-09, F-17, F-35).
- Web: allow-list празен (F-46), trust boundary липсва (F-40).
- Poller: state е durable, но 4xx → retry цикъл (F-24).
- Ingestion: pipeline работи, но без auth (F-01) и с ограничена защита срещу злонамерени файлове (F-23).

## 4. Broken
- F-01 ING endpoints без auth. F-02 `answer` се публикува при NO_ANSWER. F-04 бюджет → HTTP 500. F-05 Brain избира CORPORATE_RETRIEVAL за ясен XLS филтър (дефектът е възпроизведен; грешен GROUNDED). F-11 477 от 2306 CURRENT chunk-а са достъпни (липсват `classification`/`canonical_source_verified`). F-15 празен отговор в WebUI. F-34 клиентски `system` turn се третира като политика. F-58 два ING теста падат при mount само на ING.

## 5. Missing
Идентичност на потребителя (F-03) · persistence/Context Manager/memory (F-35) · trace store (F-38) · IaC за qdrant/embedding/open-webui/caddy (F-42) · backup/restore (F-44) · CI/integration/E2E (F-50) · Open WebUI boundary filter в runtime (F-47) · hybrid retrieval (F-20) · request size limits (F-36) · мрежова сегментация (F-41).

## 6. Security risks
P0: F-01, F-03 (latent, ACL на service principal), F-33 (Qdrant отворен за всеки контейнер в ai-net). P1: F-14/F-40 (prompt injection от документи и web), F-34, F-39 (DNS rebinding), F-41 (плоска мрежа; vLLM и SearXNG без auth), F-37 (пълни payload-и в лога). P2: F-23, F-45, F-46, F-47, F-48, F-49, F-53 (частни ключове и некриптирани бекъпи, `.env` 664). Положително: няма секрети в git (освен F-27).

## 7. Test gaps
~207 теста, само unit. Няма CI, integration, E2E, root pytest (F-50). Изцяло липсват: prompt injection, Brain unavailable (`decide()` catch-all), web unavailable/timeout в ORC, stale-document, negative за poller, SSRF IPv6/rebinding (F-51). Дублирано име на тест маскира тест (F-30). Gateway и WebUI filter тестове не са пускани в тази фаза.

## 8. Runtime gaps
`embedding-test` `restart=no` и `:latest` (F-43); running ORC image ≠ HEAD (F-31); 5 контейнера без compose (F-42); няма healthchecks/ресурсни лимити (F-59); ~25 Exited контейнера (F-60); тестови данни в prod PG/Qdrant (F-28); WebUI филтър не е инсталиран, мъртъв connection към `office-tools` (F-47). Authorized `/v1/orchestrate` и E2E acceptance A–L не са изпълнени.

## 9. Documentation inconsistencies
DECISIONS #60–#67 дублирани (F-54); CHECKPOINT твърди, че кодът не е в GitHub (F-55); SERVICES/NETWORK/DATA_FLOW/STORAGE/RECOVERY/RISKS са stub-ове; PROJECT_MASTER/RISKS не споменават Brain; брой тестове 24/32/38/58/78 (F-61); Open WebUI boundary и C8 context са описани като дизайн, не като реалност; ARCH_MAP грешеше за Caddyfile (gitignored).

## 10. Exact implementation backlog
Виж `BACKLOG.md` (работни пакети WP-01…WP-19, зависимости и секция „Решения на собственика“ O-1…O-12).
