# Implementation Backlog

Дата обновления: 2026-04-29

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
- `backend/scripts/smoke_review_approval_mcp.sh`
- `backend/scripts/smoke_configuration_library_mcp.sh`

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

Статус: Done.

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

Twelfth slice done:

- добавлена persisted template library: `TemplateLibraryApplicationService`, `PostgresTemplateStore` и миграция `0010_document_templates.sql`;
- `TemplateCatalog` и `SectionContractBuilder` теперь поддерживают `template_version`, сохраняя приоритет inline `template_payload`;
- `AuthoringApplicationService` теперь может резолвить шаблоны из persisted library по `task_context.template_id/template_version`;
- `ApiContainer` wires template library в authoring path без изменения внешних API;
- добавлены unit/integration tests для fallback store, versioned template resolution и authoring через persisted template library;
- targeted template library tests: `89 passed`;
- full suite with Docker async e2e and OpenRouter external LLM enabled: `199 passed`.

Thirteenth slice done:

- добавлен public template management API boundary: `PUT /api/v1/templates/{template_id}`, `GET /api/v1/templates/{template_id}`, `GET /api/v1/templates`;
- добавлены typed API contracts для upsert/get/list reusable templates;
- `TemplateLibraryApplicationService` получил compile helper для API path, без обхода existing `TemplateCompiler`;
- persisted template library теперь доступна не только внутреннему authoring path, но и как управляемая service boundary;
- добавлены integration tests для template API flow и 404 path;
- targeted template API tests: `54 passed`;
- full suite with Docker async e2e and OpenRouter external LLM enabled: `202 passed`.

Fourteenth slice done:

- добавлен Template Library MCP boundary: `FastMcpTemplateLibraryService`, `apps/mcp_template_library/main.py` и typed MCP schemas `schemas.mcp.template_library`;
- MCP tools `upsert_template/get_template/list_templates` переиспользуют existing `TemplateLibraryApplicationService` и `TemplateCompiler`, без отдельной template-specific архитектуры;
- добавлены runtime/smoke scripts `run_template_library_mcp.sh/.ps1` и `smoke_template_library_mcp.sh/.ps1`;
- добавлены unit tests для Template Library MCP metadata, upsert/get/list flow и missing-template error mapping;
- добавлен ADR-0059 и обновлены README/SAO/runbook под новый MCP boundary;
- targeted template MCP/API tests: `40 passed`;
- full suite with Docker async e2e and OpenRouter external LLM enabled: `205 passed`.

Fifteenth slice done:

- добавлен baseline template governance status `draft|published` для persisted template library;
- добавлен `publish_template` path в `TemplateLibraryApplicationService`, HTTP API и Template Library MCP;
- authoring без явного `template_version` теперь резолвит последнюю `published` template version, сохраняя приоритет inline `template_payload` и explicit version lookup;
- добавлена миграция `0011_template_status_governance.sql` и расширены fallback/PostgreSQL template store read models;
- добавлены unit/integration tests для publish flow, published-only resolution и authoring default behavior;
- добавлен ADR-0060 и обновлены README/SAO/runbook/scripts docs;
- targeted governance tests: `80 passed`;
- local suite without external flags: `208 passed, 3 skipped`.

Sixteenth slice done:

- `TemplateCompiler` и `SectionContractBuilder` получили richer template assembly policy baseline:
  - section-level поля `required`, `include_if_has_evidence`, `include_if_review_status`, `section_group`;
  - assembly-level поля `include_sections`, `exclude_sections`, `allowed_section_groups`;
- `DocumentAssembler` теперь применяет эти richer rules при выборе итоговых секций и фильтрации section traceability;
- `ArtifactExporter` переиспользует тот же deterministic section selection path, поэтому `markdown` и `json` больше не расходятся по составу секций;
- `OutlinePlanner` и `AuthoringApplicationService` теперь строят template-aware `section_traceability` для custom templates, а не только для release-readiness default path;
- добавлен ADR-0061 и расширены unit tests для compiler normalization, template-aware traceability, conditional section inclusion и JSON export consistency;
- targeted authoring/domain tests: `44 passed`;
- full suite with Docker async e2e and OpenRouter external LLM enabled: `216 passed`.

Seventeenth slice done:

- template library publish semantics стали exclusive: для одного `template_id` теперь допускается только одна active `published` version;
- `publish_template` автоматически demote-ит предыдущую published version обратно в `draft` в fallback и PostgreSQL store path;
- HTTP API, MCP и authoring default published-resolution продолжают работать через тот же `TemplateLibraryApplicationService` без изменения публичных контрактов;
- добавлен ADR-0062 и расширены unit/integration tests для publish demotion semantics;
- targeted governance/API/MCP tests: `65 passed`;
- full suite with Docker async e2e and OpenRouter external LLM enabled: `219 passed`.

