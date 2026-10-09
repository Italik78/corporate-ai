# CORPORATE AI — PROMPT-И ПО СЕСИИ

Всяка сесия: `/clear` → постави prompt-а → когато пакетът е готов, Claude обновява `SESSION_LOG.md`, прави commit и спира.
Правилата идват от `.claude/CORPORATE_AI_RULES.md` (чрез `CLAUDE.md`) и **не се поставят** отново.

---

## СЕСИЯ 0 — Setup (еднократно, евтино, Sonnet)

```
Прочети .claude/CORPORATE_AI_RULES.md. Изпълни §15 Git проверките и докладвай с ≤10 реда.
Създай 99_MANAGEMENT/audit/ с празни AUDIT_FINDINGS.md, BACKLOG.md, SESSION_LOG.md и ARCH_MAP.md (само заглавия).
Изпълни runtime snapshot по §14 с компактни команди (§1.3) и го запиши в ARCH_MAP.md, секция "Runtime".
Commit: chore(audit): scaffold audit workspace. Стоп.
```

## СЕСИЯ 1 — Архитектурна карта (Opus или opusplan)

```
Цел: ARCH_MAP.md, който служи като основа за всички следващи сесии. Без промени в кода.

1. Прочети задължителните документи от §0 на оригиналния план: 00_PROJECT/{PROJECT_MASTER,REQUIREMENTS,DECISIONS,RISKS}.md,
   99_MANAGEMENT/{ROADMAP,CURRENT_STATUS}.md, 04_KNOWLEDGE/{REPOSITORY_CONTRACT,DOCUMENT_INGESTION_SERVICE}.md,
   01_ARCHITECTURE/{CONVERSATION_CONTEXT_MANAGEMENT,SERVICES}.md. Първо заглавията, после релевантните секции (§1.2).
2. Изброй с Glob останалите архитектурни документи. Чети само тези за: Gateway, Brain, Orchestrator, Knowledge, RAG, Evidence,
   Verification, Tool Policy, Context, Memory, Ingestion, Structured Query, Web, Open WebUI, security, auth, provenance, audit, observability.
3. Изследвай repo структурата, docker-compose и service entrypoints.
4. Запиши в ARCH_MAP.md (компактно, с file:line): services и портове; entrypoints; request flow Open WebUI→LLM;
   RAG flow; Web flow; Brain/Control Plane; Context; Ingestion; Structured Query; тестова структура и как се пускат тестовете;
   ключови решения от DECISIONS; разлики docs↔code, забелязани по пътя.
Ограничение: ARCH_MAP.md ≤ 250 реда. Commit: docs(audit): architecture map. Стоп.
```

## СЕСИЯ 2 — Audit, част 1: core flow (Opus главна + 3 агента sonnet/haiku)

```
Използвай ARCH_MAP.md като контекст. Без промени в кода.
Пусни паралелно 3 Explore агента (model sonnet). На всеки подай съответната секция от ARCH_MAP.md и точните файлове.
Всеки записва детайли в 99_MANAGEMENT/audit/agent_<X>.md във формат §11 и връща ≤30 реда:
 A: Gateway → Context → Brain → Control Plane flow + Brain validation/fallback/budgets (§3, §18).
 B: Knowledge/RAG + Evidence + Verification (§5, §8). Включително ACL leakage при synthesis.
 C: Document Ingestion + Structured Query E2E (§6, §7). Включително проверка на известния дефект с класификацията.
После провери лично 2–3 от най-критичните твърдения (file:line), за да потвърдиш или отхвърлиш.
Обедини потвърдените находки в AUDIT_FINDINGS.md. Commit: docs(audit): core flow findings. Стоп.
```

## СЕСИЯ 3 — Audit, част 2: периметър (3 агента)

```
Същият подход като в сесия 2:
 D: Conversation & Context Management спрямо архитектурния документ (§10).
 E: Security audit по пълния списък от §12, включително Web SSRF/fetch (§9).
 F: Тестове + runtime: тестово покритие спрямо пирамидата и negative списъка (§13), пускане на съществуващия suite
    (компактен изход), health/connectivity по §14, docs↔code несъответствия (§16).
Обедини находките в AUDIT_FINDINGS.md.
След това напиши пълния audit отчет (10 секции от §11) в AUDIT_FINDINGS.md и BACKLOG.md с P0–P4.
Всеки backlog item: ID, priority, работен пакет (групирай свързаните items в пакети, побиращи се в една сесия), зависимости.
Commit: docs(audit): full audit report and backlog. Стоп и покажи резюмето на backlog-а (≤40 реда).
```

## СЕСИЯ 4…N — Изпълнение (Sonnet; Opus само при архитектурно решение)

```
Прочети последните 2 записа в SESSION_LOG.md и BACKLOG.md. Вземи следващия незавършен работен пакет с най-висок приоритет
(P0 преди всичко останало). Без допълнително потвърждение за очевидни технически стъпки.
За всеки item изпълни цикъла от §2 и Definition of Done от §19.
Чети само файловете, посочени в находката и в ARCH_MAP.md. Ако пакетът промени архитектурата, обнови ARCH_MAP.md.
В края на пакета: един review агент (model sonnet) с checklist correctness/security/tests/architecture/documentation
върху `git diff` на пакета. Ако е P0 security, добави отделен security review агент.
Ако reviewer-ите противоречат на нещо, провери кода и DECISIONS, вместо автоматично да приемеш едната страна.
Поправи → тестове → commit(и) → маркирай items в BACKLOG.md → запис в SESSION_LOG.md. Стоп.
```

## ФИНАЛНА СЕСИЯ — Acceptance

```
Прочети BACKLOG.md и SESSION_LOG.md. Провери, че няма отворени P0/P1, или ги изброи изрично.
Изпълни acceptance pass A–L от §20 срещу реалния runtime. За всеки сценарий запиши команда/заявка, резултат и PASS/FAIL
в 99_MANAGEMENT/audit/ACCEPTANCE.md. При FAIL добави backlog item и не обявявай проекта за завършен.
Напиши финалния отчет по §21, обнови CURRENT_STATUS.md и ROADMAP.md. Commit: docs(status): acceptance report. Стоп.
```

---

## Кратки съвети по време на работа
- `/cost` или `/usage` показва колко е изразходено. Ако един пакет изяде повече от ~⅓ от лимита, раздели го на по-малки.
- Ако контекстът се напълни в средата на пакет: `/compact Запази: текущ backlog item, променени файлове, failing тестове, следваща стъпка.`
- Не поставяй пак оригиналния master prompt. Цялото му съдържание вече е в RULES файла.
