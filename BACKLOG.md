# Implementation Backlog

Update date: 2026-05-26

The document sets out the plan for completing the backend/framework part of the platform. For now, the main focus remains on the reusable framework, LangGraph runtime, service boundaries, persistence, MCP and demo/acceptance scenarios. Frontend and product domains are expanded only after the backend foundation has been stabilized.

## Principles of conduct

After each iteration, be sure to:

1. Update `README.md`, `docs/architecture/System_Architecture_Overview.md` and relevant ADR/design notes.
2. Update the release go/no-go demo script if the API, retrieval, authoring, HITL, ingestion or output artifacts have changed.
3. Run unit/integration/e2e tests.
4. If there are infrastructure changes, run smoke/demo scripts in the PostgreSQL profile.
5. Make an atomic commit with a clear description of the increment.

## Acceptance Demo Harness

Basic manual acceptance circuit:

- `backend/scripts/demo_release_go_no_go_case.sh`
- `backend/scripts/demo_release_go_no_go_multifile_case.sh`
- `backend/scripts/smoke_authoring_api.sh`
- `backend/scripts/demo_release_authoring_traceability_case.sh`
- `backend/scripts/smoke_authoring_async_api.sh`
- `backend/scripts/demo_release_authoring_async_hitl_case.sh`
- `backend/scripts/smoke_review_approval_mcp.sh`
- `backend/scripts/smoke_configuration_library_mcp.sh`

Minimum criterion: after each backend increment, the demo shows the link `input documents -> retrieval/evidence -> authoring artifact -> traceability -> task events -> HITL/read-model`, if the layer being modified affects this path.

## Increment 24: Framework Hardening

Status: Done.

Goal: to fix the framework as a stable basis before expanding ingestion, retrieval and authoring domains.

Scope:

- revise `framework/*` contracts;
- add contract tests for base agents/tools/mcp/db/stores;
- describe the standard path for extending the framework;
- fix acceptance matrix for demo;
- update architectural documentation and ADR.

Deliverables:

- `docs/framework_extension_guide.md`;
- ADR on frame hardening;
- additional unit tests;
- updated `README.md` and SAO;
- green tests.

Definition of Done:

- a new workflow/tool/MCP service can be added using a documented path;
- basic framework contracts are covered with lifecycle and error tests;
- demo-harness is described as a mandatory acceptance layer.

## Increment 25: Knowledge Factory MVP

Status: Done. Implemented canonical contracts, `domain_docs`, parser `.md/.txt/.json/.docx/.pdf`, `KnowledgeIndexingWorkflow`, canonical persistence/read-model layer, canonical retrieval source, embedding/pgvector detail retrieval, binary demo input `.docx/.pdf`, task lifecycle API for indexing, smoke and canonical release go/no-go report.

Goal: close the gap between demo ingestion and the target canonical document pipeline.

Scope:

- add `packages/domain_docs`;
- define canonical document schemas:
  - document identity;
  - version;
  - source path;
  - file type;
  - metadata profile;
  - structure tree;
  - content blocks;
  - tables;
  - quality flags;
- implement parsers for `.md`, `.txt`, `.json`, `.docx`, `.pdf`;
- Leave the OCR path optional, but lay down the quality contract right away;
- add `KnowledgeIndexingWorkflow`;
- add CLI/API entrypoint for ingestion;
- add persistence for canonical documents and knowledge blocks.

Demo update:

- expand release go/no-go inputs `.docx`/`.pdf`;
- in the report show source mapping and quality flags;
- save the current file/dir demo as a quick fallback.

Definition of Done:

- ingestion creates canonical representation;
- indexing task is saved in task registry and task events;
- retrieval can read new knowledge blocks through a standard interface.

First slice done:

- canonical representation is created for `.md/.txt/.json`;
- canonical payload was first saved through the existing document repository boundary; in the second section it is replaced by canonical store;
- release go/no-go multifile input is checked via `smoke_knowledge_indexing.sh/.ps1`.

Second slice done:

- canonical representation supports the basic `.docx/.pdf` parser boundary;
- canonical documents are saved in a separate `PostgresCanonicalDocumentStore`;
- derived content blocks are written in the read-model `knowledge_blocks`;
- smoke shows `stored_blocks_total > 0`.

Third slice done:

- retrieval supports `task_context.knowledge_source=canonical`;
- canonical retrieval builds summary/detail blocks from `canonical_documents` and `knowledge_blocks`;
- smoke `smoke_canonical_retrieval.sh/.ps1` checks path `canonical indexing -> retrieval -> evidence`.

Fourth slice done:

- indexing writes embeddings for canonical content blocks;
- vector metadata associates embedding with `knowledge_blocks.block_ref`;
- canonical detail retrieval uses `CanonicalVectorRetriever`;
- smoke shows `embeddings_indexed > 0` and `retrieval_backend=pgvector`.

Fifth slice done:

- release go/no-go multifile input expanded with files `05_release_notes.docx` and `06_audit_summary.pdf`;
- added generator `build_binary_demo_documents.sh/.ps1/.py`;
- canonical indexing/retrieval smoke supports `--build-binary-demo-docs`;
- manual PostgreSQL runbook describes a manual run of `.md/.txt/.json/.docx/.pdf`.

Sixth slice done:

- added endpoint `POST /api/v1/tasks/knowledge-indexing/start`;
- Knowledge Indexing writes task lifecycle in `app.tasks`, checkpoint payload and `app.task_events`;
- task details contain counts, file types, `quality_summary` and `quality_gate_status`;
- added smoke `smoke_knowledge_indexing_api.sh/.ps1`.

Seventh slice done:

- `demo_release_go_no_go_multifile_case.sh/.ps1` moved to canonical route;
- demo runs the Knowledge Indexing API, then retrieval with `knowledge_source=canonical` and `canonical_doc_ids`;
- `release_readiness_report.md` shows `Canonical Quality Summary` and `Canonical Source Mapping`;
- report links evidence blocks with source `.md/.txt/.json/.docx/.pdf` files.

## Increment 26: Framework Runtime Closure

Status: Done.

Goal: close the reusable framework runtime surface before further expanding the retrieval, authoring and MCP domains. After this, new workflows/tools/subgraphs should be added through stable framework primitives, and not through temporary application glue logic.

Scope:

- modify workflow runtime:
  - multi-node `BaseWorkflow` extension hooks;
- working `SubgraphWorkflow` contract;
  - node-level execution metadata;
  - typed interrupt/resume boundary;
- stable `thread_id`/`correlation_id` propagation;
- modify tool execution:
  - `ToolExecutionPolicy`;
  - retry policy;
  - timeout accounting;
  - idempotency key handling;
- audit records for tool calls;
- contract tests for success/retry/failure/idempotency;
- modify the registry/factory layer:
  - DI-friendly `WorkflowFactory`;
- clear lookup/duplicate registration errors;
- capability metadata for tools/workflows;
- fix the framework execution context:
  - task id;
  - node name;
  - actor;
  - correlation id;
  - metadata;
- update `docs/framework_extension_guide.md`, README, SAO and ADR/design note.

Demo update:

- release demo may not change in the first slice if public APIs do not change;
- after node-level events demo/smoke should check at least one graph-node event in task audit.

Definition of Done:

- a new tool/workflow/subgraph can be added with retry/idempotency/audit behavior without changing application services;
- existing retrieval/knowledge-indexing/authoring tests remain green;
- framework contract tests record lifecycle, errors and metadata propagation;
- backlog contains the current status of completed slices.

First slice done:

- added policy-aware `ToolExecutor`;
- backward compatibility of `ToolExecutor(registry).execute(...)` is preserved;
- `ToolContext` expanded `node_name`, `correlation_id`, `idempotency_key`;
- added `ToolExecutionPolicy`, `ToolExecutionRecord`, `ToolExecutionAuditSink`;
- added audit/idempotency/retry contract tests;
- parser missing-dependency tests moved from environment-dependent skip to monkeypatch-based check;
- full suite with Docker async e2e and OpenRouter external LLM enabled: `137 passed`.

Second slice done:

- added `WorkflowExecutionContext` for workflow node execution;
- added `WorkflowNodeSpec` as an extension hook for sequential multi-node workflows;
- `BaseWorkflow` compiles invoke/resume graphs from node specs;
- fallback runtime also executes node specs, maintaining behavior without LangGraph;
- `SubgraphWorkflow` received `subgraph_name`, `invoke_as_subgraph(...)` and parent context propagation;
- added contract tests for multi-node invoke/resume, fallback runtime and subgraph context.
- full suite with Docker async e2e and OpenRouter external LLM enabled: `140 passed`.

