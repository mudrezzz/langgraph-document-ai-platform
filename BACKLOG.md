# Implementation Backlog

Дата обновления: 2026-04-25

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

Статус: Done. Реализованы canonical contracts, `domain_docs`, parser `.md/.txt/.json/.docx/.pdf`, `KnowledgeIndexingWorkflow`, canonical persistence/read-model слой, canonical retrieval source, embedding/pgvector detail retrieval, binary demo input `.docx/.pdf`, task lifecycle API для indexing, smoke и canonical release go/no-go report.

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
- canonical payload сначала сохранялся через existing document repository boundary; во втором срезе заменено на canonical store;
- release go/no-go multifile input проверяется через `smoke_knowledge_indexing.sh/.ps1`.

Second slice done:

- canonical representation поддерживает базовый `.docx/.pdf` parser boundary;
- canonical documents сохраняются в отдельный `PostgresCanonicalDocumentStore`;
- derived content blocks пишутся в read-model `knowledge_blocks`;
- smoke показывает `stored_blocks_total > 0`.

Third slice done:

- retrieval поддерживает `task_context.knowledge_source=canonical`;
- canonical retrieval строит summary/detail blocks из `canonical_documents` и `knowledge_blocks`;
- smoke `smoke_canonical_retrieval.sh/.ps1` проверяет path `canonical indexing -> retrieval -> evidence`.

Fourth slice done:

- indexing пишет embeddings для canonical content blocks;
- vector metadata связывает embedding с `knowledge_blocks.block_ref`;
- canonical detail retrieval использует `CanonicalVectorRetriever`;
- smoke показывает `embeddings_indexed > 0` и `retrieval_backend=pgvector`.

Fifth slice done:

- release go/no-go multifile input расширен файлами `05_release_notes.docx` и `06_audit_summary.pdf`;
- добавлен генератор `build_binary_demo_documents.sh/.ps1/.py`;
- canonical indexing/retrieval smoke поддерживает `--build-binary-demo-docs`;
- manual PostgreSQL runbook описывает ручной прогон `.md/.txt/.json/.docx/.pdf`.

Sixth slice done:

- добавлен endpoint `POST /api/v1/tasks/knowledge-indexing/start`;
- Knowledge Indexing пишет task lifecycle в `app.tasks`, checkpoint payload и `app.task_events`;
- task details содержат counts, file types, `quality_summary` и `quality_gate_status`;
- добавлен smoke `smoke_knowledge_indexing_api.sh/.ps1`.

Seventh slice done:

- `demo_release_go_no_go_multifile_case.sh/.ps1` переведен на canonical route;
- demo запускает Knowledge Indexing API, затем retrieval с `knowledge_source=canonical` и `canonical_doc_ids`;
- `release_readiness_report.md` показывает `Canonical Quality Summary` и `Canonical Source Mapping`;
- report связывает evidence blocks с исходными `.md/.txt/.json/.docx/.pdf` файлами.

## Increment 26: Framework Runtime Closure

Статус: Done.

Цель: закрыть reusable framework runtime surface перед дальнейшим расширением retrieval, authoring и MCP доменов. После этого новые workflows/tools/subgraphs должны добавляться через устойчивые framework primitives, а не через временную application glue-логику.

Scope:

- доработать workflow runtime:
  - multi-node `BaseWorkflow` extension hooks;
  - рабочий `SubgraphWorkflow` contract;
  - node-level execution metadata;
  - typed interrupt/resume boundary;
  - устойчивый `thread_id`/`correlation_id` propagation;
- доработать tool execution:
  - `ToolExecutionPolicy`;
  - retry policy;
  - timeout accounting;
  - idempotency key handling;
  - audit records для tool calls;
  - contract tests на success/retry/failure/idempotency;
- доработать registry/factory слой:
  - DI-friendly `WorkflowFactory`;
  - понятные ошибки lookup/duplicate registration;
  - capability metadata для tools/workflows;
- зафиксировать framework execution context:
  - task id;
  - node name;
  - actor;
  - correlation id;
  - metadata;
