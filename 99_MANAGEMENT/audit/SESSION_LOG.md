# SESSION LOG

## 2026-10-09 — Сесия 1: ARCH_MAP (без промени в кода)
- Прочетени: DECISIONS/PROJECT_MASTER/RISKS/TASK_STATUS/CHECKPOINT (избрани секции), заглавия на REQUIREMENTS/ROADMAP/CURRENT_STATUS/REPOSITORY_CONTRACT/INGESTION_SERVICE/CONTEXT_MGMT; код: entrypoints, brain/orchestrator, KE qdrant филтри, ingestion routes.
- ARCH_MAP.md (134 реда): runtime+compose източници, flows, Brain, RAG, Web, Context, Ingestion, Structured Query, тестове, docs↔code разлики.
- Ключови находки: `-test` knowledge-engine и embedding са production зависимости; gateway→orchestrator и open-webui→gateway работят; `parse_structured_query` не е вързан никъде (+ префиксен bug «От файла»); WebUI filter не е инсталиран, мъртъв `office-tools` connection; user identity не се предава gateway→orchestrator; няма conversation persistence; DECISIONS #60-67 дублирани.
- Не са пускани тестове (само collect: orchestrator 80 ok; останалите без deps в системния python).
- Следваща стъпка: Сесия 2 (audit по SESSION_PROMPTS.md) — започни с identity/ACL и structured-query интеграцията.

## 2026-10-09 — Сесия 2: Core flow audit (без промени в кода)
- 3 Explore агента (sonnet): A core flow/Brain/budgets, B RAG/evidence/verification/ACL, C ingestion/structured query → `agent_A/B/C.md`.
- Тестове в ефимерни контейнери от service image (`docker run --rm -v services/X:/src:ro … pip --target /tmp/pt`): ORC 80 ✔, KE 14 ✔, ING 63 ✔ / 2 ✗ (poller тест извън mount-а).
- Реални заявки към /v1/orchestrate и gateway; дефектът CORPORATE_RETRIEVAL vs STRUCTURED_QUERY е възпроизведен (грешен GROUNDED за „Прекратен“).
- Лично проверени: F-01 unauth ingest (`ING/main.py:61,100,352-372`, curl 200), F-02 answer при NO_ANSWER (`ORC/main.py:106`), F-04 BudgetExceeded→500 (реална заявка), F-07 409 преди ACL, F-31 image без parser.
- AUDIT_FINDINGS.md: F-01..F-32 (3×P0, 12×P1). BACKLOG.md още не е попълнен.
- Следваща стъпка: попълни BACKLOG от F-ID-тата; първи P0 пакет = F-01 (ING auth) + F-02 (answer gating); F-03 identity — нужно е архитектурно решение (DECISIONS).
