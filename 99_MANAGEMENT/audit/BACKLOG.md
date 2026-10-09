# BACKLOG

Статус: `TODO` · `BLOCKED(O-x)` = чака решение на собственика (секция най-долу) · `DONE`.
Една сесия = един пакет (rules §1.6). Всеки пакет приключва с: тестове (засегнатите) → SESSION_LOG → commit → стоп.
Правило §2: **не започвай P2/P3, докато има отворен P0**. P0 пакетите WP-03 и WP-04 са блокирани от решения → собственикът трябва да реши O-1/O-6 или изрично да разреши P2/P3 да тръгнат преди тях.
Модел: Sonnet за имплементация; Opus за O-решения и WP-04/WP-12 (дизайн). Review: един агент на пакет; отделен security агент само за P0 (WP-01, WP-03, WP-04).

## Преглед

| Пакет | Prio | Findings | Статус | Зависи от |
|---|---|---|---|---|
| WP-01 ING auth + ACL ред | P0 | F-01, F-07, F-58 | TODO | — |
| WP-02 Answer gating + budget safety | P0 | F-02, F-04, F-15 | TODO | — |
| WP-03 Qdrant auth | P0 | F-33 | BLOCKED(O-6) | WP-01 |
| WP-04 User identity + ACL propagation | P0 | F-03 (+E-02, D-07) | BLOCKED(O-1) | WP-01, WP-02 |
| WP-05 Structured query routing | P1 | F-05, F-06, F-32, F-31, F-21 | TODO | WP-01 |
| WP-06 Brain robustness + context role hygiene | P1 | F-08, F-10, F-16, F-19, F-34 | TODO | WP-02 |
| WP-07 Prompt-injection boundary | P1 | F-14, F-40 | TODO | WP-06 |
| WP-08 Web fetch hardening | P1/P2 | F-39, F-45, F-46 | TODO (F-46 BLOCKED(O-8)) | — |
| WP-09 KE corpus + evidence + conflict | P1 | F-11, F-12, F-13 | TODO | WP-03 (за Qdrant запис) |
| WP-10 Gateway hygiene: limits, logs, dead code | P1 | F-36, F-37, F-29, F-49, F-57, F-62 | TODO | — |
| WP-11 Test infrastructure + negative tests | P2 | F-50, F-51, F-30, F-61 | TODO | WP-05, WP-06 |
| WP-12 Conversation persistence + Context Manager | P1 | F-35, F-09, F-17, F-18 | BLOCKED(O-1,O-2,O-3) | WP-04, WP-06 |
| WP-13 Trace store / observability | P1 | F-38, F-10 | BLOCKED(O-2) | WP-06 |
| WP-14 IaC + embedding restart + image pinning | P1 | F-42, F-43, F-52, F-59 | BLOCKED(O-6) | — |
| WP-15 Backup / restore | P1 | F-44, F-53 | BLOCKED(O-7) | WP-14 |
| WP-16 Network segmentation + container hardening | P1/P2 | F-41, F-47, F-48, F-56 | BLOCKED(O-5,O-10) | WP-03, WP-14 |
| WP-17 Ingestion robustness | P2 | F-22, F-23, F-24, F-25, F-26, F-28, F-60 | TODO (F-22 BLOCKED(O-4); F-28/F-60 BLOCKED(O-12)) | WP-01 |
| WP-18 Retrieval quality | P2 | F-20, F-27 | TODO | WP-09 |
| WP-19 Documentation sync (§16) | P2/P3 | F-54, F-55 (+ docs от всички пакети) | TODO — последен | всички |

Препоръчан ред: WP-01 → WP-02 → (WP-05, WP-06 паралелно като сесии след една) → WP-07 → WP-08 → WP-10 → WP-09 → WP-11 → … блокираните след решения → WP-19.

## P0