Eighteenth slice done:

- template governance закрыт до production-compatible lifecycle: `draft|published|deprecated|archived`;
- добавлен explicit `set_template_status` path в `TemplateLibraryApplicationService`, HTTP API (`POST /api/v1/templates/{template_id}/status`) и Template Library MCP;
- fallback/PostgreSQL template store теперь сохраняют governance metadata/history в `metadata.governance` и продолжают поддерживать exclusive published invariant;
- authoring default resolution теперь требует published template, explicit archived version запрещена, explicit deprecated version остается доступной;
- расширены smoke/unit/integration tests для lifecycle transitions, archived guardrails и MCP governance path;
- targeted governance/authoring/API/MCP tests: `122 passed`;
- full suite with Docker async e2e and OpenRouter external LLM enabled: `232 passed`.

Demo update:

- generated artifact должен собираться section-by-section;
- traceability должен сохраняться на уровне секций и source refs;
- HITL flow должен уметь отправлять section на повторную доработку.

Definition of Done:

- application layer только оркестрирует use case;
- authoring domain testable отдельно от FastAPI;
- итоговый документ собирается deterministic assembly.

Next increment:

- начать `Increment 29: Unified Execution Plane + Observability`.

## Increment 29: Unified Execution Plane + Observability

Статус: Done.

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

First slice done:

- async execution plane расширен с authoring на `knowledge_indexing` через existing dispatcher/Celery wiring, без новой параллельной архитектуры;
- добавлены `KnowledgeIndexingAsyncDispatcher`, `InlineKnowledgeIndexingAsyncDispatcher`, `CeleryKnowledgeIndexingAsyncDispatcher`;
- `KnowledgeIndexingApplicationService` поддерживает `start_task_async(...)` и `run_existing_task(...)`;
- добавлен endpoint `POST /api/v1/tasks/knowledge-indexing/start_async`;
- worker app получил task `run_knowledge_indexing_task`, отдельную queue `knowledge-indexing` и env `APP_CELERY_INDEXING_QUEUE`;
- worker dispatcher normalizes host `source_paths` в `/workspace/...` для docker-compose bind mount;
- `Dockerfile.worker` подтянут до parser-compatible dependency set (`python-docx`, `PyMuPDF`), чтобы async indexing покрывал `.docx/.pdf` fixtures так же, как sync path;
- добавлены unit/integration/e2e tests для async indexing path и Celery dispatcher path normalization.

Second slice done:

- retrieval lifecycle переведен на тот же async execution plane без breaking change для sync endpoint `POST /api/v1/tasks/retrieval/start`;
- добавлены `RetrievalAsyncDispatcher`, `InlineRetrievalAsyncDispatcher`, `CeleryRetrievalAsyncDispatcher`;
- `RetrievalApplicationService` поддерживает `start_async(...)` и `run_existing_task(...)`;
- добавлен endpoint `POST /api/v1/tasks/retrieval/start_async`;
- worker app получил task `run_retrieval_task`, отдельную queue `retrieval` и env `APP_CELERY_RETRIEVAL_QUEUE`;
- docker-compose async worker теперь слушает очереди `authoring`, `knowledge-indexing`, `retrieval`;
- добавлены unit/integration/e2e tests для async retrieval path;
- добавлены manual acceptance scripts `smoke_retrieval_async_api.sh/.py` и `demo_release_go_no_go_async_case.sh/.py`;
- targeted tests: `71 passed`;
- targeted Docker/Celery e2e: `4 passed`;
- full suite with Docker async e2e and OpenRouter external LLM enabled: `246 passed`.

Third slice done:

- task lifecycle details расширены execution metadata: `correlation_id`, `async_provider`, `queue_name`, `queued_at`, `started_at`, `completed_at|failed_at`, `queue_wait_ms`;
- добавлен read-model endpoint `GET /api/v1/tasks/observability/summary` с current-state counts и latency aggregates по `task_type`;
- async smoke/demo scripts теперь явно показывают execution trace и observability aggregates для retrieval/indexing/authoring paths;
- async release readiness report показывает queue/dispatch/correlation metadata;
- added ADR `0066-task-observability-summary-and-execution-metadata.md`;
- targeted tests: `76 passed`;
- full suite with Docker async e2e and OpenRouter external LLM enabled: `246 passed`.

Fourth slice done:

- добавлен shared helper `infra.logging.runtime` для one-line structured JSON logs на stdlib logging;
- FastAPI endpoints, Celery worker tasks и `AuthoringApplicationService` теперь эмитят structured runtime events с `task_id`, `correlation_id`, `dispatch_id`, `queue_name`, `decision`, `iteration`;
- `HitlActionStore` расширен агрегатами `summarize_actions(...)`, а API получил endpoint `GET /api/v1/hitl/observability/summary`;
- async authoring smoke показывает reviewer/HITL observability summary рядом с existing task observability summary;
- added ADR `0067-structured-logging-and-hitl-observability-summary.md`;
- targeted tests: `75 passed`;
- full suite with Docker async e2e and OpenRouter external LLM enabled: `252 passed`.

