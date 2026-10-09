# CORPORATE AI — ПОСТОЯННИ ПРАВИЛА ЗА CLAUDE CODE

> Този файл се зарежда веднъж и важи за всички сесии.
> Сложи го в repo като `.claude/CORPORATE_AI_RULES.md` и добави в `CLAUDE.md` ред:
> `Правилата за работа са в @.claude/CORPORATE_AI_RULES.md — спазвай ги винаги.`
> Ако използваш `@`-import, той зарежда файла при всяка сесия. Тогава не го поставяй и в prompt-а.

---

## 0. Контекст

- Repo: `Italik78/corporate-ai`, dir `~/corporate-ai`, branch `feature/corporate-ai-gateway-v0.1`, checkpoint `3e70c5d`.
- Model: `Qwen3.6-35B-A3B-NVFP4`, service `corporate-ai-qwen36`, API `http://corporate-ai-qwen36:8000/v1`, model name `qwen36`. Не сменяй модела или inference архитектурата без доказана необходимост.
- Роля: senior engineer + architect + reviewer + tester. Целта е production-ready, evidence-first система: **„всезнайко, но не измисляч“**.

## 1. ПРАВИЛА ЗА ИКОНОМИЯ НА ТОКЕНИ (задължителни)

Тези правила не намаляват обхвата. Те само премахват повторното и излишното четене.

### 1.1 Състояние на диск, не в контекста
Цялото състояние на работата се пази във файлове. Всяка сесия чете **само тях**, а не целия проект отначало:

```
99_MANAGEMENT/audit/AUDIT_FINDINGS.md   — находки (формат §11)
99_MANAGEMENT/audit/BACKLOG.md          — P0–P4 backlog със статус
99_MANAGEMENT/audit/SESSION_LOG.md      — ≤15 реда на сесия: какво е направено, commit-и, следваща стъпка
99_MANAGEMENT/audit/ARCH_MAP.md         — компактна карта: services, entrypoints, request flows, ключови файлове:редове
```

- Преди да четеш код, прочети `SESSION_LOG.md` (последните 2 записа) и `BACKLOG.md`.
- `ARCH_MAP.md` се пише веднъж по време на audit-а. След това се **ползва вместо повторно изследване**, а при промяна в кода се обновява.

### 1.2 Дисциплина при четене
- Първо `Grep`/`Glob`, после `Read` само на нужния диапазон (`offset`/`limit`). Целия файл четеш само ако е под ~300 реда или се променя.
- Документите: първо заглавията (`grep -n '^#'`), после само релевантните секции.
- Не чети повторно файл, който вече е в контекста. Не чети повторно файл след `Edit`.
- Не чети lock-файлове, generated код, `node_modules`, `.venv`, data/fixture dump-ове и големи логове.

### 1.3 Дисциплина при изход от команди
- Tests: `pytest -q -x --tb=short 2>&1 | tail -40`. Пълният suite се пуска само преди commit. По време на работа пускай само засегнатите тестове.
- Docker: `docker compose ps --format 'table {{.Name}}\t{{.Status}}'`, `docker logs --tail 80 <svc>`, `curl -s ... | head -c 2000`.
- Никога не изкарвай целия `docker compose config`, пълни логове или пълни HTTP отговори.
- `git log --oneline -20`, `git diff --stat`. Пълен diff само за файла, който преглеждаш.

### 1.4 Subagents: целенасочено, не масово
- **Максимум 3 паралелни агента.** Всеки агент стартира от нула и повтаря четенето, затова 7 паралелни агента струват ~7× контекста.
- За read-only изследване ползвай агент тип `Explore` с `model: haiku` или `sonnet`. Задачата трябва да има точен обхват (кои директории/файлове), точен въпрос и формат на резултата.
- Агентът **записва детайлите във файл** (`99_MANAGEMENT/audit/agent_<X>.md`) и връща на главната сесия **≤30 реда резюме**.
- Подай на агента релевантната секция от `ARCH_MAP.md` и файловете/редовете, вместо да го оставяш да открива repo-то сам.
- Review след имплементация: **един** review агент на работен пакет, с checklist от 5 измерения (correctness, security, tests, architecture, documentation). Така се покриват същите 5 гледни точки като при 5 отделни reviewer-а. Отделен агент се пуска само за P0 security промени.

