# Implementation Backlog

Дата обновления: 2026-04-23

Документ фиксирует план завершения backend/framework части платформы. Пока основной фокус остается на reusable framework, LangGraph runtime, service boundaries, persistence, MCP и demo/acceptance сценариях. Frontend и продуктовые домены расширяются только после стабилизации backend foundation.

## Принципы ведения

После каждой итерации обязательно:

1. Обновить `README.md`, `docs/architecture/System_Architecture_Overview.md` и релевантные ADR/design notes.
2. Обновить demo-сценарий release go/no-go, если изменились API, retrieval, authoring, HITL, ingestion или output artifacts.
3. Прогнать unit/integration/e2e тесты.
4. При наличии инфраструктурных изменений прогнать smoke/demo scripts в PostgreSQL профиле.
5. Сделать атомарный commit с понятным описанием инкремента.

## Acceptance Demo Harness

Основной ручной acceptance контур:

- `backend/scripts/demo_release_go_no_go_case.sh`
- `backend/scripts/demo_release_go_no_go_multifile_case.sh`
- `backend/scripts/smoke_authoring_api.sh`
- `backend/scripts/demo_release_authoring_traceability_case.sh`
- `backend/scripts/smoke_authoring_async_api.sh`
- `backend/scripts/demo_release_authoring_async_hitl_case.sh`

Минимальный критерий: после каждого backend-инкремента demo показывает связку `input documents -> retrieval/evidence -> authoring artifact -> traceability -> task events -> HITL/read-model`, если изменяемый слой влияет на этот путь.

## Increment 24: Framework Hardening

Статус: Done.

Цель: зафиксировать framework как устойчивую основу перед расширением ingestion, retrieval и authoring доменов.

Scope:

- провести ревизию `framework/*` contracts;
- добавить contract tests для базовых agents/tools/mcp/db/stores;
- описать стандартный путь расширения framework;
- зафиксировать acceptance matrix для demo;
- обновить архитектурную документацию и ADR.

Deliverables:

- `docs/framework_extension_guide.md`;
- ADR по framework hardening;
- дополнительные unit tests;
- обновленные `README.md` и SAO;
- зеленые тесты.

Definition of Done:

- новый workflow/tool/MCP service можно добавить по документированному пути;
- базовые framework contracts покрыты тестами на lifecycle и ошибки;
- demo-harness описан как обязательный acceptance слой.

## Increment 25: Knowledge Factory MVP

Статус: In progress. Первый срез реализует canonical contracts, `domain_docs`, parser `.md/.txt/.json`, `KnowledgeIndexingWorkflow` и smoke на release go/no-go multifile input. Следующий срез должен добавить binary formats и отдельный persistence слой для canonical documents / knowledge blocks.

Цель: закрыть разрыв между demo ingestion и целевой canonical document pipeline.

Scope:

- добавить `packages/domain_docs`;
- определить canonical document schemas:
  - document identity;
  - version;
  - source path;
  - file type;
  - metadata profile;
  - structure tree;
  - content blocks;
  - tables;
  - quality flags;
- реализовать parsers для `.md`, `.txt`, `.json`, `.docx`, `.pdf`;
- OCR путь оставить optional, но контракт качества заложить сразу;
- добавить `KnowledgeIndexingWorkflow`;
- добавить CLI/API entrypoint для ingestion;
- добавить persistence для canonical documents и knowledge blocks.

Demo update:

- расширить release go/no-go входы `.docx`/`.pdf`;
- в report показывать source mapping и quality flags;
- сохранить текущий file/dir demo как быстрый fallback.

Definition of Done:

- ingestion создает canonical representation;
- indexing task сохраняется в task registry и task events;
- retrieval может читать новые knowledge blocks через стандартный интерфейс.

First slice done:

- canonical representation создается для `.md/.txt/.json`;
- canonical payload сохраняется через existing document repository boundary;
- release go/no-go multifile input проверяется через `smoke_knowledge_indexing.sh/.ps1`.

## Increment 26: Production Retrieval Fabric

Цель: перевести retrieval с demo/in-memory режима на indexed corpus.