Increment closed:

- полный gate with Docker async e2e and OpenRouter external LLM enabled: `252 passed`.

## Increment 30: MCP + Production Boundary

Статус: In Progress.

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

First slice done:

- добавлен Review/Approval MCP boundary:
  - `backend/apps/mcp_review_approval/main.py`;
  - `backend/packages/infra/fastmcp/review_approval_service.py`;
  - `backend/packages/schemas/mcp/review_approval.py`;
- MCP tools покрывают reviewer/HITL manual operations без доступа к internal state payload:
  - `get_hitl_status`;
  - `list_hitl_actions`;
  - `submit_hitl_review`;
  - `get_hitl_observability_summary`;
- boundary переиспользует existing `AuthoringApplicationService`, `PostgresHitlActionStore` и existing async dispatcher plane, без новой review-specific архитектуры;
- добавлены operational scripts `run_review_approval_mcp.sh/.ps1` и `smoke_review_approval_mcp.sh/.ps1`;
- добавлен ADR `0068-review-approval-mcp-boundary.md`;
- targeted MCP/authoring/API tests: `78 passed`;
- manual smoke Review/Approval MCP: passed;
- full suite with Docker async e2e and OpenRouter external LLM enabled: `259 passed`.

Second slice done:

- добавлен Configuration Library MCP skeleton:
  - `backend/apps/mcp_configuration_library/main.py`;
  - `backend/packages/application/configuration_library_service.py`;
  - `backend/packages/infra/postgres/configuration_store.py`;
  - `backend/packages/infra/fastmcp/configuration_library_service.py`;
  - `backend/packages/schemas/mcp/configuration_library.py`;
- MCP tools покрывают persisted configuration artifacts без знания internal storage payload:
  - `upsert_config`;
  - `get_config`;
  - `list_configs`;
  - `find_similar_configs`;
  - `compare_configs`;
- boundary использует PostgreSQL/fallback persistence pattern через новую таблицу `app.configuration_library` и migration `backend/migrations/0012_configuration_library.sql`;
- similarity path реализован как deterministic heuristic поверх existing persisted config records, а compare path как deterministic diff по flattened JSON keys, без отдельного vector/runtime stack;
- добавлены operational scripts `run_configuration_library_mcp.sh/.ps1` и `smoke_configuration_library_mcp.sh/.ps1`;
- добавлен ADR `0069-configuration-library-mcp-skeleton.md`;
- targeted configuration MCP/persistence tests: `28 passed`;
- manual smoke Configuration Library MCP: passed;
- full suite with Docker async e2e and OpenRouter external LLM enabled: `265 passed`.

Third slice done:

- `BaseFastMcpService` получил unified MCP policy layer с валидируемым `tool_names`, `service_scope`, `operation_scopes`, `policy_version`, input/output validation markers и standard `audit_payload_fields`;
- все current FastMCP services (`retrieval`, `repository`, `artifact-writer`, `template-library`, `review-approval`, `configuration-library`) переведены на общий `_register_toolset(...)` и единый error mapping helper `_operation_error(...)`;
- `build_evidence_pack` зафиксирован как `operation_scope=action`, а read/write tools теперь получают consistent scope metadata автоматически;
- добавлен ADR `0070-unified-fastmcp-service-policies.md`;
- targeted MCP/framework tests: `53 passed`;
- full suite with Docker async e2e and OpenRouter external LLM enabled: `268 passed`.

Fourth slice done:

- добавлены базовые auth/RBAC boundaries для sensitive API/MCP operations через shared `framework.security.rbac` policy layer;
- FastAPI template governance endpoints (`upsert/publish/set status`) и authoring HITL submit endpoint теперь поддерживают header-based actor context (`X-Actor-Id`, `X-Actor-Roles`) и при `APP_AUTH_ENABLED=true` возвращают `401/403` для unauthorized access;
- `BaseFastMcpService` расширен auth-aware metadata (`auth_policy`, `tool_required_roles`) и unified `_authorize_tool(...)` helper;
- sensitive FastMCP tools теперь требуют explicit roles в typed payloads: `template_admin`, `reviewer`, `config_admin`, `artifact_writer`, `repository_writer`;
- при выключенном auth (`APP_AUTH_ENABLED=false`) сохранена backward compatibility для текущих smoke/demo paths;
- добавлен ADR `0071-rbac-boundaries-for-sensitive-api-and-mcp-operations.md`;
- targeted auth/MCP/API tests: `101 passed`;
- full suite with Docker async e2e and OpenRouter external LLM enabled: `278 passed`.