### 1.5 Модели
- Audit синтез, архитектурни решения и разрешаване на конфликти: Opus. Ако е налично, ползвай `/model opusplan` (Opus в plan mode, Sonnet при изпълнение).
- Имплементация, тестове и документация: Sonnet.
- Търсене и изброяване: Haiku агенти.

### 1.6 Сесии на работни пакети
- Една сесия = един работен пакет (виж `SESSION_PROMPTS.md`). Пакетът завършва → `SESSION_LOG.md` → commit → **стоп**.
- Ако контекстът стане голям в средата на пакет: обнови `SESSION_LOG.md`, после `/compact` с инструкция какво да се запази.
- Между пакетите: `/clear`. Новата сесия продължава от файловете, а не от историята на чата.

## 2. Работен процес (непроменен по съдържание)

- **Първо разбиране, после промени.** Не прави архитектурни предположения, които можеш да провериш в repo-то.
- Не приемай, че TODO документацията описва всички проблеми. Проверявай кода, runtime-а, Docker, тестовете и интеграциите.
- **Не преправяй проекта от нула.** Преди refactor провери: защо компонентът съществува, кой го ползва, кои тестове го покриват, какъв е API договорът му, какво пише в `DECISIONS.md` и дали промяната нарушава Repository Contract. Refactor е допустим само заради correctness, security, maintainability, testability, архитектурна съвместимост или production readiness.
- **Не измисляй API.** Преди да ползваш endpoint, намери го в кода, заедно със schema, auth, tests и runtime поведение. Ако не съществува, имплементирай го или адаптирай caller-а.
- **Не приемай mock/stub/fake като завършена feature.** Това важи особено за Brain, retrieval, web search/fetch, verification, ingestion, structured query, memory, context и security. При placeholder: документирай → намери production path → имплементирай → тествай.
- **Противоречие** между docs, code, tests и runtime не се прикрива. Определи кое е authoritative според DECISIONS и реалното поведение. Ако е нужна архитектурна промяна: decision → code → tests → docs.

### Цикъл за всеки gap
1. Локализирай проблема.
2. Намери root cause.
3. Провери зависимостите.
4. Провери за частична имплементация.
5. Провери тестовете.
6. Направи минимална, архитектурно правилна промяна.
7. Добави regression tests.
8. Пусни засегнатите тестове.
9. Пусни integration тестовете.
10. Провери runtime.
11. Обнови документацията.
12. Commit.
13. Продължи към следващия gap.

### Приоритети
`P0` correctness/security blockers · `P1` архитектурни пропуски · `P2` липсваща production функционалност · `P3` robustness/observability · `P4` optimization/polish. **Не започвай P2/P3, докато има отворен P0.**

## 3. Целева архитектура

```
Open WebUI → Corporate AI Gateway → Conversation & Context Management → AI Brain
→ Deterministic Control Plane → Capability execution → Evidence collection
→ Verification → Answer / Re-plan / Refusal
```

Brain планира само в рамките на: capability registry, source policy, authorization, budgets, evidence requirements, verification rules и task state machine. **Brain никога не заобикаля deterministic control plane.**

Съществуващи компоненти: `BrainPlanStep`, `BrainDecision`, `validate_decision()`, `CapabilityRegistry`, `TaskType`, `TaskState`, `Budget`. Провери: decision schema, capability authorization, source policy, structured query validation, fallback, malformed output, unavailable Brain, invalid capability/arguments, budget exhaustion, loops, conflict handling, re-planning.

## 4. Продуктов принцип и source policy

**Разрешено:** корпоративни документи, структурирани данни, Knowledge/RAG, web search/fetch, reasoning, synthesis, cross-source comparison, verification, explicit uncertainty.

**Забранено:** измислени факти, citations, документи, DB резултати и web резултати; отговор на база „усещане“; неконтролиран интернет; неконтролирани tool calls; произволен избор на документ; скриване на конфликт между източници.

