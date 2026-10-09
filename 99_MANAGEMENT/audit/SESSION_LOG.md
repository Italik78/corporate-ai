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

## 2026-10-09 — Сесия 3: Context, Security/Web, Tests/Deploy/Docs + backlog (без промени в кода)
- 3 `auditor` агента (sonnet): D Context (`agent_D.md`), E Security/Web (`agent_E.md`), F Tests/Deploy/Docs (`agent_F.md`, ID с префикс G-xx). Тестове не са пускани повторно (само диагностика на poller теста в ефимерен контейнер).
- Лично проверени: D-01 (`context.py:8-25`, `orchestrator.py:198-221`; понижен до P1 — засяга само GENERAL_RESPONSE), E-01 (Qdrant :6333 → 200 без ключ от ORC контейнера, user 0:0), G-05 (`caddy/` в `.gitignore:16`, `git ls-files caddy` = 0; корекция на ARCH_MAP).
- AUDIT_FINDINGS.md: +F-33…F-62 (1×P0 F-33, 11×P1, 12×P2, 7×P3; E-02/D-07→F-03, E-07→F-29, E-15→F-27). AUDIT_REPORT.md (10 секции). BACKLOG.md: WP-01…WP-19 + решения O-1…O-12.
- Блокирани: WP-03 (O-6), WP-04 (O-1), WP-12 (O-1,O-2,O-3), WP-13 (O-2), WP-14 (O-6), WP-15 (O-7), WP-16 (O-5,O-10); частично WP-08 (O-8), WP-17 (O-4,O-12).
- Следваща стъпка: WP-01 (ING auth + ACL ред), после WP-02. Собственикът решава O-1 и O-6 (P0 пакетите WP-03/WP-04), иначе P2/P3 не стартират.