Fifth slice done:

- добавлен production runbook `docs/production_runbook.md` для stage/prod rehearsal:
  - deploy;
  - migrate;
  - FastAPI smoke;
  - async/Celery smoke;
  - MCP smoke;
  - RBAC rehearsal;
  - backup/restore;
  - rollback;
  - release gate;
- добавлен handoff checklist `docs/handoff/2026-04-27_increment_30_production_boundary_handoff.md`;
- добавлены contract tests `backend/tests/unit/test_production_runbook_contracts.py`, которые проверяют, что runbook ссылается на существующие scripts и покрывает обязательные operational sections/env flags;
- Increment 30 production boundary теперь имеет documented stage/prod rehearsal path перед переходом к Knowledge Factory Hardening;
- targeted runbook contract tests: `3 passed`;
- full suite with Docker async e2e and OpenRouter external LLM enabled: `281 passed`.

## Increment 31: Knowledge Factory Hardening

Цель: довести canonical ingestion до требований ТЗ по форматам, quality gates и production parsing behavior.

First slice done:

- добавлен typed parser quality read-model baseline для canonical ingestion:
  - `ParserQualityIssue` и `ParserQualitySummary` в `schemas.documents`;
  - `CanonicalDocument.parser_quality` теперь хранит parser family, extraction mode, page/block/heading/list/table counts и typed issues;
- `CanonicalDocumentParser` теперь заполняет structured diagnostics для текущих `.md/.txt/.json/.docx/.pdf` adapters:
  - markdown/text фиксируют headings/lists counts;
  - DOCX помечает detected tables через `docx_tables_detected` и `table_extraction_not_implemented`;
  - PDF без extractable text дополнительно помечается как `ocr_required`;
- `KnowledgeIndexingApplicationService` task details и aggregated `quality_summary` расширены parser diagnostics полями:
  - `parser_quality` по каждому `doc_id`;
  - `parser_families`, `extraction_modes`, `parser_issues_total`, `documents_with_tables`, `documents_needing_ocr`;
- retrieval/reporting/read-model path теперь тоже отдает `parser_quality` metadata для canonical sources;
- smoke/report path обновлен:
  - `smoke_knowledge_indexing.sh/.ps1` и `smoke_knowledge_indexing_api.sh/.ps1` выводят parser diagnostics;
  - `release_readiness_report.md` показывает parser diagnostics внутри `Canonical Quality Summary`;
- добавлен ADR `0072-canonical-parser-quality-read-model-baseline.md`;
- targeted parser/indexing/retrieval/report tests: `78 passed`.

Second slice done:

- добавлен OCR preflight + scanned PDF fallback path для canonical parser:
  - новый adapter boundary `domain_docs.parsing.ocr.PdfOcrGateway`;
  - infra adapters `SidecarPdfOcrGateway` и optional `OcrmypdfGateway`;
  - `CanonicalDocumentParser` теперь при `pdf_no_extractable_text` пытается OCR recovery и пишет `ocr_applied|ocr_provider:*|ocr_not_available|ocr_text_not_recovered` quality flags;
- API/container wiring поддерживает env-driven OCR runtime:
  - `APP_OCR_ENABLED=true|false`;
  - `APP_OCR_PROVIDER=sidecar|ocrmypdf`;
  - optional `APP_OCR_LANGUAGE`, `APP_OCR_TIMEOUT_SEC` для real CLI path;
- demo input расширен OCR сценарием:
  - `07_scanned_signoff.pdf`;
  - `07_scanned_signoff.pdf.ocr.txt` как deterministic OCR sidecar fixture;
- smoke/report/tests теперь показывают OCR path в Knowledge Indexing details и canonical quality summary;
- targeted OCR/parser/indexing/API/report tests: `78 passed`.

Third slice done:

- усилен DOCX parser hardening path:
  - `CanonicalDocumentParser` теперь извлекает `CanonicalTable` в `extracted_tables`;
  - строки DOCX tables становятся canonical `table_row` blocks и попадают в indexing/retrieval corpus;
  - numbered/list paragraphs нормализуются как `bullet` blocks;
  - appendix-like headings помечаются через `appendix_section_detected`;
- demo DOCX fixture `05_release_notes.docx` расширен реальными структурами:
  - numbered deployment checklist;
  - approval matrix table со статусами `PENDING/READY/APPROVED`;
  - appendix section с rollback contacts;
- tests и API smoke теперь проверяют, что demo DOCX реально отдает `extracted_tables` и `table_row` blocks, а не только quality flag;

Fourth slice done:

- исправлен parity bug между direct shell smoke и API/container indexing path:
  - `backend/scripts/smoke_knowledge_indexing.py` теперь использует `ApiContainer().knowledge_indexing_service`, а не вручную собранный `KnowledgeIndexingApplicationService` без OCR-aware parser;
  - direct smoke теперь совпадает с API smoke по env-driven OCR runtime и корректно показывает `ocr_applied`/`ocr_recovered_doc_ids` для scanned PDF fixture;
- добавлен regression test `backend/tests/unit/test_smoke_knowledge_indexing_script.py`, который фиксирует container-managed behavior для direct smoke path;
- manual smoke docs и README уточнены: при `APP_OCR_ENABLED=true` и `APP_OCR_PROVIDER=sidecar` прямой smoke больше не должен возвращать `ocr_not_available` для `07_scanned_signoff.pdf`;
- targeted tests + direct/API smoke verification + full suite with Docker async e2e and OpenRouter external LLM enabled: planned after slice finalization.

Fifth slice done:

- retrieval/source mapping обогащен table-aware provenance для canonical `table_row` blocks без новой retrieval архитектуры;
- canonical indexing vector metadata и canonical dataset path теперь сохраняют/отдают:
  - `source_kind=table_row`;
  - `table_id`, `table_title`, `table_columns`;
  - `row_index`, `row_values`;
  - `section_title`;
- `FastMcpRetrievalService.lookup_source` теперь возвращает typed provenance и typed table payload для table-backed evidence;
- `release_readiness_report` и Retrieval MCP smoke теперь могут явно показать, что evidence пришел из approval matrix row, а не из абстрактного paragraph block;
- добавлен ADR `0074-table-aware-canonical-retrieval-provenance.md`;
- targeted provenance/retrieval/report tests: `18 passed`.

Sixth slice done:

- canonical parser baseline расширен поддержкой `.xlsx` через `openpyxl`;
- workbook sheets теперь становятся structural sections, sheet tables попадают в `extracted_tables`, а строки листов индексируются как canonical `table_row` blocks;
- binary demo input расширен реальным fixture `08_release_tracker.xlsx`;
- indexing/API tests и parser demo tests теперь проверяют, что XLSX проходит тот же canonical/indexing path, что и DOCX/PDF/JSON;
- добавлен ADR `0075-xlsx-parser-baseline-for-canonical-ingestion.md`;
- targeted parser/indexing/API tests: `70 passed`;
- full suite with Docker async e2e and OpenRouter external LLM enabled: `296 passed`.

Seventh slice done:

- добавлена version-aware canonical document policy без ломки текущего latest-by-doc_id поведения;
- `PostgresCanonicalDocumentStore` теперь хранит latest read-model отдельно от historical versions:
  - latest tables: `app.canonical_documents`, `app.knowledge_blocks`;
  - history tables: `app.canonical_document_versions`, `app.knowledge_block_versions`;
- `CanonicalDocumentApplicationService` поддерживает explicit version lookup и `list_versions(...)`;
- Knowledge Indexing API/request contracts и smoke scripts поддерживают `document_version`;
- re-index semantics очищают latest vector entries по `doc_id`, но historical canonical versions остаются доступными для explicit lookup/source mapping;
- Retrieval MCP `lookup_source` теперь принимает optional `version` и умеет резолвить historical `block_ref`;
- targeted canonical-version-policy tests: `104 passed`.

Eighth slice done:

- quality gates canonical indexing переведены в отдельный production policy layer:
  - добавлен `domain_docs.indexing.quality_policy.KnowledgeIndexingQualityPolicy`;
  - policy возвращает typed per-document decisions (`accepted/rejected`) и aggregate decision (`gate_status`, `blocking_flags`, `warning_flags`);
- `KnowledgeIndexingApplicationService` теперь применяет policy до persistence workflow:
  - rejected documents не сохраняются в canonical store и не индексируются в `app.embeddings`;
  - accepted documents проходят прежний `KnowledgeIndexingWorkflow` path;
  - OCR-recovered scanned PDF (`pdf_no_extractable_text` + `ocr_applied`) остается warning-path по умолчанию;
- `ApiContainer` собирает policy из env (`APP_INDEXING_QUALITY_*`) без изменения публичных API;
- `quality_summary` в task details/state payload расширен policy metadata:
  - `policy_name`;
  - `accepted_documents_total` / `rejected_documents_total`;
  - `accepted_doc_ids` / `rejected_doc_ids`;
  - `blocking_flags` / `warning_flags`;
- добавлен ADR `0077-production-indexing-quality-policy-layer.md`;
- targeted quality/indexing tests: `18 passed` (`13 + 5`);
- full suite with Docker async e2e and OpenRouter external LLM enabled: `301 passed`.

Ninth slice done:

- canonical parser baseline расширен поддержкой `.pptx` через `python-pptx`;
- slides теперь становятся structural sections, а presentation content индексируется как canonical blocks:
  - `slide_title`;
  - `paragraph`;
  - `bullet`;
  - `note` (speaker notes);