При недостатъчно доказателства: `NO_ANSWER` или `CONDITIONAL_ANSWER`.

- Корпоративните данни са authoritative за корпоративни въпроси, когато има достатъчно evidence.
- Web се ползва само когато: policy го позволява, корпоративните източници не стигат, въпросът изисква актуална публична информация, или е нужен cross-check.
- Web резултат никога не се представя като корпоративен факт и обратно. Всеки evidence item има provenance.

## 5. Evidence и verification

Минимум за evidence: `source`, `source class`, `document/page/row/url`, `evidence identifier`, `retrieval context`, `verification state`.
Състояния: `SUPPORTED`, `CONFLICT`, `INSUFFICIENT_EVIDENCE`, `NOT_REQUIRED`.

Retrieval score ≠ истина. Retrieval намира кандидати, evidence evaluation определя приложимостта, а verification решава дали отговорът може да бъде публикуван.

Verification трябва реално да спира грешни отговори. Проверява: semantic support, unsupported claims, contradictions, numeric consistency, source consistency, applicability, stale information, conflicting sources. При проблем → `re-plan`, `conditional answer` или `no answer`, никога само warning в лога.

## 6. Structured Query

Файлове: `services/ai-orchestrator/app/structured_query.py`, `.../structured_query_parser.py`, `services/document-ingestion/app/structured_query.py`, `.../document_reference.py`.

E2E поток: NL → task classification → structured-query detection → deterministic parser → exact document resolution → ACL/current lifecycle validation → structured query → row evidence → verification → answer.

**Известен дефект:** Qwen Brain избира `CORPORATE_RETRIEVAL` вместо `STRUCTURED_QUERY` за ясен XLS файл + филтър. Не приемай Brain classification за достатъчна. Ако дефектът е налице, добави deterministic subclassification **преди** Brain decision, без да променяш общия TaskType:

```
CORPORATE_KNOWLEDGE → deterministic parser → valid? YES → STRUCTURED_QUERY / NO → Brain
```

Parser-ът не измисля файл, sheet, column, operator или value. При ambiguity връща ambiguity.

## 7. Document Ingestion

Pipeline: `RECEIVED → SECURITY_CHECK → DEDUPLICATING → ROUTING → EXTRACTING → NORMALIZING → METADATA → INDEXING → READY | FAILED`.
Lifecycle: `INGESTING → CURRENT → SUPERSEDED → ARCHIVED`.

Провери: SHA-256 dedup (никога само по filename), scoped identity, ACL, current lifecycle, versioning, provenance, original storage key, structured query, PDF/scanned PDF/OCR/vision, сложни документи, durable poller state.

## 8. Knowledge/RAG

Поток: query → retrieval → filtering → access control → evidence → provenance → verification. Провери Qdrant и embedding договорите и scoping-а на retrieval. **Ако synthesis може да ползва документ, до който потребителят няма достъп, това е security bug (P0).**

## 9. Web Search/Fetch

Провери: SearXNG, нормализация, provenance, official domains, fetch, timeout, SSRF, URL validation, redirects, content limits, duplicate sources, source trust, evidence extraction, citation generation. Никога: `search result title → fabricated factual answer`.

## 10. Conversation & Context

Провери спрямо `01_ARCHITECTURE/CONVERSATION_CONTEXT_MANAGEMENT.md`: conversation identity, turns, state, context layers, selection, summarization, memory, provenance, priority, token budget, compaction, дълги разговори, relevant-history retrieval, conflicts. Контекстът никога не се подава сляпо към LLM; задължителна е selection policy.

## 11. Формат на находките (AUDIT_FINDINGS.md)

```
ID | Priority | Component | Evidence (file:line / команда+изход) | Root cause | Impact | Required change | Tests required | Dependencies
```

Отчетът от audit-а съдържа: 1. Current architecture · 2. Working · 3. Partially implemented · 4. Broken · 5. Missing · 6. Security risks · 7. Test gaps · 8. Runtime gaps · 9. Documentation inconsistencies · 10. Exact implementation backlog.

## 12. Security (fail-closed)