- обновить `docs/framework_extension_guide.md`, README, SAO и ADR/design note.

Demo update:

- release demo может не измениться в первом срезе, если публичные API не меняются;
- после node-level events demo/smoke должен проверять хотя бы один graph-node event в task audit.

Definition of Done:

- новый tool/workflow/subgraph можно добавить с retry/idempotency/audit behavior без изменения application services;
- existing retrieval/knowledge-indexing/authoring tests остаются зелеными;
- framework contract tests фиксируют lifecycle, ошибки и metadata propagation;
- backlog содержит актуальный статус выполненных slices.

First slice done:

- добавлен policy-aware `ToolExecutor`;
- сохранена обратная совместимость `ToolExecutor(registry).execute(...)`;
- `ToolContext` расширен `node_name`, `correlation_id`, `idempotency_key`;
- добавлены `ToolExecutionPolicy`, `ToolExecutionRecord`, `ToolExecutionAuditSink`;
- добавлены audit/idempotency/retry contract tests;
- parser missing-dependency tests переведены с environment-dependent skip на monkeypatch-based проверку;
- full suite with Docker async e2e and OpenRouter external LLM enabled: `137 passed`.

Second slice done:

- добавлен `WorkflowExecutionContext` для workflow node execution;
- добавлен `WorkflowNodeSpec` как extension hook для sequential multi-node workflows;
- `BaseWorkflow` компилирует invoke/resume graphs из node specs;
- fallback runtime также исполняет node specs, сохраняя поведение без LangGraph;
- `SubgraphWorkflow` получил `subgraph_name`, `invoke_as_subgraph(...)` и parent context propagation;
- добавлены contract tests для multi-node invoke/resume, fallback runtime и subgraph context.
- full suite with Docker async e2e and OpenRouter external LLM enabled: `140 passed`.

Third slice done:

- `BaseWorkflow` эмитит `WorkflowNodeEventRecord` для node `started/completed/failed`;
- добавлен `WorkflowNodeEventSink` port;
- `TaskWorkflowNodeEventSink` мапит workflow node events в существующий `task_events` read-model;
- внешние API не изменились: node events доступны через `GET /api/v1/tasks/events` в `event_payload.event_kind=workflow_node`;
- retrieval и knowledge-indexing workflows подключены к node event sink через application services;
- добавлены unit/integration tests для explicit task events, workflow node events и API payload;
- обычный suite без внешних флагов: `141 passed, 2 skipped`.
- full suite with Docker async e2e and OpenRouter external LLM enabled: `143 passed`.

Fourth slice done:

- `WorkflowFactory` поддерживает DI-friendly `register_builder(...)` и `build(..., **dependencies)`;
- сохранена обратная совместимость `register("key", WorkflowClass)`;
- добавлены явные `WorkflowRegistrationError` и `WorkflowNotRegisteredError`;
- duplicate registration запрещен по умолчанию, осознанная замена требует `replace=True`;
- workflow capability metadata доступна через `metadata(key)`, discovery через `has(...)`/`list_workflows()`;
- обновлены framework extension guide, README, SAO и ADR-0040;
- full suite with Docker async e2e and OpenRouter external LLM enabled: `147 passed`.

Next increment:

- начать Increment 27: Production Retrieval Fabric.

## Increment 27: Production Retrieval Fabric

Статус: Done.

Цель: перевести retrieval с demo/in-memory режима на indexed corpus.

Scope:

- использовать framework runtime/tool policies из Increment 26;
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

First slice done:

- Knowledge Indexing пишет vector embeddings не только для `content_blocks`, но и для `section_summaries`;
- добавлен `CanonicalSummaryVectorRetriever` поверх pgvector с `kind=knowledge_summary_embedding`;
- `build_retrieval_workflow(... knowledge_source="canonical" ...)` использует pgvector-backed summary/detail retrievers при наличии `embedding_gateway` и `vector_store`;
- in-memory fallback для demo/bootstrap режима сохранен;
- добавлены contract tests для summary retriever, summary embedding indexing и canonical workflow с indexed summary/detail layers;
- full suite with Docker async e2e and OpenRouter external LLM enabled: `149 passed`.