Third slice done:

- `BaseWorkflow` issues `WorkflowNodeEventRecord` for node `started/completed/failed`;
- added `WorkflowNodeEventSink` port;
- `TaskWorkflowNodeEventSink` maps workflow node events to the existing `task_events` read-model;
- external APIs have not changed: node events are available via `GET /api/v1/tasks/events` in `event_payload.event_kind=workflow_node`;
- retrieval and knowledge-indexing workflows are connected to the node event sink via application services;
- added unit/integration tests for explicit task events, workflow node events and API payload;
- regular suite without external flags: `141 passed, 2 skipped`.
- full suite with Docker async e2e and OpenRouter external LLM enabled: `143 passed`.

Fourth slice done:

- `WorkflowFactory` supports DI-friendly `register_builder(...)` and `build(..., **dependencies)`;
- backward compatibility of `register("key", WorkflowClass)` is preserved;
- added explicit `WorkflowRegistrationError` and `WorkflowNotRegisteredError`;
- duplicate registration is disabled by default, conscious replacement requires `replace=True`;
- workflow capability metadata is available via `metadata(key)`, discovery via `has(...)`/`list_workflows()`;
- updated framework extension guide, README, SAO and ADR-0040;
- full suite with Docker async e2e and OpenRouter external LLM enabled: `147 passed`.

Next increment:

- start Increment 27: Production Retrieval Fabric.

## Increment 27: Production Retrieval Fabric

Status: Done.

Goal: transfer retrieval from demo/in-memory mode to indexed corpus.

Scope:

- use framework runtime/tool ​​policies from Increment 26;
- implement pgvector-backed summary/detail retrievers;
- connect real TEI embedding gateway for indexing;
- connect real TEI rerank gateway to the authoring path;
- expand Retrieval MCP:
  - `search_summaries`;
  - `search_blocks`;
  - `lookup_source`;
- add retrieval quality gates:
  - low evidence count;
  - low confidence;
  - missing methodology/source refs;
  - unresolved gaps;
- add contract tests for retrieval adapters.

Demo update:

- release go/no-go must be able to be launched from the indexed corpus;
- file/dir mode remains bootstrap/demo mode;
- the report must clearly show confidence and unresolved gaps.

Definition of Done:

- evidence pack is built from Postgres/pgvector knowledge store;
- metadata filtering works via SQL/JSONB;
- authoring path uses rerank.

First slice done:

- Knowledge Indexing writes vector embeddings not only for `content_blocks`, but also for `section_summaries`;
- added `CanonicalSummaryVectorRetriever` on top of pgvector with `kind=knowledge_summary_embedding`;
- `build_retrieval_workflow(... knowledge_source="canonical" ...)` uses pgvector-backed summary/detail retrievers if `embedding_gateway` and `vector_store` are present;
- in-memory fallback for demo/bootstrap mode saved;
- added contract tests for summary retriever, summary embedding indexing and canonical workflow with indexed summary/detail layers;
- full suite with Docker async e2e and OpenRouter external LLM enabled: `149 passed`.

Second slice done:

- `TeiEmbeddingGateway` supports real TEI HTTP `/embed` endpoint via `TEI_EMBEDDING_URL` or `TEI_BASE_URL`;
- `TeiRerankGateway` supports real TEI HTTP `/rerank` endpoint via `TEI_RERANK_URL` or `TEI_BASE_URL`;
- local deterministic fallback is preserved, and fallback in case of a network error is enabled explicitly via `TEI_FALLBACK_ENABLED=true`;
- `ApiContainer` collects embedding/rerank gateways from env;
- `RetrievalApplicationService` accepts injected `rerank_gateway`, so the authoring path uses the same rerank adapter via the retrieval service;
- added unit tests for HTTP payload/parsing and fallback behavior;
- full suite with Docker async e2e and OpenRouter external LLM enabled: `153 passed`.

Third slice done:

- added `RetrievalQualityPolicy` for evidence quality gates;
- `EvidenceBuilder` fills `EvidencePack.unresolved_gaps` and `confidence_notes`;
- gates supported:
  - low evidence count;
  - low confidence;
- missing required document types, including `methodology`;
  - missing source refs;
- retrieval task details contain `quality_gate_status`, `unresolved_gaps`, `confidence_notes`;
- release readiness report shows confidence, retrieval quality gate and unresolved gaps;
- canonical retrieval smoke outputs `quality_gate_status`, `unresolved_gaps`, `confidence_notes`;
- added unit tests for policy gaps and report output;
- full suite with Docker async e2e and OpenRouter external LLM enabled: `155 passed`.

Fourth slice done:

- Retrieval MCP expanded indexed canonical tools:
  - `search_summaries`;
  - `search_blocks`;
  - `lookup_source`;
- `search_summaries` uses `CanonicalSummaryVectorRetriever` on top of existing `embedding_gateway` + `vector_store`;
- `search_blocks` uses `CanonicalVectorRetriever` on top of the same indexed corpus;
- `lookup_source` reads canonical document/block source mapping via `CanonicalDocumentApplicationService`;
- `build_evidence_pack` saved without changing the external contract;
- added typed MCP schemas and unit tests for metadata, summary/detail search, source lookup and backward compatibility;
- targeted MCP tests: `6 passed`.
- full suite with Docker async e2e and OpenRouter external LLM enabled: `159 passed`.

Fifth slice done:

- added operational smoke for Retrieval MCP indexed tools:
  - `backend/scripts/smoke_retrieval_mcp.py`;
  - `backend/scripts/smoke_retrieval_mcp.sh`;
  - `backend/scripts/smoke_retrieval_mcp.ps1`;
- smoke runs the path `canonical indexing -> search_summaries -> search_blocks -> lookup_source -> build_evidence_pack`;
- unit tests expanded to edge cases:
- tags filtering for `search_blocks`;
- doc-level lookup without `block_id`;
  - invalid `block_ref`;
  - missing `canonical_document_service`;
  - missing indexed dependencies;
- targeted MCP tests: `11 passed`.
- full suite with Docker async e2e and OpenRouter external LLM enabled: `164 passed`.

Sixth slice done:

- real Docker/Celery e2e extended to iterative HITL path;
- `backend/tests/e2e/test_fastapi_authoring_async_celery_e2e.py` now covers:
  - `start_async -> waiting_human -> approve -> completed`;
  - `start_async -> waiting_human(iteration=1) -> needs_changes -> waiting_human(iteration=2) -> approve -> completed`;
- e2e checks `GET /api/v1/tasks/{task_id}/hitl`, `POST /api/v1/tasks/{task_id}/hitl/submit`, the resulting artifact metadata and `GET /api/v1/hitl/actions`;
- targeted Docker/Celery e2e: `2 passed`;
- full suite with Docker async e2e and OpenRouter external LLM enabled: `165 passed`.

Next increment:

- start `Increment 28: Domain Authoring Extraction`.

## Increment 28: Domain Authoring Extraction

Status: Done.

Goal: move authoring from a large application service to a separate domain layer.

Scope:

- add `packages/domain_authoring`;
- highlight:
  - `TemplateCompiler`;
  - `SectionContractBuilder`;
  - `OutlinePlanner`;
  - `SectionAuthoringWorkflow`;
  - `SectionReviewService`;
  - `DocumentAssembler`;
  - `ArtifactExporter`;
- describe section packet and section digest schemas;
- add outline approval HITL point;
- maintain compatibility of existing APIs:
  - `authoring/start`;
  - `authoring/start_async`;
  - `tasks/{task_id}/artifact`;
  - `tasks/{task_id}/hitl`;
  - `hitl/submit`.

First slice done:

- added package `backend/packages/domain_authoring`;
- minimal domain services are highlighted:
  - `OutlinePlanner`;
  - `SectionReviewService`;
  - `DocumentAssembler`;
- `AuthoringApplicationService` integrates these services through dependency injection with default implementations;
- external authoring API and HITL contracts have not changed;
- added ADR-0045 and unit tests for new domain services;
- targeted authoring tests: `11 passed`.

Second slice done:

- added `ResearchSummaryBuilder` and `WriterDraftService` to `domain_authoring`;
- `AuthoringApplicationService` no longer contains research summary formatting, deterministic draft formatting and LLM prompt composition;
- the orchestration of choosing `draft_strategy`, external LLM gateway and fallback policy is saved in the application layer;
- added ADR-0046 and expanded unit tests domain authoring.

Third slice done:

- `OutlinePlanner` now covers source-ref mapping for section traceability;
- `SectionReviewService` is used for mass update of section review status;
- `WriterDraftService` formats human feedback during HITL rewrite;
- `AuthoringApplicationService` continues orchestration, but no longer contains these stateless helper methods as independent domain logic;
- added ADR-0047 and expanded authoring unit tests.

Fourth slice done:

- added typed schemas `SectionContract` and `SectionPacket`;
- added `SectionContractBuilder` to `domain_authoring`;
- `AuthoringApplicationService` builds section contracts from evidence/review context and stores them in state + artifact metadata;
- public authoring/HITL APIs have not been changed;
- added ADR-0048 and unit tests for section contracts/packets.

Fifth slice done:

- added typed `SectionArtifact` and `SectionAuthoringService`;
- section packets are now actually used for deterministic section draft/digest generation;
- `AuthoringTaskState` and artifact metadata save `section_artifacts`;
- the final external API and assembled document have been saved without changes for now;
- added ADR-0049 and expanded unit tests.

Sixth slice done:

- added `domain_docs.TemplateCompiler`;
- `SectionContractBuilder` can now build contracts from `TemplateSpec`;
- `AuthoringApplicationService` supports template-aware authoring via `task_context.template_id` and `task_context.template_payload`;
- default path `release_readiness` is preserved for backward compatibility;
- added ADR-0050 and unit tests for custom templates.

Seventh slice done:

- `DocumentAssembler` now supports template-aware deterministic assembly;
- the final document can be assembled from `TemplateSpec` and `section_artifacts`, and not only from release-readiness-specific layout;
- the old fallback path is preserved for backward compatibility;
- added ADR-0051 and expanded unit tests.

Eighth slice done:

- added baseline `TemplateCatalog` and `InMemoryTemplateCatalog`;
- `TemplateSpec` expanded with `assembly_rules` field;
- `TemplateCompiler` compiles and normalizes assembly rules;
- `DocumentAssembler` uses assembly rules for section order;
- `DocumentAssembler` now also enforces `include_writer_draft` and `include_traceability` from assembly rules;
- added baseline `ArtifactExporter` for `markdown|json` export without changing the external authoring API;
- `artifact_format=json` now returns structured artifact payload for template-aware authoring;
- added ADR-0053 and unit/integration tests;
- targeted authoring/export tests: `61 passed`;
- full suite with Docker async e2e and OpenRouter external LLM enabled: `186 passed`.

Ninth slice done:

- `hitl_required=true` now first opens outline approval pause before section authoring and exposes outline snapshot via HITL status;
- HITL status read-model expanded with `phase` and `outline` fields;
- approve path keeps the existing completion flow compatible, and outline `needs_changes` moves the task to the next HITL iteration without section authoring;
- added ADR-0054 and unit/integration tests;
- targeted outline authoring tests: `64 passed`;
- full suite with Docker async e2e and OpenRouter external LLM enabled: `189 passed`.

Tenth slice done:

- added baseline `SectionAuthoringWorkflow` on top of existing `SectionAuthoringService` and `SectionReviewService`;
- workflow uses typed `SectionAuthoringState` and multi-node path `write_section -> review_section -> finalize_section`;
- `AuthoringApplicationService` now builds `section_artifacts` through the workflow boundary, without changing external APIs;
- resume path supports section-level human feedback as a baseline rewrite hook;
- added ADR-0055 and unit tests for invoke/resume workflow path;
- targeted section workflow tests: `66 passed`;
- full suite with Docker async e2e and OpenRouter external LLM enabled: `191 passed`.

Eleventh slice done:

- added baseline `DocumentAssemblyWorkflow` on top of existing `DocumentAssembler` and `ArtifactExporter`;
- workflow uses typed `AssemblyWorkflowState` and multi-node path `assemble_document -> export_artifact -> finalize_document`;
- `AuthoringApplicationService` now conducts final assembly/export through the workflow boundary, without changing external APIs;
- `build_domain_authoring_services()` now also returns `DocumentAssemblyWorkflow` as part of the domain authoring wiring;
- added ADR-0056 and unit tests for document assembly workflow and injected workflow path;
- targeted assembly workflow tests: `34 passed`;
- full suite with Docker async e2e and OpenRouter external LLM enabled: `193 passed`.

Twelfth slice done:

- added persisted template library: `TemplateLibraryApplicationService`, `PostgresTemplateStore` and migration `0010_document_templates.sql`;
- `TemplateCatalog` and `SectionContractBuilder` now support `template_version`, maintaining the inline priority of `template_payload`;
- `AuthoringApplicationService` can now resolve templates from the persisted library by `task_context.template_id/template_version`;
- `ApiContainer` wires template library in the authoring path without changing external APIs;
- added unit/integration tests for fallback store, versioned template resolution and authoring via persisted template library;
- targeted template library tests: `89 passed`;
- full suite with Docker async e2e and OpenRouter external LLM enabled: `199 passed`.

Thirteenth slice done:

- added public template management API boundary: `PUT /api/v1/templates/{template_id}`, `GET /api/v1/templates/{template_id}`, `GET /api/v1/templates`;
- added typed API contracts for upsert/get/list reusable templates;
- `TemplateLibraryApplicationService` received a compile helper for the API path, without bypassing the existing `TemplateCompiler`;
- the persisted template library is now available not only to the internal authoring path, but also as a managed service boundary;
- added integration tests for template API flow and 404 path;
- targeted template API tests: `54 passed`;
- full suite with Docker async e2e and OpenRouter external LLM enabled: `202 passed`.

Fourteenth slice done:

- added Template Library MCP boundary: `FastMcpTemplateLibraryService`, `apps/mcp_template_library/main.py` and typed MCP schemas `schemas.mcp.template_library`;
- MCP tools `upsert_template/get_template/list_templates` reuse the existing `TemplateLibraryApplicationService` and `TemplateCompiler`, without a separate template-specific architecture;
- added runtime/smoke scripts `run_template_library_mcp.sh/.ps1` and `smoke_template_library_mcp.sh/.ps1`;
- added unit tests for Template Library MCP metadata, upsert/get/list flow and missing-template error mapping;
- added ADR-0059 and updated README/SAO/runbook for the new MCP boundary;
- targeted template MCP/API tests: `40 passed`;
- full suite with Docker async e2e and OpenRouter external LLM enabled: `205 passed`.

Fifteenth slice done:

- added baseline template governance status `draft|published` for persisted template library;
- added `publish_template` path to `TemplateLibraryApplicationService`, HTTP API and Template Library MCP;
- authoring without an explicit `template_version` will now resolve the latest `published` template version, maintaining the priority of inline `template_payload` and explicit version lookup;
- added migration `0011_template_status_governance.sql` and extended fallback/PostgreSQL template store read models;
- added unit/integration tests for publish flow, published-only resolution and authoring default behavior;
- added ADR-0060 and updated README/SAO/runbook/scripts docs;
- targeted governance tests: `80 passed`;
- local suite without external flags: `208 passed, 3 skipped`.

Sixteenth slice done:

- `TemplateCompiler` and `SectionContractBuilder` received richer template assembly policy baseline:
- section-level fields `required`, `include_if_has_evidence`, `include_if_review_status`, `section_group`;
- assembly-level fields `include_sections`, `exclude_sections`, `allowed_section_groups`;
- `DocumentAssembler` now applies these richer rules when selecting summary sections and filtering section traceability;
- `ArtifactExporter` reuses the same deterministic section selection path, so `markdown` and `json` no longer differ in the composition of sections;
- `OutlinePlanner` and `AuthoringApplicationService` now build template-aware `section_traceability` for custom templates, not just for release-readiness default path;
- added ADR-0061 and expanded unit tests for compiler normalization, template-aware traceability, conditional section inclusion and JSON consistency export;
- targeted authoring/domain tests: `44 passed`;
- full suite with Docker async e2e and OpenRouter external LLM enabled: `216 passed`.

Seventeenth slice done:

- template library publish semantics have become exclusive: for one `template_id` only one active `published` version is now allowed;
- `publish_template` automatically demote the previous published version back to `draft` in the fallback and PostgreSQL store path;
- HTTP API, MCP and authoring default published-resolution continue to work through the same `TemplateLibraryApplicationService` without changing public contracts;
- added ADR-0062 and expanded unit/integration tests for publish demotion semantics;
- targeted governance/API/MCP tests: `65 passed`;
- full suite with Docker async e2e and OpenRouter external LLM enabled: `219 passed`.

Eighteenth slice done:

- template governance is closed to production-compatible lifecycle: `draft|published|deprecated|archived`;
- added explicit `set_template_status` path to `TemplateLibraryApplicationService`, HTTP API (`POST /api/v1/templates/{template_id}/status`) and Template Library MCP;
- fallback/PostgreSQL template stores now preserve governance metadata/history in `metadata.governance` and continue to support exclusive published invariant;
- authoring default resolution now requires a published template, explicit archived version is prohibited, explicit deprecated version remains available;
- smoke/unit/integration tests for lifecycle transitions, archived guardrails and MCP governance path have been expanded;
- targeted governance/authoring/API/MCP tests: `122 passed`;
- full suite with Docker async e2e and OpenRouter external LLM enabled: `232 passed`.

Demo update:

- generated artifact must be assembled section-by-section;
- traceability must be maintained at the section and source refs level;
- HITL flow should be able to send sections for rework.

Definition of Done:

- application layer only orchestrates use cases;
- authoring domain testable separately from FastAPI;
- the final document is assembled into a deterministic assembly.

Next increment:

- start `Increment 29: Unified Execution Plane + Observability`.

## Increment 29: Unified Execution Plane + Observability

Status: Done.

Goal: make async execution and observability common to all long-running workflows.

Scope:

- generalize dispatcher beyond authoring:
  - ingestion;
  - retrieval;
  - authoring;
  - quality evaluation;
- add retry/timeout/idempotency policy;
- add node-level task events;
- add correlation IDs;
- add structured JSON logging;
- add periodic aggregates:
  - task events day/week;
  - HITL SLA;
  - decision mix;
  - reviewer load.

Demo update:

- async smoke should check task events at the graph nodes level;
- HITL demo should check SLA/read-model aggregates.

Definition of Done:

- all long-running workflows can be performed through a single execution plane;
- audit/read-model layer is suitable for dashboard;
- production troubleshooting is possible without reading raw checkpoint payload.

First slice done:

- async execution plane expanded from authoring to `knowledge_indexing` via existing dispatcher/Celery wiring, without a new parallel architecture;
- added `KnowledgeIndexingAsyncDispatcher`, `InlineKnowledgeIndexingAsyncDispatcher`, `CeleryKnowledgeIndexingAsyncDispatcher`;
- `KnowledgeIndexingApplicationService` supports `start_task_async(...)` and `run_existing_task(...)`;
- added endpoint `POST /api/v1/tasks/knowledge-indexing/start_async`;
- the worker app received task `run_knowledge_indexing_task`, a separate queue `knowledge-indexing` and env `APP_CELERY_INDEXING_QUEUE`;
- worker dispatcher normalizes host `source_paths` in `/workspace/...` for docker-compose bind mount;
- `Dockerfile.worker` has been updated to parser-compatible dependency set (`python-docx`, `PyMuPDF`) so that async indexing covers `.docx/.pdf` fixtures as well as sync path;
- added unit/integration/e2e tests for async indexing path and Celery dispatcher path normalization.

Second slice done:

- retrieval lifecycle transferred to the same async execution plane without breaking change for sync endpoint `POST /api/v1/tasks/retrieval/start`;
- added `RetrievalAsyncDispatcher`, `InlineRetrievalAsyncDispatcher`, `CeleryRetrievalAsyncDispatcher`;
- `RetrievalApplicationService` supports `start_async(...)` and `run_existing_task(...)`;
- added endpoint `POST /api/v1/tasks/retrieval/start_async`;
- the worker app received a task `run_retrieval_task`, a separate queue `retrieval` and env `APP_CELERY_RETRIEVAL_QUEUE`;
- docker-compose async worker now listens to the `authoring`, `knowledge-indexing`, `retrieval` queues;
- added unit/integration/e2e tests for async retrieval path;
- added manual acceptance scripts `smoke_retrieval_async_api.sh/.py` and `demo_release_go_no_go_async_case.sh/.py`;
- targeted tests: `71 passed`;
- targeted Docker/Celery e2e: `4 passed`;
- full suite with Docker async e2e and OpenRouter external LLM enabled: `246 passed`.

Third slice done:

- task lifecycle details expanded execution metadata: `correlation_id`, `async_provider`, `queue_name`, `queued_at`, `started_at`, `completed_at|failed_at`, `queue_wait_ms`;
- added read-model endpoint `GET /api/v1/tasks/observability/summary` with current-state counts and latency aggregates by `task_type`;
- async smoke/demo scripts now explicitly show execution trace and observability aggregates for retrieval/indexing/authoring paths;
- async release readiness report shows queue/dispatch/correlation metadata;
- added ADR `0066-task-observability-summary-and-execution-metadata.md`;
- targeted tests: `76 passed`;
- full suite with Docker async e2e and OpenRouter external LLM enabled: `246 passed`.

Fourth slice done:

- added shared helper `infra.logging.runtime` for one-line structured JSON logs on stdlib logging;
- FastAPI endpoints, Celery worker tasks and `AuthoringApplicationService` now issue structured runtime events with `task_id`, `correlation_id`, `dispatch_id`, `queue_name`, `decision`, `iteration`;
- `HitlActionStore` has been expanded with `summarize_actions(...)` aggregates, and the API has received an endpoint `GET /api/v1/hitl/observability/summary`;
- async authoring smoke shows reviewer/HITL observability summary next to the existing task observability summary;
- added ADR `0067-structured-logging-and-hitl-observability-summary.md`;
- targeted tests: `75 passed`;
- full suite with Docker async e2e and OpenRouter external LLM enabled: `252 passed`.

Increment closed:

- full gate with Docker async e2e and OpenRouter external LLM enabled: `252 passed`.

## Increment 30: MCP + Production Boundary

Status: In Progress.

Goal: bring the service boundary to a production-like state.

Scope:

- add Review/Approval MCP;
- add Configuration Library MCP skeleton;
- unify MCP policies:
  - tool naming;
  - input/output validation;
  - audit payload;
  - error mapping;
  - operation scope;
- add basic auth/RBAC boundaries for sensitive endpoints;
- prepare production runbook:
  - deploy;
  - migrate;
  - smoke;
  - backup;
  - restore;
  - rollback.

Demo update:

- the release scenario must go through Repository MCP, Retrieval MCP, Artifact Writer MCP and Review/Approval MCP;
- report should save MCP operation refs in audit/metadata.

Definition of Done:

- MCP layer covers the minimum target set;
- operational runbook is sufficient for stage/prod rehearsal;
- service contracts do not require knowledge of internal state payload.

First slice done:

- added Review/Approval MCP boundary:
  - `backend/apps/mcp_review_approval/main.py`;
  - `backend/packages/infra/fastmcp/review_approval_service.py`;
  - `backend/packages/schemas/mcp/review_approval.py`;
- MCP tools cover reviewer/HITL manual operations without access to internal state payload:
  - `get_hitl_status`;
  - `list_hitl_actions`;
  - `submit_hitl_review`;
  - `get_hitl_observability_summary`;
- boundary reuses existing `AuthoringApplicationService`, `PostgresHitlActionStore` and existing async dispatcher plane, without a new review-specific architecture;
- added operational scripts `run_review_approval_mcp.sh/.ps1` and `smoke_review_approval_mcp.sh/.ps1`;
- added ADR `0068-review-approval-mcp-boundary.md`;
- targeted MCP/authoring/API tests: `78 passed`;
- manual smoke Review/Approval MCP: passed;
- full suite with Docker async e2e and OpenRouter external LLM enabled: `259 passed`.

Second slice done:

- added Configuration Library MCP skeleton:
  - `backend/apps/mcp_configuration_library/main.py`;
  - `backend/packages/application/configuration_library_service.py`;
  - `backend/packages/infra/postgres/configuration_store.py`;
  - `backend/packages/infra/fastmcp/configuration_library_service.py`;
  - `backend/packages/schemas/mcp/configuration_library.py`;
- MCP tools cover persisted configuration artifacts without knowledge of internal storage payload:
  - `upsert_config`;
  - `get_config`;
  - `list_configs`;
  - `find_similar_configs`;
  - `compare_configs`;
- boundary uses PostgreSQL/fallback persistence pattern through a new table `app.configuration_library` and migration `backend/migrations/0012_configuration_library.sql`;
- similarity path is implemented as deterministic heuristic on top of existing persisted config records, and compare path as deterministic diff based on flattened JSON keys, without a separate vector/runtime stack;
- added operational scripts `run_configuration_library_mcp.sh/.ps1` and `smoke_configuration_library_mcp.sh/.ps1`;
- added ADR `0069-configuration-library-mcp-skeleton.md`;
- targeted configuration MCP/persistence tests: `28 passed`;
- manual smoke Configuration Library MCP: passed;
- full suite with Docker async e2e and OpenRouter external LLM enabled: `265 passed`.