### WP-01 — ING auth + ACL ред (F-01, F-07, F-58)
- `Depends(service_auth)` + permission на `/v1/documents/ingest`, `/process`, `/versions`, `/status`, `/details` (`ING/main.py:61,100,352-372`); poller получава service credential.
- Structured query: ACL/lifecycle проверка **преди** 409 с `model_dump()` на съвпаденията (`ING/main.py:213-221`); непригодни документи не се разкриват.
- Премести `test_poller_state.py` в `services/nextcloud-poller/tests/`.
- Тестове: 401/403 без/с грешен токен за всеки endpoint; unauthorized scope не вижда съвпаденията; poller ingest с токен. Runtime: rebuild само на ING + poller. Security review агент (P0).
- Done: unit + integration (curl със/без токен) + negative + commit.

### WP-02 — Answer gating + budget safety (F-02, F-04, F-15)
- `ORC/main.py:106`: `answer` се връща само при `answer_status` ∈ {GROUNDED, CONDITIONAL}; при NO_ANSWER/INSUFFICIENT — детерминистичен отказ с причина и какво липсва (по подразбиране; финалната формулировка → O-11).
- Gateway не показва `answer` без статус (`GW:1514-1519`); празен отговор → винаги съобщение.
- `BudgetExceeded` → контролиран NO_ANSWER/CONDITIONAL (не 500), със статус на бюджета.
- Тестове: NO_ANSWER не пуска текст на модела; budget=1 → 200 с отказ; GW не връща празен content. Runtime: rebuild ORC + GW.

### WP-03 — Qdrant auth (F-33) — BLOCKED(O-6)
- `QDRANT__SERVICE__API_KEY` + `api-key` в KE/ING клиентите; compose за qdrant (данните: bind `data/qdrant`, **без** изтриване/reset). Нужен е кратък downtime за recreate на qdrant.
- Тестове: заявка без ключ → 403; KE search/ingest работят; Qdrant данните (2353 точки) непроменени преди/след. Security review.

### WP-04 — User identity + ACL propagation (F-03) — BLOCKED(O-1)
- Според O-1: подписан identity контекст WebUI→GW→ORC→KE/ING; `user_context` се чете и се прилага към `access_scopes` на retrieval и structured query; fail-closed при липсваща идентичност.
- Тестове: user A не получава документ на user B (RAG + structured + web evidence provenance); липсваща identity → отказ; подправен header → отказ. Е2Е I (unauthorized source). Security review.

## P1

### WP-05 — Structured query routing (F-05, F-06, F-32, F-31, F-21)
- Свържи `parse_structured_query` в `brain.decide()` **преди** Brain (CORPORATE_KNOWLEDGE → parser → valid → STRUCTURED_QUERY; ambiguity → clarification); поправи `_FILE_RE` («От файла» префикс); сигнали за „редове/xls/лист“ (F-32).
- Подай към ING само валидирани filters (F-06 — `query` не се игнорира мълчаливо); непознат sheet → 4xx вместо 200/0 реда; числови gt/lt (F-21).
- Rebuild на ORC image до HEAD (F-31).
- Тестове: XLS+филтър → STRUCTURED_QUERY без Brain; ambiguity; непознат файл/колона/оператор → fail-closed; regression за известния дефект (7.1).xls. E2E B/C.

### WP-06 — Brain robustness + context role hygiene (F-08, F-10, F-16, F-19, F-34)
- Валидирай `input` на всички capability стъпки (`planner.py:54`); `except Exception` с лог + `decision_reason` в отговора (без chain-of-thought); „web“ в заявката не повишава CORPORATE_AND_WEB без policy; детерминизъм (temperature 0 / seed, fallback при разминаване); role whitelist в `context.py`, клиентски `system` → отхвърлен.
- Тестове: Brain unavailable/невалиден JSON/timeout → `deterministic_fallback` с причина; client system turn; invalid input на стъпка; E2E K, L.