Scope:

- реализовать pgvector-backed summary/detail retrievers;
- подключить real TEI embedding gateway для indexing;
- подключить real TEI rerank gateway в authoring path;
- расширить Retrieval MCP:
  - `search_summaries`;
  - `search_blocks`;
  - `lookup_source`;
- добавить retrieval quality gates:
  - low evidence count;
  - low confidence;
  - missing methodology/source refs;
  - unresolved gaps;
- добавить contract tests для retrieval adapters.

Demo update:

- release go/no-go должен уметь запускаться из indexed corpus;
- file/dir режим остается bootstrap/demo режимом;
- report должен явно показывать confidence и unresolved gaps.

Definition of Done:

- evidence pack строится из Postgres/pgvector knowledge store;
- metadata filtering работает через SQL/JSONB;
- authoring path использует rerank.

## Increment 27: Domain Authoring Extraction

Цель: вынести authoring из крупного application service в отдельный доменный слой.

Scope:

- добавить `packages/domain_authoring`;
- выделить:
  - `TemplateCompiler`;
  - `SectionContractBuilder`;
  - `OutlinePlanner`;
  - `SectionAuthoringWorkflow`;
  - `SectionReviewService`;
  - `DocumentAssembler`;
  - `ArtifactExporter`;
- описать section packet и section digest schemas;
- добавить outline approval HITL point;
- сохранить совместимость существующих API:
  - `authoring/start`;
  - `authoring/start_async`;
  - `tasks/{task_id}/artifact`;
  - `tasks/{task_id}/hitl`;
  - `hitl/submit`.

Demo update:

- generated artifact должен собираться section-by-section;
- traceability должен сохраняться на уровне секций и source refs;
- HITL flow должен уметь отправлять section на повторную доработку.

Definition of Done:

- application layer только оркестрирует use case;
- authoring domain testable отдельно от FastAPI;
- итоговый документ собирается deterministic assembly.

## Increment 28: Unified Execution Plane + Observability

Цель: сделать async execution и observability общими для всех long-running workflows.

Scope:

- обобщить dispatcher за пределы authoring:
  - ingestion;
  - retrieval;
  - authoring;
  - quality evaluation;
- добавить retry/timeout/idempotency policy;
- добавить node-level task events;
- добавить correlation IDs;
- добавить structured JSON logging;
- добавить periodic aggregates:
  - task events day/week;
  - HITL SLA;
  - decision mix;
  - reviewer load.

Demo update:

- async smoke должен проверять task events на уровне graph nodes;
- HITL demo должен проверять SLA/read-model aggregates.

Definition of Done:

- все long-running workflows могут выполняться через единый execution plane;
- audit/read-model слой пригоден для dashboard;
- production troubleshooting возможен без чтения raw checkpoint payload.

## Increment 29: MCP + Production Boundary

Цель: довести service boundary до production-like состояния.

Scope:

- добавить Review/Approval MCP;
- добавить Configuration Library MCP skeleton;
- унифицировать MCP policies:
  - tool naming;
  - input/output validation;
  - audit payload;
  - error mapping;
  - operation scope;
- добавить базовые auth/RBAC boundaries для sensitive endpoints;
- подготовить production runbook:
  - deploy;
  - migrate;
  - smoke;
  - backup;
  - restore;
  - rollback.

Demo update:

- release scenario должен проходить через Repository MCP, Retrieval MCP, Artifact Writer MCP и Review/Approval MCP;
- report должен сохранять MCP operation refs в audit/metadata.

Definition of Done:

- MCP слой покрывает минимальный целевой набор;
- operational runbook достаточен для stage/prod rehearsal;
- service contracts не требуют knowledge of internal state payload.

## Later Product/UI Track

После backend/framework стабилизации:

- React/TypeScript frontend shell;
- task dashboard;
- evidence review screen;
- outline/section review screens;
- reviewer queue dashboard;
- generated artifacts/version screen;
- typed API client generated from OpenAPI;
- RBAC/SSO integration.

Этот трек не должен опережать backend contracts, иначе UI начнет закреплять временные API и runtime shortcuts.