Провери: authentication, service-to-service tokens, API keys, authorization, ACL, source isolation, prompt injection (документи и web), malicious documents, SSRF, arbitrary URL fetch, tool abuse, изтичане на secrets, logs, PII, cross-user context leakage, cross-project retrieval leakage, document access leakage, Docker exposure, host ports, вътрешни services, Open WebUI boundary.

## 13. Testing

"Tests pass" не доказва production readiness. Нужна е test pyramid: **Unit** (parser, state machine, validators, policy, evidence, verification), **Integration** (service-to-service), **E2E** (Open WebUI → Gateway → Orchestrator → capability → evidence → verification → answer), **Regression** (не чупи работещи тестове).

**Задължителни negative tests:** ambiguous document, inaccessible document, conflicting sources, empty retrieval, web unavailable, Brain unavailable, invalid Brain decision, malformed tool input, timeout, budget exhaustion, duplicate document, stale document, unauthorized source, prompt injection, SSRF, unsupported claim.

## 14. Runtime (недеструктивно)

Провери реално `docker compose ps`, health endpoints и свързаността между Gateway, Orchestrator, Qwen, Knowledge Engine, Qdrant, Document Ingestion, SearXNG и Open WebUI. При нужда rebuild само на конкретния service и integration tests.

**Забранено:** изтриване на volumes, reset на database, reset на Qdrant, загуба на production data.

## 15. Git

Преди работа: `git status`, `git branch --show-current`, `git log --oneline -20`; потвърди branch-а и checkpoint-а.

**Забранено:** force push, rebase/reset на remote история без изрично разрешение, `git reset --hard` върху непроверени промени.

Commit след всяка логически завършена задача, формат `type(scope): description` (напр. `fix(orchestrator): deterministically detect structured queries`).

## 16. Документация

При архитектурна промяна обнови `PROJECT_MASTER.md`, `REQUIREMENTS.md`, `DECISIONS.md`, `RISKS.md`, `ROADMAP.md`, `CURRENT_STATUS.md` и съответния архитектурен документ. Документацията описва реалното състояние; никога не се променя, за да скрие дефект.

## 17. Observability

Trace-ът трябва да отговаря на въпросите: какво е поискал потребителят, как е класифицирана задачата, какъв context е избран, какво е решил Brain, кои capabilities са извикани, какви evidence са получени и как са оценени, имало ли е conflict, как е минала verification и защо е даден точно този отговор.

Trace-ът съдържа operational metadata (`task_type`, `state`, `capability`, `source`, `evidence_id`, `verification_status`, `decision_reason`, `budget_usage`) и **не съдържа** private chain-of-thought.

## 18. Budgets (реално enforcement)

`max_steps=12 · max_capability_calls=12 · max_retrieval_rounds=3 · max_web_searches=3 · max_web_fetches=5 · max_verification_rounds=2 · max_context_chars=120000`. Без безкрайни цикли, без неконтролирани web calls, без неконтролиран растеж на контекста.

## 19. Definition of Done

Feature е done само при всичко изброено: implementation + unit + integration + negative tests + runtime validation + security validation + documentation + Git commit. Core компонентите изискват и E2E валидация.

## 20. Финален acceptance pass

A. Corporate knowledge → верен evidence → verified answer
B. Structured: NL → точен XLS → filters → rows → evidence → answer
C. Ambiguous document → clarification
D. Web: search → fetch → evidence → verification → citations
E. Corporate + Web → контролирана комбинация
F. Conflict → conflict handling
G. Insufficient evidence → без халюцинации
H. Дълъг multi-turn → правилен релевантен контекст
I. Unauthorized source → denied
J. Invalid/unauthorized capability → denied
K. Brain unavailable/invalid → deterministic safe fallback
L. Повтарящо се planning/tool calls → bounded execution

## 21. Финален отчет

```
PROJECT STATUS
Architecture / Implemented / Fixed / Still incomplete / Security / Tests / E2E / Runtime / Documentation / Git / Remaining risks
```

За всеки незавършен елемент посочи конкретно защо не е завършен. Никога „всичко е готово“, ако има gaps.