- parser diagnostics/quality flags расширены для presentation path:
  - `pptx_slides_detected`;
  - `pptx_notes_detected`;
- binary demo input расширен новым fixture `09_release_briefing.pptx`;
- `build_binary_demo_documents.py` теперь генерирует `.pptx` вместе с `.docx/.pdf/.xlsx`;
- demo/smoke expectations и API tests обновлены на `documents_total=9` и `file_types` с `pptx`;
- worker image dependency set расширен `python-pptx` для async indexing parity;
- добавлен ADR `0078-pptx-parser-baseline-for-canonical-ingestion.md`;
- targeted parser/indexing/API/e2e tests: `26 passed`;
- full suite with Docker async e2e and OpenRouter external LLM enabled: `299 passed`.

Tenth slice done:

- добавлен PDF page provenance baseline для canonical retrieval/report path:
  - `source_kind=page_block`;
  - `page_number`;
  - `layout_source`;
  - `bbox` (best-effort);
- исправлена нумерация PDF block ids на global-per-document path:
  - многостраничные PDF больше не создают коллизии `B-1` между страницами;
  - `structure_tree.block_ids` теперь согласован с итоговыми `content_blocks`;
- canonical dataset loader и pgvector retriever metadata mapping теперь сохраняют page provenance в `RetrievedBlock.metadata`;
- Retrieval MCP `lookup_source` source provenance расширен page-level полями без breaking изменений existing payload;
- release readiness report `Canonical Source Mapping` теперь показывает `pages=...` и `layout_sources=...` для PDF evidence;
- добавлен ADR `0079-pdf-page-provenance-baseline-for-canonical-retrieval.md`;
- targeted parser/retrieval/report tests: `36 passed` + cross-check set `61 passed`;
- full suite with Docker async e2e and OpenRouter external LLM enabled: `303 passed`.

Eleventh slice done:

- добавлен richer PDF layout semantics baseline (v2) без изменения публичных API:
  - `reading_order_index` для page blocks (best-effort порядок чтения);
  - `layout_kind=paragraph|table_like` через lightweight layout эвристику;
  - parser quality flag `pdf_table_like_blocks_detected` при наличии table-like blocks;
- OCR fallback path также теперь заполняет `reading_order_index` и `layout_kind`;
- canonical dataset loader, pgvector metadata mapping и MCP `lookup_source` source provenance теперь прокидывают:
  - `reading_order_index`;
  - `layout_kind`;
- release readiness report `Canonical Source Mapping` теперь показывает `layout_kinds=...` для PDF evidence;
- добавлен ADR `0080-pdf-reading-order-and-layout-kind-baseline.md`;
- targeted parser/retrieval/report tests: `37 passed` + cross-check set `60 passed`;
- full suite with Docker async e2e and OpenRouter external LLM enabled: `304 passed`.

Twelfth slice done:

- добавлен PDF deep table extraction baseline для canonical ingestion:
  - table-like PDF blocks теперь materialize-ятся в `extracted_tables` и canonical `table_row` blocks;
  - `table_id` формируется как `PDF-T-*`, строки получают `row_index` и row-wise metadata через existing tabular builder;
- table rows из PDF сохраняют provenance metadata:
  - `source_kind=table_row`;
  - `page_number`, `reading_order_index`, `layout_kind`, `layout_source`, `bbox`;
- parser quality дополнен флагом `pdf_tables_extracted`;
- existing retrieval path переиспользован без новой архитектуры:
  - canonical dataset loader;
  - pgvector metadata mapping;
  - MCP `lookup_source`;
  - release report source mapping;
- добавлен ADR `0081-pdf-table-extraction-baseline-for-canonical-ingestion.md`;
- targeted parser/retrieval/report/indexing tests: `44 passed` + cross-check set `54 passed`;
- full suite with Docker async e2e and OpenRouter external LLM enabled: `304 passed`.

Thirteenth slice done:

- PDF table extraction hardening расширен form-like scenarios и demo-проверкой:
  - parser распознает form-like key/value blocks как tabular extraction path;
  - для form-like extraction добавлен quality flag `pdf_form_like_blocks_detected`;
  - table metadata и `table_row` metadata содержат `pdf_table_kind=form_like|pipe_table|spaced_table`;
- demo fixture `06_audit_summary.pdf` расширен:
  - complex table-like release controls;
  - form-like release gate block;
  - позволяет вручную проверить извлечение `extracted_tables` и `table_row` из PDF в smoke/demo;
- tests обновлены на demo + parser hardening assertions:
  - проверяется `pdf_tables_extracted` + `pdf_form_like_blocks_detected`;
  - проверяется presence `table_row` blocks и `pdf_table_kind=form_like`;