Second slice done:

- `TeiEmbeddingGateway` поддерживает real TEI HTTP `/embed` endpoint через `TEI_EMBEDDING_URL` или `TEI_BASE_URL`;
- `TeiRerankGateway` поддерживает real TEI HTTP `/rerank` endpoint через `TEI_RERANK_URL` или `TEI_BASE_URL`;
- локальный deterministic fallback сохранен, а fallback при сетевой ошибке включается явно через `TEI_FALLBACK_ENABLED=true`;
- `ApiContainer` собирает embedding/rerank gateways из env;
- `RetrievalApplicationService` принимает injected `rerank_gateway`, поэтому authoring path использует тот же rerank adapter через retrieval service;
- добавлены unit tests на HTTP payload/parsing и fallback behavior;
- full suite with Docker async e2e and OpenRouter external LLM enabled: `153 passed`.

Third slice done:

- добавлен `RetrievalQualityPolicy` для evidence quality gates;
- `EvidenceBuilder` заполняет `EvidencePack.unresolved_gaps` и `confidence_notes`;
- поддержаны gates:
  - low evidence count;
  - low confidence;
  - missing required document types, включая `methodology`;
  - missing source refs;
- retrieval task details содержат `quality_gate_status`, `unresolved_gaps`, `confidence_notes`;
- release readiness report показывает confidence, retrieval quality gate и unresolved gaps;
- canonical retrieval smoke выводит `quality_gate_status`, `unresolved_gaps`, `confidence_notes`;
- добавлены unit tests на policy gaps и report output;
- full suite with Docker async e2e and OpenRouter external LLM enabled: `155 passed`.

Fourth slice done:

- Retrieval MCP расширен indexed canonical tools:
  - `search_summaries`;
  - `search_blocks`;
  - `lookup_source`;
- `search_summaries` использует `CanonicalSummaryVectorRetriever` поверх existing `embedding_gateway` + `vector_store`;
- `search_blocks` использует `CanonicalVectorRetriever` поверх того же indexed corpus;
- `lookup_source` читает canonical document/block source mapping через `CanonicalDocumentApplicationService`;
- `build_evidence_pack` сохранен без изменения внешнего контракта;
- добавлены typed MCP schemas и unit tests для metadata, summary/detail search, source lookup и backward compatibility;
- targeted MCP tests: `6 passed`.
- full suite with Docker async e2e and OpenRouter external LLM enabled: `159 passed`.

Fifth slice done:

- добавлен operational smoke для Retrieval MCP indexed tools:
  - `backend/scripts/smoke_retrieval_mcp.py`;
  - `backend/scripts/smoke_retrieval_mcp.sh`;
  - `backend/scripts/smoke_retrieval_mcp.ps1`;
- smoke прогоняет путь `canonical indexing -> search_summaries -> search_blocks -> lookup_source -> build_evidence_pack`;
- unit tests расширены на edge cases:
  - tags filtering для `search_blocks`;
  - doc-level lookup без `block_id`;
  - invalid `block_ref`;
  - missing `canonical_document_service`;
  - missing indexed dependencies;
- targeted MCP tests: `11 passed`.
- full suite with Docker async e2e and OpenRouter external LLM enabled: `164 passed`.

Sixth slice done:

- реальный Docker/Celery e2e расширен на iterative HITL path;
- `backend/tests/e2e/test_fastapi_authoring_async_celery_e2e.py` теперь покрывает:
  - `start_async -> waiting_human -> approve -> completed`;
  - `start_async -> waiting_human(iteration=1) -> needs_changes -> waiting_human(iteration=2) -> approve -> completed`;
- e2e проверяет `GET /api/v1/tasks/{task_id}/hitl`, `POST /api/v1/tasks/{task_id}/hitl/submit`, итоговый artifact metadata и `GET /api/v1/hitl/actions`;
- targeted Docker/Celery e2e: `2 passed`;
- full suite with Docker async e2e and OpenRouter external LLM enabled: `165 passed`.

Next increment:

- начать `Increment 28: Domain Authoring Extraction`.