Third slice done:

- `BaseFastMcpService` received a unified MCP policy layer with validated `tool_names`, `service_scope`, `operation_scopes`, `policy_version`, input/output validation markers and standard `audit_payload_fields`;
- all current FastMCP services (`retrieval`, `repository`, `artifact-writer`, `template-library`, `review-approval`, `configuration-library`) have been transferred to a common `_register_toolset(...)` and a single error mapping helper `_operation_error(...)`;
- `build_evidence_pack` is fixed as `operation_scope=action`, and read/write tools now receive consistent scope metadata automatically;
- added ADR `0070-unified-fastmcp-service-policies.md`;
- targeted MCP/framework tests: `53 passed`;
- full suite with Docker async e2e and OpenRouter external LLM enabled: `268 passed`.

Fourth slice done:

- added basic auth/RBAC boundaries for sensitive API/MCP operations via shared `framework.security.rbac` policy layer;
- FastAPI template governance endpoints (`upsert/publish/set status`) and authoring HITL submit endpoint now support header-based actor context (`X-Actor-Id`, `X-Actor-Roles`) and with `APP_AUTH_ENABLED=true` return `401/403` for unauthorized access;
- `BaseFastMcpService` extended auth-aware metadata (`auth_policy`, `tool_required_roles`) and unified `_authorize_tool(...)` helper;
- sensitive FastMCP tools now require explicit roles in typed payloads: `template_admin`, `reviewer`, `config_admin`, `artifact_writer`, `repository_writer`;
- when auth is disabled (`APP_AUTH_ENABLED=false`), backward compatibility is maintained for current smoke/demo paths;
- added ADR `0071-rbac-boundaries-for-sensitive-api-and-mcp-operations.md`;
- targeted auth/MCP/API tests: `101 passed`;
- full suite with Docker async e2e and OpenRouter external LLM enabled: `278 passed`.

Fifth slice done:

- added production runbook `docs/production_runbook.md` for stage/prod rehearsal:
  - deploy;
  - migrate;
  - FastAPI smoke;
  - async/Celery smoke;
  - MCP smoke;
  - RBAC rehearsal;
  - backup/restore;
  - rollback;
  - release gate;
- added handoff checklist `docs/handoff/2026-04-27_increment_30_production_boundary_handoff.md`;
- added contract tests `backend/tests/unit/test_production_runbook_contracts.py`, which check that the runbook refers to existing scripts and covers the required operational sections/env flags;
- Increment 30 production boundary now has a documented stage/prod rehearsal path before moving to Knowledge Factory Hardening;
- targeted runbook contract tests: `3 passed`;
- full suite with Docker async e2e and OpenRouter external LLM enabled: `281 passed`.

## Increment 31: Knowledge Factory Hardening

Goal: to bring canonical ingestion to the requirements of technical specifications for formats, quality gates and production parsing behavior.

First slice done:

- added typed parser quality read-model baseline for canonical ingestion:
- `ParserQualityIssue` and `ParserQualitySummary` in `schemas.documents`;
- `CanonicalDocument.parser_quality` now stores parser family, extraction mode, page/block/heading/list/table counts and typed issues;
- `CanonicalDocumentParser` now populates structured diagnostics for current `.md/.txt/.json/.docx/.pdf` adapters:
- markdown/text record headings/lists counts;
- DOCX marks detected tables via `docx_tables_detected` and `table_extraction_not_implemented`;
- PDF without extractable text is additionally marked as `ocr_required`;
- `KnowledgeIndexingApplicationService` task details and aggregated `quality_summary` have been expanded with parser diagnostics fields:
- `parser_quality` for each `doc_id`;
  - `parser_families`, `extraction_modes`, `parser_issues_total`, `documents_with_tables`, `documents_needing_ocr`;
- retrieval/reporting/read-model path now also returns `parser_quality` metadata for canonical sources;
- smoke/report path updated:
- `smoke_knowledge_indexing.sh/.ps1` and `smoke_knowledge_indexing_api.sh/.ps1` output parser diagnostics;
- `release_readiness_report.md` shows parser diagnostics inside `Canonical Quality Summary`;
- added ADR `0072-canonical-parser-quality-read-model-baseline.md`;
- targeted parser/indexing/retrieval/report tests: `78 passed`.

Second slice done:

- added OCR preflight + scanned PDF fallback path for canonical parser:
- new adapter boundary `domain_docs.parsing.ocr.PdfOcrGateway`;
- infra adapters `SidecarPdfOcrGateway` and optional `OcrmypdfGateway`;
- `CanonicalDocumentParser` now tries OCR recovery with `pdf_no_extractable_text` and writes `ocr_applied|ocr_provider:*|ocr_not_available|ocr_text_not_recovered` quality flags;
- API/container wiring supports env-driven OCR runtime:
  - `APP_OCR_ENABLED=true|false`;
  - `APP_OCR_PROVIDER=sidecar|ocrmypdf`;
- optional `APP_OCR_LANGUAGE`, `APP_OCR_TIMEOUT_SEC` for real CLI path;
- demo input extended with OCR script:
  - `07_scanned_signoff.pdf`;
- `07_scanned_signoff.pdf.ocr.txt` as deterministic OCR sidecar fixture;
- smoke/report/tests now show OCR path in Knowledge Indexing details and canonical quality summary;
- targeted OCR/parser/indexing/API/report tests: `78 passed`.

Third slice done:

- DOCX parser hardening path:
- `CanonicalDocumentParser` now extracts `CanonicalTable` into `extracted_tables`;
- DOCX tables rows become canonical `table_row` blocks and end up in the indexing/retrieval corpus;
- numbered/list paragraphs are normalized as `bullet` blocks;
- appendix-like headings are marked via `appendix_section_detected`;
- demo DOCX fixture `05_release_notes.docx` extended with real structures:
  - numbered deployment checklist;
- approval matrix table with statuses `PENDING/READY/APPROVED`;
- appendix section with rollback contacts;
- tests and API smoke now check that demo DOCX actually returns `extracted_tables` and `table_row` blocks, and not just the quality flag;

Fourth slice done:

- fixed parity bug between direct shell smoke and API/container indexing path:
- `backend/scripts/smoke_knowledge_indexing.py` now uses `ApiContainer().knowledge_indexing_service`, rather than the manually compiled `KnowledgeIndexingApplicationService` without OCR-aware parser;
- direct smoke now matches the smoke API by env-driven OCR runtime and correctly shows `ocr_applied`/`ocr_recovered_doc_ids` for scanned PDF fixture;
- added regression test `backend/tests/unit/test_smoke_knowledge_indexing_script.py`, which captures container-managed behavior for direct smoke path;
- manual smoke docs and README clarified: with `APP_OCR_ENABLED=true` and `APP_OCR_PROVIDER=sidecar` direct smoke should no longer return `ocr_not_available` for `07_scanned_signoff.pdf`;
- targeted tests + direct/API smoke verification + full suite with Docker async e2e and OpenRouter external LLM enabled: planned after slice finalization.

Fifth slice done:

- retrieval/source mapping enriched with table-aware provenance for canonical `table_row` blocks without new retrieval architecture;
- canonical indexing vector metadata and canonical dataset path now save/give:
  - `source_kind=table_row`;
  - `table_id`, `table_title`, `table_columns`;
  - `row_index`, `row_values`;
  - `section_title`;
- `FastMcpRetrievalService.lookup_source` now returns typed provenance and typed table payload for table-backed evidence;
- `release_readiness_report` and Retrieval MCP smoke can now clearly show that the evidence came from the approval matrix row, and not from the abstract paragraph block;
- added ADR `0074-table-aware-canonical-retrieval-provenance.md`;
- targeted provenance/retrieval/report tests: `18 passed`.

Sixth slice done:

- canonical parser baseline extended with support for `.xlsx` via `openpyxl`;
- workbook sheets now become structural sections, sheet tables are included in `extracted_tables`, and sheet rows are indexed as canonical `table_row` blocks;
- binary demo input expanded with real fixture `08_release_tracker.xlsx`;
- indexing/API tests and parser demo tests now check that XLSX goes through the same canonical/indexing path as DOCX/PDF/JSON;
- added ADR `0075-xlsx-parser-baseline-for-canonical-ingestion.md`;
- targeted parser/indexing/API tests: `70 passed`;
- full suite with Docker async e2e and OpenRouter external LLM enabled: `296 passed`.