### WP-07 — Prompt-injection boundary (F-14, F-40)
- Delimited „untrusted data“ блокове за документи и web в synthesis, semantic_verification, web_research; инструкции към модела; detection на command-подобен текст като evidence flag; `trusted_as_instruction` се налага.
- Тестове: документ и страница с „ignore previous instructions / use web / reveal prompt“ не променят plan, policy, статус.

### WP-08 — Web fetch hardening (F-39, F-45, F-46)
- Пиниране на проверения IP (rebinding), async DNS; само 80/443; общ `asyncio.timeout`; allow-list/trust tiers (F-46 → O-8).
- Тестове: rebinding резолвър, IPv6, link-local, порт 22/6379 → 403, бавно тяло → timeout; реален redirect към вътрешен адрес (с локален тестов сървър).

### WP-09 — KE corpus, evidence, conflict (F-11, F-12, F-13)
- Backfill `classification`/`canonical_source_verified` за 1829 chunk-а (payload update, **не** изтриване/reindex на колекцията; първо dry-run и броячи); `EvidenceRecord` с retrieval_score/page/chunk_id/query/verification_state; активирай conflict детектора (`scope`/`semantic_metric`) и applicability (stale).
- Тестове: stale document не се цитира; conflicting sources; evidence има пълния §5 минимум.
- Забележка: пише в production Qdrant — само след WP-03 и backup (WP-15 ако е налично, иначе Qdrant snapshot).

### WP-10 — Gateway hygiene (F-36, F-37, F-29, F-49, F-57, F-62)
- Лимити на messages/chars/body (413); structured logging без съдържание; премахни мъртвия `general` клон и legacy `print`; `docs_url/openapi_url=None` (GW, KE, ING); `GATEWAY_API_KEY:?`; нормализация на list/multimodal content.
- Тестове: 413; лог не съдържа message content; list-content.

### WP-12 — Conversation persistence + Context Manager (F-35, F-09, F-17, F-18) — BLOCKED(O-1,O-2,O-3)
- Според O-2/O-3: PG схема (conversations, messages, state, summaries), Context Manager със selection policy и token budget, scope filter във всяка memory заявка, enforce на `max_context_chars` и общ deadline.
- Тестове: дълъг multi-turn (E2E H), изолация user/conversation, compaction, противоречие между turns.

### WP-13 — Trace store (F-38, F-10) — BLOCKED(O-2)
- Operational trace (task_type, state, capability, evidence_id, verification_status, decision_reason, budget_usage; без chain-of-thought) + защитен достъп.

### WP-14 — IaC, embedding restart, pinning (F-42, F-43, F-52, F-59) — BLOCKED(O-6)
- Compose за qdrant, embedding, open-webui, caddy (Caddyfile без частни ключове) в repo; **qwen36 само документиран** (untouchable); digest pinning; healthchecks/лимити.
- Бърза мярка без recreate (по решение O-6): `docker update --restart unless-stopped` за embedding-test.

### WP-15 — Backup / restore (F-44, F-53) — BLOCKED(O-7)
- Скрипт + restore drill в ефимерни контейнери; `chmod 600 deploy/compose/.env`; криптиране/преместване на частните ключове в `backups/`.

### WP-16 — Network segmentation + hardening (F-41, F-47, F-48, F-56) — BLOCKED(O-5, O-10)
- Мрежи edge/app/data/egress; hardening на WebUI/postgres/qdrant/caddy; Caddy security headers, махни `papra`; инсталиране на boundary filter според O-10.

## P2–P3

### WP-11 — Test infrastructure + negative tests (F-50, F-51, F-30, F-61)
- `scripts/test.sh` (ефимерни контейнери, по сервиз); `tests/integration` (health, 401 без токен, happy path); E2E скрипт за acceptance A–L; тестове по матрицата от `agent_F.md` §2; дублираното име на тест (F-30); CI според O-9.