## Increment 28: Domain Authoring Extraction

Статус: In Progress.

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

First slice done:

- добавлен пакет `backend/packages/domain_authoring`;
- выделены минимальные domain services:
  - `OutlinePlanner`;
  - `SectionReviewService`;
  - `DocumentAssembler`;
- `AuthoringApplicationService` интегрирует эти сервисы через dependency injection с дефолтными реализациями;
- внешние authoring API и HITL contracts не изменились;
- добавлен ADR-0045 и unit tests для новых domain services;
- targeted authoring tests: `11 passed`.

Second slice done:

- в `domain_authoring` добавлены `ResearchSummaryBuilder` и `WriterDraftService`;
- `AuthoringApplicationService` больше не содержит research summary formatting, deterministic draft formatting и LLM prompt composition;
- orchestration выбора `draft_strategy`, внешнего LLM gateway и fallback policy сохранена в application layer;
- добавлен ADR-0046 и расширены unit tests domain authoring.

Third slice done:

- `OutlinePlanner` теперь покрывает source-ref mapping для section traceability;
- `SectionReviewService` используется для массового обновления section review status;
- `WriterDraftService` форматирует human feedback при HITL rewrite;
- `AuthoringApplicationService` продолжает orchestration, но больше не содержит эти stateless helper-методы как самостоятельную domain logic;
- добавлен ADR-0047 и расширены authoring unit tests.

Fourth slice done:

- добавлены typed schemas `SectionContract` и `SectionPacket`;
- добавлен `SectionContractBuilder` в `domain_authoring`;
- `AuthoringApplicationService` строит section contracts из evidence/review context и сохраняет их в state + artifact metadata;
- публичные authoring/HITL API не изменены;
- добавлен ADR-0048 и unit tests для section contracts/packets.

Fifth slice done:

- добавлены typed `SectionArtifact` и `SectionAuthoringService`;
- section packets теперь реально используются для deterministic section draft/digest generation;
- `AuthoringTaskState` и artifact metadata сохраняют `section_artifacts`;
- финальный внешний API и assembled document пока сохранены без изменения;
- добавлен ADR-0049 и расширены unit tests.

Sixth slice done:

- добавлен `domain_docs.TemplateCompiler`;
- `SectionContractBuilder` теперь умеет строить contracts из `TemplateSpec`;
- `AuthoringApplicationService` поддерживает template-aware authoring через `task_context.template_id` и `task_context.template_payload`;
- дефолтный путь `release_readiness` сохранен для обратной совместимости;
- добавлен ADR-0050 и unit tests для custom templates.

Seventh slice done:

- `DocumentAssembler` теперь поддерживает template-aware deterministic assembly;
- итоговый документ может собираться из `TemplateSpec` и `section_artifacts`, а не только из release-readiness-specific layout;
- старый fallback path сохранен для обратной совместимости;
- добавлен ADR-0051 и расширены unit tests.

Eighth slice done:

- добавлены baseline `TemplateCatalog` и `InMemoryTemplateCatalog`;
- `TemplateSpec` расширен полем `assembly_rules`;
- `TemplateCompiler` компилирует и нормализует assembly rules;
- `DocumentAssembler` использует assembly rules для section order;
- `DocumentAssembler` теперь также применяет `include_writer_draft` и `include_traceability` из assembly rules;
- добавлен baseline `ArtifactExporter` для `markdown|json` export без изменения внешнего authoring API;
- `artifact_format=json` теперь возвращает structured artifact payload для template-aware authoring;
- добавлен ADR-0053 и unit/integration tests;
- targeted authoring/export tests: `61 passed`;
- full suite with Docker async e2e and OpenRouter external LLM enabled: `186 passed`.

Ninth slice done:

- `hitl_required=true` теперь сначала открывает outline approval pause перед section authoring и expose-ит outline snapshot через HITL status;
- HITL status read-model расширен полями `phase` и `outline`;
- approve path сохраняет совместимость существующего completion flow, а outline `needs_changes` переводит задачу в следующую HITL iteration без section authoring;
- добавлен ADR-0054 и unit/integration tests;
- targeted outline authoring tests: `64 passed`;
- full suite with Docker async e2e and OpenRouter external LLM enabled: `189 passed`.