Seventh slice done:

- added version-aware canonical document policy without breaking the current latest-by-doc_id behavior;
- `PostgresCanonicalDocumentStore` now stores the latest read-model separately from historical versions:
  - latest tables: `app.canonical_documents`, `app.knowledge_blocks`;
  - history tables: `app.canonical_document_versions`, `app.knowledge_block_versions`;
- `CanonicalDocumentApplicationService` supports explicit version lookup and `list_versions(...)`;
- Knowledge Indexing API/request contracts and smoke scripts support `document_version`;
- re-index semantics clear latest vector entries by `doc_id`, but historical canonical versions remain available for explicit lookup/source mapping;
- Retrieval MCP `lookup_source` now accepts optional `version` and can resolve historical `block_ref`;
- targeted canonical-version-policy tests: `104 passed`.

Eighth slice done:

- quality gates canonical indexing have been transferred to a separate production policy layer:
- added `domain_docs.indexing.quality_policy.KnowledgeIndexingQualityPolicy`;
- policy returns typed per-document decisions (`accepted/rejected`) and aggregate decision (`gate_status`, `blocking_flags`, `warning_flags`);
- `KnowledgeIndexingApplicationService` now applies policy before persistence workflow:
- rejected documents are not saved in the canonical store and are not indexed in `app.embeddings`;
- accepted documents follow the same `KnowledgeIndexingWorkflow` path;
- OCR-recovered scanned PDF (`pdf_no_extractable_text` + `ocr_applied`) remains the default warning-path;
- `ApiContainer` collects policy from env (`APP_INDEXING_QUALITY_*`) without changing public APIs;
- `quality_summary` in task details/state payload expanded policy metadata:
  - `policy_name`;
  - `accepted_documents_total` / `rejected_documents_total`;
  - `accepted_doc_ids` / `rejected_doc_ids`;
  - `blocking_flags` / `warning_flags`;
- added ADR `0077-production-indexing-quality-policy-layer.md`;
- targeted quality/indexing tests: `18 passed` (`13 + 5`);
- full suite with Docker async e2e and OpenRouter external LLM enabled: `301 passed`.

Ninth slice done:

- canonical parser baseline extended with support for `.pptx` via `python-pptx`;
- slides now become structural sections, and presentation content is indexed as canonical blocks:
  - `slide_title`;
  - `paragraph`;
  - `bullet`;
  - `note` (speaker notes);
- parser diagnostics/quality flags extended for presentation path:
  - `pptx_slides_detected`;
  - `pptx_notes_detected`;
- binary demo input expanded with new fixture `09_release_briefing.pptx`;
- `build_binary_demo_documents.py` now generates `.pptx` along with `.docx/.pdf/.xlsx`;
- demo/smoke expectations and API tests updated to `documents_total=9` and `file_types` from `pptx`;
- worker image dependency set extended `python-pptx` for async indexing parity;
- added ADR `0078-pptx-parser-baseline-for-canonical-ingestion.md`;
- targeted parser/indexing/API/e2e tests: `26 passed`;
- full suite with Docker async e2e and OpenRouter external LLM enabled: `299 passed`.

Tenth slice done:

- added PDF page provenance baseline for canonical retrieval/report path:
  - `source_kind=page_block`;
  - `page_number`;
  - `layout_source`;
  - `bbox` (best-effort);
- fixed numbering of PDF block ids on global-per-document path:
- multi-page PDFs no longer create `B-1` collisions between pages;
- `structure_tree.block_ids` is now consistent with the resulting `content_blocks`;
- canonical dataset loader and pgvector retriever metadata mapping now save page provenance in `RetrievedBlock.metadata`;
- Retrieval MCP `lookup_source` source provenance expanded with page-level fields without breaking existing payload changes;
- release readiness report `Canonical Source Mapping` now shows `pages=...` and `layout_sources=...` for PDF evidence;
- added ADR `0079-pdf-page-provenance-baseline-for-canonical-retrieval.md`;
- targeted parser/retrieval/report tests: `36 passed` + cross-check set `61 passed`;
- full suite with Docker async e2e and OpenRouter external LLM enabled: `303 passed`.

Eleventh slice done:

- added richer PDF layout semantics baseline (v2) without changing public APIs:
- `reading_order_index` for page blocks (best-effort reading order);
- `layout_kind=paragraph|table_like` via lightweight layout heuristics;
- parser quality flag `pdf_table_like_blocks_detected` if there are table-like blocks;
- OCR fallback path also now fills `reading_order_index` and `layout_kind`;
- canonical dataset loader, pgvector metadata mapping and MCP `lookup_source` source provenance now forward:
  - `reading_order_index`;
  - `layout_kind`;
- release readiness report `Canonical Source Mapping` now shows `layout_kinds=...` for PDF evidence;
- added ADR `0080-pdf-reading-order-and-layout-kind-baseline.md`;
- targeted parser/retrieval/report tests: `37 passed` + cross-check set `60 passed`;
- full suite with Docker async e2e and OpenRouter external LLM enabled: `304 passed`.

Twelfth slice done:

- added PDF deep table extraction baseline for canonical ingestion:
- table-like PDF blocks are now materialized in `extracted_tables` and canonical `table_row` blocks;
- `table_id` is formed as `PDF-T-*`, rows receive `row_index` and row-wise metadata via the existing tabular builder;
- table rows from PDF save provenance metadata:
  - `source_kind=table_row`;
  - `page_number`, `reading_order_index`, `layout_kind`, `layout_source`, `bbox`;
- parser quality added with the `pdf_tables_extracted` flag;
- existing retrieval path reused without new architecture:
  - canonical dataset loader;
  - pgvector metadata mapping;
  - MCP `lookup_source`;
  - release report source mapping;
- added ADR `0081-pdf-table-extraction-baseline-for-canonical-ingestion.md`;
- targeted parser/retrieval/report/indexing tests: `44 passed` + cross-check set `54 passed`;
- full suite with Docker async e2e and OpenRouter external LLM enabled: `304 passed`.

Thirteenth slice done:

- PDF table extraction hardening expanded with form-like scenarios and demo check:
- parser recognizes form-like key/value blocks as tabular extraction path;
- for form-like extraction added quality flag `pdf_form_like_blocks_detected`;
- table metadata and `table_row` metadata contain `pdf_table_kind=form_like|pipe_table|spaced_table`;
- demo fixture `06_audit_summary.pdf` expanded:
  - complex table-like release controls;
  - form-like release gate block;
- allows you to manually check the extraction of `extracted_tables` and `table_row` from PDF in smoke/demo;
- tests updated to demo + parser hardening assertions:
- `pdf_tables_extracted` + `pdf_form_like_blocks_detected` is checked;
- presence of `table_row` blocks and `pdf_table_kind=form_like` is checked;
- added ADR `0082-pdf-form-like-extraction-and-demo-fixture-hardening.md`;
- targeted parser/indexing/demo tests: `78 passed`;
- targeted retrieval/report tests: `20 passed`;
- full suite with Docker async e2e and OpenRouter external LLM enabled: `305 passed`.

Fourteenth slice done:

- added PDF extraction coverage/partial-failure quality gates:
  - `pdf_table_candidates_total`;
  - `pdf_table_candidates_extracted`;
  - `pdf_table_rows_extracted`;
  - `pdf_table_rows_failed`;
  - `pdf_table_coverage_percent`;
- introduced quality flag `pdf_table_extraction_partial` for cases of partial extraction of table-like blocks;
- `parser_quality.issues` for `pdf_tables_extracted` and `pdf_table_extraction_partial` now returns coverage/rows metadata;
- indexing aggregate quality summary expanded with fields:
  - `documents_with_pdf_table_partial`;
  - `documents_with_pdf_form_like`;
- integration tests updated to check PDF table/form extraction in demo indexing path;
- added ADR `0083-pdf-extraction-coverage-and-partial-failure-gates.md`;
- targeted parser/retrieval/indexing/integration tests: `99 passed`;
- full suite with Docker async e2e and OpenRouter external LLM enabled: `306 passed`.

Fifteenth slice done:

- added PDF form-confidence baseline for canonical parser diagnostics:
  - `key_value_pairs_total`;
  - `key_value_pairs_extracted`;
  - `field_fill_rate_percent`;
  - `form_confidence_score`;