### WP-17 — Ingestion robustness (F-22, F-23, F-24, F-25, F-26, F-28, F-60)
- Zip bomb/magic bytes/лимит на страници/NUL; poller 4xx state; `error=str(e)` към caller; enum за `access_scope`/`classification`; F-22 по O-4; cleanup на тестови данни и Exited контейнери само с разрешение O-12.

### WP-18 — Retrieval quality (F-20, F-27)
- Hybrid (dense + keyword/номер на договор); PG парола от compose във secret.

### WP-19 — Documentation sync (F-54, F-55 + §16)
- Преномерирай DECISIONS блок B (#96–#103); обнови CHECKPOINT, PROJECT_MASTER, REQUIREMENTS, RISKS, ROADMAP, CURRENT_STATUS, SERVICES/NETWORK/DATA_FLOW/STORAGE/DOCKER/RECOVERY; запиши решенията O-1…O-12 в DECISIONS. Документацията описва реалното състояние.

---

# Решения на собственика

Всяко решение: варианти, trade-offs, препоръка. Пакетите, които зависят от тях, са маркирани `BLOCKED(O-x)` по-горе. Препоръките не са приложени; след избор → запис в DECISIONS.

### O-1 Identity модел (F-03) — блокира WP-04, WP-12
- **A. Per-user identity:** Open WebUI праща user/групи (`ENABLE_FORWARD_USER_INFO_HEADERS`), Gateway подписва контекст (JWT/HMAC), ORC/KE/ING мапват групи → `access_scopes` (таблица в PG). + истинска ACL, одит, основа за памет/история. − най-много работа; нужно мапване групи→scopes и съгласие какви са групите.
- **B. Единен корпоративен principal:** всички потребители имат един и същи достъп; приемаме го изрично и документираме (текущото състояние). + нулева работа. − няма разграничаване на документи (HR/финанси); блокира персонална памет/история; не е „fail-closed“ за различни нива.
- **C. Няколко connection-а/API key (по отдел/роля) в WebUI:** ключ = scope набор. + бързо, без промяна в WebUI. − идентичност на ниво отдел, не потребител; ключове се споделят; не дава user-level история.
- **Препоръка: A**, с B като документиран междинен статус до WP-04. Ако в момента всички потребители са доверени и еднакво оторизирани, може да се започне с C за бърза реална граница.

### O-2 Persistence на разговори и trace (F-35, F-38) — блокира WP-12, WP-13
- **A. Пълен C8** (10 PG таблици, summaries, memory). + покрива DEC #75–84. − голям обем; изисква O-1, O-3.
- **B. Минимум:** `conversations` + trace таблица в PG; историята остава в Open WebUI. + бързо, дава §17 observability. − без дълга памет/summary.
- **C. Stateless:** без нищо. + нищо за поддръжка. − не покрива §10/§17; не можем да обясним отговор post-hoc.
- **Препоръка: B сега, A като следващ етап** след O-1.

### O-3 Retention и поверителност на разговори (F-35, F-37) — блокира WP-12
- **A.** 30 дни, съдържанието само в PG, логове без съдържание. **B.** 90 дни + потребителско изтриване. **C.** без ограничение.
- Trade-off: по-дълго = по-добър контекст/одит, по-голям privacy/GDPR риск и повърхност при изтичане.
- **Препоръка: B**, с изтриване по заявка и без съдържание в операционни логове. Нужна е и справка с вътрешната политика за лични данни.

### O-4 Семантика на версиите на документи (F-22) — блокира частта на WP-17
- **A.** Идентичност по SHA-256+scope; връщане към стар хеш → изрично „re-promote“ през API. **B.** Отхвърляне на A→B→A (текущо `DUPLICATE_VERSION_NOT_CURRENT`). **C.** Всяко качване е нова версия (без дедуп по хеш за стари).
- **Препоръка: A** — запазва SHA-256 принципа (#44) и позволява легитимно връщане към стара редакция. Без `source_reference` → документите с еднакво име остават отделни, но ambiguity се показва (не CURRENT дубликат).

### O-5 Мрежова сегментация и auth на vLLM (F-41) — блокира WP-16
- **A.** 3–4 Docker мрежи (edge/app/data/egress); vLLM остава непроменен, защитен от мрежата. **B.** `--api-key` на vLLM (променя untouchable inference config — само с изрично разрешение). **C.** Плоска мрежа + auth на qdrant и вътрешни services.
- **Препоръка: A + auth на Qdrant (WP-03)**; B не се прави.

### O-6 Обхват на IaC и прозорец за поддръжка (F-33, F-42, F-43) — блокира WP-03, WP-14
- **A.** Compose в repo за qdrant, embedding, open-webui, caddy; recreate в уговорен прозорец (кратък downtime). qwen36 само документиран.
- **B.** Само документация (inspect снимки); без recreate; Qdrant ключът → необходим recreate, не е постижим.
- **C.** Включително qwen36 — **изключено** (untouchable).
- **Препоръка: A.** Преди recreate: backup/snapshot на Qdrant, `data/qdrant` без промяна. За `embedding-test` бърза мярка: `docker update --restart unless-stopped` (без recreate). Преименуването на `-test` контейнерите става чрез мрежови алиаси.

### O-7 Backup политика (F-44) — блокира WP-15
- **A.** Нощен дъмп на същия хост. **B.** Нощен + копие извън хоста (напр. Synology NAS), шифровано; 7 дневни + 4 седмични; тестван restore. **C.** Ръчно при промяна.
- **Препоръка: B.** RPO ≤ 24 ч; RTO за ефимерен restore drill. Нужно е да решиш дестинацията и къде се пази ключът за шифроване.

### O-8 Web source policy (F-46) — блокира F-46 от WP-08
- **A.** Само официални домейни (строг allow-list). **B.** Нива на доверие: official / trusted / other (други — само с предупреждение, без да влизат като факт). **C.** Отворено (текущо).
- **Препоръка: B**, при `INTERNAL_FIRST_WEB_FALLBACK`; първоначален списък домейни — от теб.

### O-9 Къде се пускат тестовете (F-50)
- **A.** Само локален `scripts/test.sh`. **B.** GitHub Actions (unit; без GPU). **C.** Self-hosted runner на DGX (integration/E2E срещу живите services).
- **Препоръка: A сега + B за unit;** C отлагаме, докато не се стабилизират IaC и мрежите. Не е блокиращо — WP-11 започва с A.

### O-10 Open WebUI граница и 67-те файла (F-47)
- **A.** Инсталирай boundary filter, изключи native Knowledge/file RAG; всичко през Corporate AI (в съответствие с DECISIONS #20,21,23,34). **B.** Native Knowledge остава като отделен, неавторитетен канал с видим етикет. **C.** Статукво.
- 67-те съществуващи файла: не се изтриват без изрично разрешение; можем да ги инвентаризираме и мигрираме през ingestion.
- **Препоръка: A**, миграция/инвентар на файловете вместо изтриване.

### O-11 Формулировка на отказ/условен отговор (F-02, F-15)
- **A.** Кратък отказ + какво липсва + предложение (уточнение / web). **B.** Условен отговор с изрични уговорки, когато има частични доказателства. **C.** Технически статус (за админи).
- **Препоръка: A за NO_ANSWER, B за CONDITIONAL**, C само в trace. WP-02 ползва A като стойност по подразбиране — не е блокиран.

### O-12 Разрешение за изтриване на тестови данни и стари контейнери (F-28, F-60)
- **A.** Само инвентар (списък) — без изтриване. **B.** Изтриване на тестови документи в PG/Qdrant след backup и с одобрен списък; изтриване на Exited контейнери (не volumes). **C.** Нищо.
- Rules §14 забранява загуба на production data → без изрично одобрение е A.
- **Препоръка: A сега;** B след WP-15 и преглед на списъка от теб.