- добавлен ADR `0082-pdf-form-like-extraction-and-demo-fixture-hardening.md`;
- targeted parser/indexing/demo tests: `78 passed`;
- targeted retrieval/report tests: `20 passed`;
- full suite with Docker async e2e and OpenRouter external LLM enabled: `305 passed`.

Fourteenth slice done:

- добавлены PDF extraction coverage/partial-failure quality gates:
  - `pdf_table_candidates_total`;
  - `pdf_table_candidates_extracted`;
  - `pdf_table_rows_extracted`;
  - `pdf_table_rows_failed`;
  - `pdf_table_coverage_percent`;
- введен quality flag `pdf_table_extraction_partial` для случаев частичного извлечения table-like blocks;
- `parser_quality.issues` для `pdf_tables_extracted` и `pdf_table_extraction_partial` теперь отдает coverage/rows metadata;
- indexing aggregate quality summary расширен полями:
  - `documents_with_pdf_table_partial`;
  - `documents_with_pdf_form_like`;
- integration tests обновлены для проверки PDF table/form extraction в demo indexing path;
- добавлен ADR `0083-pdf-extraction-coverage-and-partial-failure-gates.md`;
- targeted parser/retrieval/indexing/integration tests: `99 passed`;
- full suite with Docker async e2e and OpenRouter external LLM enabled: `306 passed`.

Fifteenth slice done:

- добавлен PDF form-confidence baseline для canonical parser diagnostics:
  - `key_value_pairs_total`;
  - `key_value_pairs_extracted`;
  - `field_fill_rate_percent`;
  - `form_confidence_score`;
- `parser_quality.issues` для `pdf_form_like_blocks_detected` теперь отдает form-confidence metadata;
- `KnowledgeIndexingQualityPolicy` расширен порогом form confidence:
  - env `APP_INDEXING_QUALITY_FORM_CONFIDENCE_MIN_SCORE` включает threshold (0..100, `0` = disabled);
  - при score ниже threshold policy добавляет synthetic flag `pdf_form_confidence_low`;
  - env `APP_INDEXING_QUALITY_FORM_CONFIDENCE_LOW_BLOCKING=true|false` включает fail-fast блокировку или warning-only режим;
- indexing aggregate quality summary расширен:
  - `documents_with_pdf_form_confidence_low`;
  - `form_confidence_min_score`;
  - `pdf_form_confidence_by_doc`;
- report/smoke path обновлен для form-confidence counters в `Canonical Quality Summary`;
- добавлен ADR `0084-pdf-form-confidence-policy-gate.md`;
- targeted parser/policy/indexing/report/integration tests: `85 passed`;
- full suite with Docker async e2e and OpenRouter external LLM enabled: `309 passed`.

Sixteenth slice done:

- усилен PDF form-like parser для production layout edge-cases:
  - поддержка ключей с пробелами/дефисами;
  - поддержка multi-line continuation values;
- добавлен rotated-layout baseline без изменения публичных API:
  - `rotated_text=true|false` в metadata page/table blocks;
  - parser quality flag `pdf_rotated_layout_detected`;
  - diagnostics metadata: `rotated_table_candidates_total`, `rotated_table_candidates_extracted`;
- demo fixture `06_audit_summary.pdf` обновлен:
  - multi-line form value;
  - rotated form-like line для ручной smoke/demo проверки;
- tests расширены на multi-line form extraction и rotated-layout detection;
- добавлен ADR `0085-pdf-multiline-form-and-rotated-layout-hardening.md`;
- targeted parser/indexing/integration tests: `87 passed`;
- full suite with Docker async e2e and OpenRouter external LLM enabled: `311 passed`.

Seventeenth slice done:

- добавлена OCR confidence calibration baseline для scanned PDF path:
  - parser issue `ocr_applied` теперь отдает diagnostics metadata:
    - `ocr_blocks_total`;
    - `ocr_words_total`;
    - `ocr_weird_char_ratio_percent`;
    - `ocr_confidence_score`;
- `KnowledgeIndexingQualityPolicy` расширен OCR confidence threshold-политикой:
  - env `APP_INDEXING_QUALITY_OCR_CONFIDENCE_MIN_SCORE` включает threshold (0..100);
  - при score ниже threshold policy добавляет synthetic flag `ocr_confidence_low`;
  - env `APP_INDEXING_QUALITY_OCR_CONFIDENCE_LOW_BLOCKING=true|false` включает fail-fast blocking или warning-only режим;
- indexing aggregate quality summary расширен:
  - `documents_with_ocr_confidence_low`;
  - `ocr_confidence_min_score`;
  - `ocr_confidence_by_doc`;