- `parser_quality.issues` for `pdf_form_like_blocks_detected` now returns form-confidence metadata;
- `KnowledgeIndexingQualityPolicy` expanded with form confidence threshold:
- env ​​`APP_INDEXING_QUALITY_FORM_CONFIDENCE_MIN_SCORE` enables threshold (0..100, `0` = disabled);
- when the score is below the threshold policy adds a synthetic flag `pdf_form_confidence_low`;
- env ​​`APP_INDEXING_QUALITY_FORM_CONFIDENCE_LOW_BLOCKING=true|false` enables fail-fast blocking or warning-only mode;
- indexing aggregate quality summary expanded:
  - `documents_with_pdf_form_confidence_low`;
  - `form_confidence_min_score`;
  - `pdf_form_confidence_by_doc`;
- report/smoke path updated for form-confidence counters in `Canonical Quality Summary`;
- added ADR `0084-pdf-form-confidence-policy-gate.md`;
- targeted parser/policy/indexing/report/integration tests: `85 passed`;
- full suite with Docker async e2e and OpenRouter external LLM enabled: `309 passed`.

Sixteenth slice done:

- enhanced PDF form-like parser for production layout edge-cases:
- support for keys with spaces/hyphens;
- support for multi-line continuation values;
- added rotated-layout baseline without changing public APIs:
- `rotated_text=true|false` in metadata page/table blocks;
  - parser quality flag `pdf_rotated_layout_detected`;
  - diagnostics metadata: `rotated_table_candidates_total`, `rotated_table_candidates_extracted`;
- demo fixture `06_audit_summary.pdf` updated:
  - multi-line form value;
- rotated form-like line for manual smoke/demo checking;
- tests expanded to multi-line form extraction and rotated-layout detection;
- added ADR `0085-pdf-multiline-form-and-rotated-layout-hardening.md`;
- targeted parser/indexing/integration tests: `87 passed`;
- full suite with Docker async e2e and OpenRouter external LLM enabled: `311 passed`.

Seventeenth slice done:

- added OCR confidence calibration baseline for scanned PDF path:
- parser issue `ocr_applied` now returns diagnostics metadata:
    - `ocr_blocks_total`;
    - `ocr_words_total`;
    - `ocr_weird_char_ratio_percent`;
    - `ocr_confidence_score`;
- `KnowledgeIndexingQualityPolicy` expanded with OCR confidence threshold policy:
- env ​​`APP_INDEXING_QUALITY_OCR_CONFIDENCE_MIN_SCORE` includes threshold (0..100);
- when the score is below the threshold policy adds a synthetic flag `ocr_confidence_low`;
- env ​​`APP_INDEXING_QUALITY_OCR_CONFIDENCE_LOW_BLOCKING=true|false` enables fail-fast blocking or warning-only mode;
- indexing aggregate quality summary expanded:
  - `documents_with_ocr_confidence_low`;
  - `ocr_confidence_min_score`;
  - `ocr_confidence_by_doc`;
- report/smoke/docs updated for OCR confidence counters and policy knobs;
- added ADR `0086-ocr-confidence-calibration-and-policy-gate.md`;
- targeted parser/policy/indexing/report/integration tests: `90 passed`;
- full suite with Docker async e2e and OpenRouter external LLM enabled: `314 passed`.

Eighteenth slice done:

- enhanced PDF pipe-table extraction for merged/wrapped rows:
- markdown separator rows (`| --- | --- |`) are ignored as data rows;
- continuation rows are merged into the previous row for merged/wrapped cell values;
- smoke demo path now gives explicit proof of the real `06_audit_summary.pdf`:
- direct smoke: `pdf_demo_proof` in `smoke_knowledge_indexing.py`;
- API smoke: `pdf_demo_proof` in `smoke_knowledge_indexing_api.py`;
- proof payload fixes extraction signs:
  - `found`;
  - `tables_total`/`table_rows_total`;
  - `has_pdf_tables_extracted`;
  - `has_pdf_form_like_blocks_detected`;
  - `has_pdf_rotated_layout_detected`;
- added ADR `0087-pdf-merged-table-hardening-and-demo-proof.md`;
- targeted parser/smoke/indexing/integration tests: `92 passed`;
- manual demo proof on real PDF fixture:
  - `smoke_knowledge_indexing.sh --build-binary-demo-docs` -> `pdf_demo_proof.found=true`, `tables_total=4`, `table_rows_total=6`;
  - `smoke_knowledge_indexing_api.sh --build-binary-demo-docs` -> `pdf_demo_proof.found=true`, `has_pdf_tables_extracted=true`.
- full suite with Docker async e2e and OpenRouter external LLM enabled: `315 passed`.

Scope:

- OCR path for scanned PDF:
  - `OCRmyPDF`;
  - Tesseract adapter boundary;
- quality flags for OCR confidence;
- rich layout extraction:
  - PDF logical blocks;
  - page/section mapping;
  - tables;
- DOCX hardening:
  - tables;
  - lists;
  - appendices;
- parser adapters for `.xlsx` and `.pptx` are implemented; PDF table+form baseline, coverage gates, form-confidence policy gate, multi-line/rotated hardening, OCR-confidence calibration and demo-proof contracts are closed; the next step is production rollout/fail-fast policy tuning on the real corpus.
- add document versions/read-model policy:
  - stable canonical identity;
  - version-aware lookup;
  - re-index semantics;
- quality gates have been transferred to a configurable production policy layer; the next step is production rollout/fail-fast policy.

Demo update:

- release go/no-go multifile case expands table/list fixture;
- smoke shows quality gate decisions by parser families.

Definition of Done:

- canonical document model covers the target parsing stack of the first production circuit;
- quality gates can block indexing in production policy;
- retrieval gets source refs from page/table/section mapping.

## Increment 32: Governance, Quality and Release Gate

Goal: Complete the backend/framework foundation as a managed production-ready foundation.

First slice done:

- execution metrics MVP is implemented on top of the existing task read-model without new telemetry storage:
- `GET /api/v1/tasks/events/summary` extended `daily[]`/`weekly[]` (`bucket_start`, `total_events`, `unique_tasks`);
- `GET /api/v1/tasks/observability/summary` and breakdown by `task_type` are extended with quality/token aggregates:
    - `avg_selected_block_count`, `avg_confidence`;
    - `tasks_with_unresolved_gaps`, `unresolved_gaps_total`;
    - `llm_tokens_prompt_total`, `llm_tokens_completion_total`, `llm_tokens_total`;
- task lifecycle details now automatically calculate `duration_ms` if `started_at` and `completed_at|failed_at` are present;
- authoring LLM path stores `llm_tokens_*` in draft metadata, artifact metadata and task details (provider usage + estimate fallback path);
- updated API/unit/e2e tests for new units and token fields;
- added ADR `0088-execution-metrics-mvp-day-week-and-token-quality-aggregates.md`;
- targeted tests: `98 passed`;
- full suite with Docker async e2e and OpenRouter external LLM enabled: `315 passed`.

Second slice done:

- observability SLA metrics added on top of the existing task read-model:
- overall and per-task-type `p50/p95` for `duration_ms` and `queue_wait_ms`;
- overall and per-task-type SLA breach counters:
    - `duration_sla_breaches_total`;
    - `queue_wait_sla_breaches_total`;
  - env-driven thresholds:
    - `APP_SLA_TASK_DURATION_MS`;
    - `APP_SLA_QUEUE_WAIT_MS`;
- `GET /api/v1/tasks/observability/summary` extended with periodic SLA time buckets:
- `daily[]` and `weekly[]` (`total_tasks`, `completed_tasks`, `failed_tasks`, `waiting_human_tasks`, SLA breaches);
- updated contracts/api mappings/tests (unit + integration + e2e);
- added ADR `0089-observability-sla-percentiles-and-time-buckets.md`;
- targeted tests: `76 passed`;
- full suite with Docker async e2e and OpenRouter external LLM enabled: `316 passed`.

Third slice done:

- added unified release-gate smoke matrix:
  - `backend/scripts/smoke_release_gate.py` + wrappers `smoke_release_gate.sh/.ps1`;
  - flow: optional `knowledge-indexing` -> `retrieval` -> `authoring + HITL` -> observability checks;
  - JSON verdict: `gate_status=pass|fail`, `checks[]` (`code`, `name`, `passed`, `expected`, `actual`, `message`), `failed_checks[]`, diagnostic `artifacts`.