Tenth slice done:

- добавлен baseline `SectionAuthoringWorkflow` поверх existing `SectionAuthoringService` и `SectionReviewService`;
- workflow использует typed `SectionAuthoringState` и multi-node path `write_section -> review_section -> finalize_section`;
- `AuthoringApplicationService` теперь строит `section_artifacts` через workflow boundary, без изменения внешних API;
- resume path поддерживает section-level human feedback как baseline rewrite hook;
- добавлен ADR-0055 и unit tests для invoke/resume workflow path;
- targeted section workflow tests: `66 passed`;
- full suite with Docker async e2e and OpenRouter external LLM enabled: `191 passed`.

Eleventh slice done:

- добавлен baseline `DocumentAssemblyWorkflow` поверх existing `DocumentAssembler` и `ArtifactExporter`;
- workflow использует typed `AssemblyWorkflowState` и multi-node path `assemble_document -> export_artifact -> finalize_document`;
- `AuthoringApplicationService` теперь проводит final assembly/export через workflow boundary, без изменения внешних API;
- `build_domain_authoring_services()` теперь отдает и `DocumentAssemblyWorkflow` как часть domain authoring wiring;
- добавлен ADR-0056 и unit tests для document assembly workflow и injected workflow path;
- targeted assembly workflow tests: `34 passed`;
- full suite with Docker async e2e and OpenRouter external LLM enabled: `193 passed`.

Demo update:

- generated artifact должен собираться section-by-section;
- traceability должен сохраняться на уровне секций и source refs;
- HITL flow должен уметь отправлять section на повторную доработку.

Definition of Done:

- application layer только оркестрирует use case;
- authoring domain testable отдельно от FastAPI;
- итоговый документ собирается deterministic assembly.

## Increment 29: Unified Execution Plane + Observability

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

## Increment 30: MCP + Production Boundary

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

## Increment 31: Knowledge Factory Hardening

Цель: довести canonical ingestion до требований ТЗ по форматам, quality gates и production parsing behavior.

Scope:

- OCR path для scanned PDF:
  - `OCRmyPDF`;
  - Tesseract adapter boundary;
  - quality flags для OCR confidence;
- rich layout extraction:
  - PDF logical blocks;
  - page/section mapping;
  - tables;
- DOCX hardening:
  - tables;
  - lists;
  - appendices;
- добавить parser adapters для:
  - `.xlsx`;
  - `.pptx`;
- добавить document versions/read-model policy:
  - stable canonical identity;
  - version-aware lookup;
  - re-index semantics;
- перевести quality gates из summary policy в конфигурируемый production policy layer.

Demo update:

- release go/no-go multifile case расширяется table/list fixture;
- smoke показывает quality gate decisions по parser families.

Definition of Done:

- canonical document model покрывает целевой parsing stack первого production-контура;
- quality gates могут блокировать indexing в production policy;
- retrieval получает source refs с page/table/section mapping.

## Increment 32: Governance, Quality и Release Gate

Цель: завершить backend/framework foundation как управляемую production-ready основу.

Scope:

- quality evaluation workflow;
- HITL/reviewer aggregates:
  - SLA;
  - decision mix;
  - reviewer load;
- task events aggregates за day/week;
- structured JSON logging и correlation id в API/worker/MCP;
- production runbook:
  - deploy;
  - migrate;
  - smoke;
  - backup;
  - restore;
  - rollback;
- release gate matrix:
  - unit;
  - integration;
  - e2e;
  - PostgreSQL smoke;
  - async/Celery smoke;
  - optional real LLM OpenRouter smoke.

Definition of Done:

- framework считается завершенным для backend foundation;
- новый продуктовый workflow добавляется через documented extension path;
- demo acceptance подтверждает полный путь `documents -> canonical indexing -> pgvector retrieval -> authoring -> HITL -> artifact -> traceability -> audit`;
- дальнейшее развитие может переходить к frontend/product layer без закрепления временных backend contracts.

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