- report/smoke/docs обновлены для OCR confidence counters и policy knobs;
- добавлен ADR `0086-ocr-confidence-calibration-and-policy-gate.md`;
- targeted parser/policy/indexing/report/integration tests: `90 passed`;
- full suite with Docker async e2e and OpenRouter external LLM enabled: `314 passed`.

Eighteenth slice done:

- усилен PDF pipe-table extraction для merged/wrapped rows:
  - markdown separator rows (`| --- | --- |`) игнорируются как data rows;
  - continuation rows склеиваются в предыдущую строку для merged/wrapped cell values;
- smoke demo path теперь отдает explicit proof по реальному `06_audit_summary.pdf`:
  - direct smoke: `pdf_demo_proof` в `smoke_knowledge_indexing.py`;
  - API smoke: `pdf_demo_proof` в `smoke_knowledge_indexing_api.py`;
- proof payload фиксирует extraction признаки:
  - `found`;
  - `tables_total`/`table_rows_total`;
  - `has_pdf_tables_extracted`;
  - `has_pdf_form_like_blocks_detected`;
  - `has_pdf_rotated_layout_detected`;
- добавлен ADR `0087-pdf-merged-table-hardening-and-demo-proof.md`;
- targeted parser/smoke/indexing/integration tests: `92 passed`;
- manual demo proof on real PDF fixture:
  - `smoke_knowledge_indexing.sh --build-binary-demo-docs` -> `pdf_demo_proof.found=true`, `tables_total=4`, `table_rows_total=6`;
  - `smoke_knowledge_indexing_api.sh --build-binary-demo-docs` -> `pdf_demo_proof.found=true`, `has_pdf_tables_extracted=true`.
- full suite with Docker async e2e and OpenRouter external LLM enabled: `315 passed`.

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
- parser adapters для `.xlsx` и `.pptx` реализованы; PDF table+form baseline, coverage gates, form-confidence policy gate, multi-line/rotated hardening, OCR-confidence calibration и demo-proof contracts закрыты; следующий шаг — production rollout/fail-fast policy tuning на real corpus.
- добавить document versions/read-model policy:
  - stable canonical identity;
  - version-aware lookup;
  - re-index semantics;
- quality gates переведены в конфигурируемый production policy layer; следующий шаг — production rollout/fail-fast policy.

Demo update:

- release go/no-go multifile case расширяется table/list fixture;
- smoke показывает quality gate decisions по parser families.

Definition of Done:

- canonical document model покрывает целевой parsing stack первого production-контура;
- quality gates могут блокировать indexing в production policy;
- retrieval получает source refs с page/table/section mapping.

## Increment 32: Governance, Quality и Release Gate

Цель: завершить backend/framework foundation как управляемую production-ready основу.

First slice done:

- execution metrics MVP реализован поверх existing task read-model без новой telemetry storage:
  - `GET /api/v1/tasks/events/summary` расширен `daily[]`/`weekly[]` (`bucket_start`, `total_events`, `unique_tasks`);
  - `GET /api/v1/tasks/observability/summary` и breakdown по `task_type` расширены quality/token агрегатами:
    - `avg_selected_block_count`, `avg_confidence`;
    - `tasks_with_unresolved_gaps`, `unresolved_gaps_total`;
    - `llm_tokens_prompt_total`, `llm_tokens_completion_total`, `llm_tokens_total`;
- task lifecycle details теперь автоматически рассчитывают `duration_ms` при наличии `started_at` и `completed_at|failed_at`;
- authoring LLM path сохраняет `llm_tokens_*` в draft metadata, artifact metadata и task details (provider usage + estimate fallback path);
- обновлены API/unit/e2e tests для новых агрегатов и token fields;
- добавлен ADR `0088-execution-metrics-mvp-day-week-and-token-quality-aggregates.md`;
- targeted tests: `98 passed`;
- full suite with Docker async e2e and OpenRouter external LLM enabled: `315 passed`.

Second slice done:

- observability SLA metrics добавлены поверх existing task read-model:
  - overall и per-task-type `p50/p95` для `duration_ms` и `queue_wait_ms`;
  - overall и per-task-type SLA breach counters:
    - `duration_sla_breaches_total`;
    - `queue_wait_sla_breaches_total`;
  - env-driven thresholds:
    - `APP_SLA_TASK_DURATION_MS`;
    - `APP_SLA_QUEUE_WAIT_MS`;
- `GET /api/v1/tasks/observability/summary` расширен периодными SLA time buckets:
  - `daily[]` и `weekly[]` (`total_tasks`, `completed_tasks`, `failed_tasks`, `waiting_human_tasks`, SLA breaches);
- обновлены contracts/api mappings/tests (unit + integration + e2e);
- добавлен ADR `0089-observability-sla-percentiles-and-time-buckets.md`;
- targeted tests: `76 passed`;
- full suite with Docker async e2e and OpenRouter external LLM enabled: `316 passed`.

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