- release-gate thresholds are included in the env/CLI contract:
- `--gate-profile dev|stage|prod` with baseline presets;
  - `APP_RELEASE_GATE_MIN_EVENTS_TOTAL`;
  - `APP_RELEASE_GATE_MIN_OBSERVABILITY_TOTAL_TASKS`;
  - `APP_RELEASE_GATE_MAX_DURATION_SLA_BREACHES`;
  - `APP_RELEASE_GATE_MAX_QUEUE_WAIT_SLA_BREACHES`;
  - `APP_RELEASE_GATE_REQUIRE_LLM_TOKENS`.
- updated runbook/scripts docs and contract tests:
  - `backend/tests/unit/test_smoke_release_gate_script.py`;
- `backend/tests/unit/test_production_runbook_contracts.py` now checks for `smoke_release_gate.sh` in the runbook.
- added ADR `0090-unified-release-gate-smoke-matrix.md`;
- targeted tests: `5 passed`;
- full suite with Docker async e2e and OpenRouter external LLM enabled: `318 passed`.

Fourth slice done:

- `smoke_release_gate` is enhanced by policy profiles and triage output:
- `--gate-profile dev|stage|prod` (with baseline presets);
- `checks[]` now contains short codes `RG001..RG012` and `message`;
- separate `failed_checks[]` for quick analysis of the reasons for fail verdict;
- profile/env/CLI override policy is fixed in `resolve_gate_policy(...)` and is covered by unit tests;
- scripts/runbook docs updated for the new profile contract (`stage/prod` examples);
- targeted tests: `6 passed`;
- full suite with Docker async e2e and OpenRouter external LLM enabled: `319 passed`.

Fifth slice done:

- added final release decision orchestrator:
  - `backend/scripts/release_decision_gate.py` + wrappers `release_decision_gate.sh/.ps1`;
- orchestrator runs `smoke_release_gate` + full pytest gate and writes unified verdict artifacts:
    - `backend/.release_gate/release_decision_*.json`;
    - `backend/.release_gate/release_decision_*.md`;
- unified decision payload fixes:
  - `status`, `decision_reason`, `failed_checks[]`;
  - `smoke_release_gate` summary;
  - `test_gate_summary`;
  - `profile`, `commit_sha`, `branch`, `timestamp_utc`;
- added ADR `0091-final-release-decision-contract.md`;
- runbook contract tests updated to mandatory `release_decision_gate.sh`;
- targeted tests: `8 passed`;
- full suite with Docker async e2e and OpenRouter external LLM enabled: `321 passed`.

Sixth slice done:

- external developer documentation surface for the reusable backend/framework library has been released:
- `docs/developer_guide/README.md` as a single entry point;
- `quickstart.md` for bootstrap + first smoke;
- `manual_demo_checks.md` for manual proof canonical indexing (including PDF/PPTX);
- `extension_recipes.md` for workflow/tool/MCP/persistence extension path;
- `operations_and_release.md` for release gate and full test gate.
- `README.md` updated with external documentation section and mandatory support `docs/developer_guide/*.md`.
- `System_Architecture_Overview.md` updated to reflect the new public documentation surface.
- added ADR `0092-external-developer-documentation-surface.md` and updated ADR index.
- added unit docs-contract test `backend/tests/unit/test_developer_guide_contracts.py`.
- targeted tests: `6 passed` (`test_developer_guide_contracts.py`, `test_production_runbook_contracts.py`);
- full suite with Docker async e2e and OpenRouter external LLM enabled: `324 passed`.

Scope:

- quality evaluation workflow;
- HITL/reviewer aggregates:
  - SLA;
  - decision mix;
  - reviewer load;
- task events aggregates for day/week;
- structured JSON logging and correlation id in API/worker/MCP;
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

- the framework is considered complete for the backend foundation;
- new product workflow is added through a documented extension path;
- demo acceptance confirms the full path `documents -> canonical indexing -> pgvector retrieval -> authoring -> HITL -> artifact -> traceability -> audit`;
- further development can move to the frontend/product layer without securing temporary backend contracts.

## Increment 33: OSS Contributor Funnel and Community Readiness

Status: Planned.

Goal: to package the backend/framework foundation into a contributor-friendly open source outline, while maintaining the production-first contract discipline.

First slice done:

- Slice 33.1.1: package license metadata aligned with root license (`backend/packages/pyproject.toml`: `Apache-2.0`).
- Slice 33.1.2: Added package-level README (`backend/packages/README.md`) under `readme = "README.md"` in package metadata.
- Slice 33.1.3: added no-infra first-success path (`2-Minute Demo: No Docker, No Postgres`) with expected output to root README; production smoke path is saved as a separate block below.
- Slice 33.1.4: updated `CONTRIBUTING.md` (first-time contributor section, docs/examples/packaging-only check profile, fixed docs links).
- Slice 33.2.1: added issue forms and PR template to `.github` for structured contributor intake.
- Slice 33.2.2: labels baseline applied to GitHub repo; triage SLA/status/closure policy added to `docs/developer_guide/maintainer_playbook.md`.
- Slice 33.2.3: initial public issue backlog (16 issues, including newcomer-friendly `good first issue` set) created.
- Slice 33.3.1: root README rebuilt in front-door order (who-for/when-not-to-use/no-infra-first/docs map) with production smoke path preserved.
- Slice 33.3.2: added comparison/use-case table (`Need / Use this project? / Why`) to the root README for early user qualification.
- Slice 33.3.3: discoverability topics on the actual project capabilities (14 topics) have been added to the GitHub repository.
- Slice 33.4.1: added contributor motivation blocks (`Why Contribute`) to the root README and `CONTRIBUTING.md`, including explicit path for vibe-coders.
- Slice 33.4.2: added AI-assisted contribution policy block (\"token contribution\" = contribution via AI agents, not donations; single quality/governance bar for everyone).

Program document:

- `docs/developer_guide/oss_contributor_funnel_program.md`

Iteration plan:

1. Iteration 33.1 (P0, Day 1-5): foundation fixes.
2. Iteration 33.2 (P1, Day 6-14): contributor funnel setup.
3. Iteration 33.3 (P2, Day 15-21): public front door restructuring.
4. Iteration 33.4 (P2, Day 22-30): community messaging + feedback loop.

Planned slices:

- Slice 33.1.1: reconcile package license metadata with root Apache-2.0 license.
- Slice 33.1.2: Add `backend/packages/README.md` under `readme = "README.md"` in package metadata.
- Slice 33.1.3: add `2-Minute Demo: No Docker, No Postgres` README to root (based on `agent_examples/run_example.py --pattern retrieval_first`).
- Slice 33.1.4: improve `CONTRIBUTING.md` (first-time contributor section, secure path, link consistency).
- Slice 33.2.1: add `.github/ISSUE_TEMPLATE/*` and `.github/pull_request_template.md`.
- Slice 33.2.2: expand labels/triage baseline for open source intake (`docs`, `examples`, `ci`, `packaging`, `community`, `needs maintainer review`, `blocked`, `security`).
- Slice 33.2.3: create an initial public backlog of 15-20 issues, of which at least 8 are `good first issue`.
- Slice 33.3.1: rebuild README entrypoint (who-for, when-not-to-use, no-infra demo, docs map, contributing).
- Slice 33.3.2: add comparison/use-case table for fair script qualification.
- Slice 33.3.3: add GitHub topics on the actual project capabilities (<=20).
- Slice 33.4.1: add contributor-motivation copy (public OSS track as verifiable engineering contribution).
- Slice 33.4.2: add a policy block about voluntary support of the project with tokens (without pay-to-prioritize and without feature guarantees).
- Slice 33.4.3: run feedback loop (`FEEDBACK.md`) and two-week project update template.

Scope:

- community/onboarding/documentation packaging;
- GitHub issues/labels/templates triage contour;
- external contributor funnel before the first PR;
- feedback pipeline and regular updates.

Contract safety:

- do not change stable API/MCP contracts without maintainer review and synchronization `public_contract_surface.md` + references;
- do not delete production smoke/release path; just rearrange the priority of entrypoints.

Definition of Done:

- no-infra demo path comes before production setup in README;
- package/license metadata are consistent;
- issue/PR templates and initial issue backlog were created;
- `CONTRIBUTING.md` has a first-time contributor section;
- added GitHub topics and feedback tracker;
- at least one public update and one external post draft have been prepared.

## Later Product/UI Track

After backend/framework stabilization:

- React/TypeScript frontend shell;
- task dashboard;
- evidence review screen;
- outline/section review screens;
- reviewer queue dashboard;
- generated artifacts/version screen;
- typed API client generated from OpenAPI;
- RBAC/SSO integration.

This track should not precede backend contracts, otherwise the UI will begin to assign temporary APIs and runtime shortcuts.
