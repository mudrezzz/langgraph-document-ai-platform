# Architectural blueprint

## OOP layer, LangGraph workflows, MCP contracts and implementation structure

## 1. Purpose of the document

This document is the next level of detail after the technical specifications for a system of document AI agents based on LangGraph.

The document records:

- architectural decomposition of the system into services and modules;
- structure of repositories and packages;
- target OOP abstraction layer over standard components;
- composition of LangGraph workflows and subgraphs;
- basic contracts between layers of the system;
- composition of MCP servers and their interfaces;
- principles for implementing a reusable framework layer within a project.

The main goal of the document is to define a small, strictly standardized, object-oriented internal framework core that will speed up the development of new agents, retrieval pipelines and document workflows without accumulating chaos.

---

## 2. The main idea of ​​detailing

The system should consist of two levels:

### 2.1. Product layer

This is the applied logic of a specific business system:

- SAA/BA agents;
- retrieval pipelines;
- document authoring;
- review and approval flows;
- work with templates, technical specifications, technical specifications and design artifacts.

### 2.2. Internal framework layer

This is a small OOP layer on top of typical technical primitives:

- Agent;
- Tool;
- Workflow;
- Graph State;
- RAG Pipeline;
- Retriever;
- Reranker;
- Knowledge Store;
- Vector Store;
- Database Repository;
- Checkpoint Store;
- Artifact Builder;
- HITL Gateway;
- MCP Service.

The idea is that the business team does not manually assemble each new agent flow from disparate libraries, but works through stable domain and infrastructure abstractions.

---

## 3. Key architectural principles of the OOP layer

## 3.1. Strict OOP

The Framework layer must strictly rely on object-oriented principles.

Mandatory requirements:

- SRP - each class is responsible for one role;
- OCP - extension through inheritance and composition, rather than through rewriting base classes;
- LSP - replacing specific implementations should not break the behavior of the system;
- ISP - small interfaces instead of large “god-objects”;
- DIP - the business layer depends on abstractions rather than specific libraries.

## 3.2. Composition over inheritance

Inheritance is used only for stable base roles. The behavior of the system is built primarily through composition.

## 3.3. No hidden magic

The internal framework should not become a “magic framework” that hides behavior.

Each abstraction must:

- have a clear interface;
- have a transparent lifecycle;
- have obvious dependencies;
- to be a fool.

## 3.4. Typed contracts everywhere

All interfaces must be typed. Internal and external data must be described through Pydantic schemas and/or Protocol/ABC contracts.

## 3.5. LangGraph remains the runtime core

The OOP layer does not replace LangGraph, but organizes and standardizes work with it. LangGraph remains the system runtime for orchestration.

---

## 4. Repository architecture

## 4.1. Recommended repository structure

### Option A - Monorepo

The preferred option for the first production version.

Compound:

- `apps/api`
- `apps/frontend`
- `apps/worker`
- `apps/mcp-*`
- `packages/core`
- `packages/framework`
- `packages/schemas`
- `packages/adapters`
- `packages/domain-docs`
- `packages/domain-rag`
- `packages/domain-authoring`
- `packages/tests`

### Option B - Multi-repo

Allowed only at a later stage if the monorepository begins to slow down processes.

## 4.2. Preference monorepo

At the start, monorepo is preferable because it:

- simplifies the negotiation of contracts;
- simplifies refactoring framework layer;
- reduces transaction costs between services;
- accelerates the development of reusable abstractions.

---

## 5. Python backend code structure

## 5.1. Top-level structure

```text
backend/
  apps/
    api/
    worker/
    mcp_retrieval/
    mcp_artifact_writer/
    mcp_repo/
  packages/
    framework/
      agents/
      tools/
      workflows/
      rag/
      stores/
      db/
      checkpoints/
      artifacts/
      hitl/
      mcp/
      models/
      logging/
      errors/
    schemas/
      api/
      workflow/
      rag/
      documents/
      approvals/
      artifacts/
    domain_docs/
      parsing/
      canonicalization/
      metadata/
      templates/
    domain_rag/
      indexing/
      retrieval/
      rerank/
      evidence/
    domain_authoring/
      outline/
      sections/
      review/
      assembly/
      consistency/
    infra/
      postgres/
      pgvector/
      vllm/
      tei/
      filesystem/
      fastmcp/
    tests/
      unit/
      integration/
      acceptance/
```

---

## 6. OOP framework layer

## 6.1. Purpose of the framework layer

The Framework layer must provide a limited set of stable abstractions on which all application flows are built.

### 6.1.1. Framework layer should NOT

- turn into a second LangChain;
- hide LangGraph too deeply;
- complicate access to low-level capabilities;
- enter your own DSL without the need.

### 6.1.2. Framework layer MUST

- standardize object models;
- standardize the lifecycle of nodes and agents;
- unify RAG patterns;
- unify tool contracts;
- unify state contracts;
- reduce boilerplate.

---

## 7. Basic abstractions of the framework layer

## 7.1. Agent layer

### 7.1.1. IAgent

Basic agent interface.

Purpose:

- define a single contract for all agent roles.

Minimal interface:

- `name`;
- `description`;
- `invoke(input, context)`;
- `supports_tools()`;
- `supports_structured_output()`;
- `build_prompt()`;
- `handle_result()`.

### 7.1.2. BaseAgent

Abstract base implementation.

Responsibility:

- general lifecycle behavior;
- integration with model gateway;
- logging;
- processing structured output;
- standard error handling.

### 7.1.3. ToolAgent

An agent who can work with toolset.

### 7.1.4. ReviewAgent

Agent specialization for reviewer patterns.

### 7.1.5. SupervisorAgent

Agent specialization, which returns a routing/decision artifact.

### 7.1.6. HumanGateAgent

Specialization for human-interrupt boundary.

## 7.2. Tool layer

### 7.2.1. ITool

Basic tool interface.

Methods:

- `name()`;
- `description()`;
- `input_schema()`;
- `output_schema()`;
- `execute(command)`.

### 7.2.2. BaseTool

Abstract implementation of tool.

General responsibilities:

- validation;
- tracing;
- error handling;
- serialization.

### 7.2.3. ToolRegistry

Registry of tool objects.

Tasks:

- registration;
- lookup;
- policy filtering;
- capability discovery.

### 7.2.4. ToolExecutor

Service for executing tool commands.

Needed for:

- unified call to tools;
- retries;
- timeouts;
- idempotency handling;
- audit logging.

## 7.3. Workflow layer

### 7.3.1. IWorkflow

Basic workflow interface.

### 7.3.2. BaseWorkflow

Abstraction for LangGraph-backed workflow.

Responsibilities:

- state schema declaration;
- nodes registration;
- edges registration;
- compile();
- invoke();
- resume();

### 7.3.3. SubgraphWorkflow

Abstraction for reusable subgraph.

### 7.3.4. WorkflowFactory

Factory for creating workflow objects by task type.

## 7.4. State layer

### 7.4.1. IStateModel

Contract for workflow state.

### 7.4.2. BaseStateModel

Basic wrapper for Pydantic state contract.

### 7.4.3. StateSerializer

Serialization/deserialization of state.

### 7.4.4. StatePatch

Contract for partial state updates.

## 7.5. RAG layer

### 7.5.1. IRetriever

Retriever's contract.

Methods:

- `retrieve(query, filters, context)`.

### 7.5.2. IReranker

Reranker's contract.

### 7.5.3. IEvidenceBuilder

Evidence pack collector contract.

### 7.5.4. BaseRetrievalPipeline

The base class of the hierarchical retrieval pipeline.

Steps:

- prefilter;
- summary retrieve;
- detail retrieve;
- rerank;
- evidence build.

### 7.5.5. HierarchicalRAGPipeline

A specific implementation of the basic pipeline.

## 7.6. Storage layer

### 7.6.1. IDocumentStore

Document access contract.

### 7.6.2. IKnowledgeStore

Contract for working with canonical documents and knowledge blocks.

### 7.6.3. IVectorStore

Contract for work with vector storage.

### 7.6.4. ICheckpointStore

Checkpoint storage contract.

### 7.6.5. IArtifactStore

Storage contract for generated artifacts.

## 7.7. DB layer

### 7.7.1. IRepository

Basic repository contract.

### 7.7.2. BaseRepository

Abstract base for PostgreSQL-backed repository.

### 7.7.3. UnitOfWork

Transactional boundary abstraction.

### 7.7.4. RepositoryFactory

Repository Factory.

## 7.8. Model layer

### 7.8.1. IChatModelGateway

Generative model access contract.

### 7.8.2. IEmbeddingGateway

Contract embeddings.

### 7.8.3. IRerankGateway

Contract rerank.

### 7.8.4. ModelGatewayFactory

Factory model gateways.

## 7.9. HITL layer

### 7.9.1. IHumanReviewPort

Communication contract with the human review boundary.

### 7.9.2. HumanInterruptService

Service for creating interrupt payloads.

### 7.9.3. HumanResumeService

Resume payloads processing service.

### 7.9.4. ApprovalPolicy

Policy of mandatory approval points.

## 7.10. MCP layer

### 7.10.1. IMcpService

MCP service contract.

### 7.10.2. BaseFastMcpService

Basic implementation of MCP service on FastMCP.

### 7.10.3. McpToolAdapter

Adapter between framework tools and MCP tools.

---

## 8. Recommended object model

## 8.1. Agent level composition

Each agent must be built from the following dependencies:

- model gateway;
- prompt builder;
- tool registry;
- output parser;
- logger;
- policies;
- optional memory/state accessor.

### Composition example

`SupervisorAgent = BaseAgent + DecisionPromptBuilder + StructuredOutputParser + RoutingPolicy`

## 8.2. Composition retrieval pipeline

`HierarchicalRAGPipeline = Prefilter + SummaryRetriever + DetailRetriever + Reranker + EvidenceBuilder`

## 8.3. Workflow composition

`SectionAuthoringWorkflow = SupervisorAgent + ResearchAgent + WriterAgent + ReviewerAgent + HITL Service + Artifact Builder`

---

## 9. Mandatory abstract contracts

## 9.1. Basic ABC/Protocol contracts

The project must contain the following required abstractions:

- `IAgent`
- `ITool`
- `IWorkflow`
- `IStateModel`
- `IRetriever`
- `IReranker`
- `IEvidenceBuilder`
- `IDocumentStore`
- `IKnowledgeStore`
- `IVectorStore`
- `ICheckpointStore`
- `IArtifactStore`
- `IRepository`
- `IChatModelGateway`
- `IEmbeddingGateway`
- `IRerankGateway`
- `IHumanReviewPort`
- `IMcpService`

## 9.2. Dependency Rule

All applied domain classes should depend only on these abstractions, and not on concrete adapters.

---

## 10. Concrete adapters

## 10.1. Infrastructure adapters

Concrete adapters should be placed in `infra/` and should not flow into domain logic.

Minimum set of concrete adapters:

- `VllmChatModelGateway`
- `TeiEmbeddingGateway`
- `TeiRerankGateway`
- `PostgresDocumentRepository`
- `PgVectorStoreAdapter`
- `LangGraphPostgresCheckpointStore`
- `FilesystemArtifactStore`
- `FastMcpRetrievalService`
- `FastMcpArtifactWriterService`
- `FastMcpRepositoryService`

## 10.2. Adapter rule

Concrete adapter always implements the framework layer interface.

Example:

- `PgVectorStoreAdapter implements IVectorStore`
- `VllmChatModelGateway implements IChatModelGateway`
- `FastMcpRetrievalService extends BaseFastMcpService`

---

## 11. LangGraph workflows and subgraphs

## 11.1. Workflows directory

### 11.1.1. KnowledgeIndexingWorkflow

Purpose:

- bypassing sources;
- parsing;
- canonicalization;
- metadata extraction;
- summary generation;
- block generation;
- embeddings;
- index write.

### 11.1.2. RetrievalPackWorkflow

Purpose:

- task understanding;
- filter building;
- hierarchical retrieval;
- rerank;
- evidence pack.

### 11.1.3. TemplateCompileWorkflow

Purpose:

- template parsing;
- template spec;
- section contracts;
- validation rules.

### 11.1.4. SectionAuthoringWorkflow

Purpose:

- supervisor routing;
- research;
- write;
- review;
- human gate;
- finalize.

### 11.1.5. DocumentAssemblyWorkflow

Purpose:

- section collection;
- chapter summaries;
- consistency review;
- final assembly;
- export.

### 11.1.6. ExistingDocumentUpdateWorkflow

Purpose:

- diff detection;
- impacted sections;
- selective rewrite;
- review;
- save new version.

### 11.1.7. QualityEvaluationWorkflow

Purpose:

- retrieval evaluation;
- parsing evaluation;
- output evaluation;
- drift reporting.

## 11.2. Subgraphs directory

### 11.2.1. MetadataExtractionSubgraph

### 11.2.2. SummaryBuildSubgraph

### 11.2.3. HierarchicalRetrievalSubgraph

### 11.2.4. SectionReviewSubgraph

### 11.2.5. HumanApprovalSubgraph

### 11.2.6. ConsistencyCheckSubgraph

### 11.2.7. VersionConflictResolutionSubgraph

---

## 12. Workflow state contracts

## 12.1. General principle

Each workflow must have its own typed state contract.

## 12.2. Basic state contracts

### 12.2.1. RetrievalWorkflowState

Fields:

- task\_context
- query
- filters
- selected\_summaries
- selected\_blocks
- reranked\_blocks
- evidence\_pack
- confidence
- unresolved\_gaps

### 12.2.2. SectionAuthoringState

Fields:

- task\_context
- section\_contract
- project\_context
- evidence\_pack
- research\_summary
- draft
- review\_result
- human\_feedback
- iteration\_count
- final\_section\_artifact

### 12.2.3. AssemblyWorkflowState

Fields:

- template\_spec
- section\_artifacts
- chapter\_summaries
- consistency\_report
- final\_document
- export\_result

## 12.3. State policy

State should not store everything. Only artifacts needed for orchestration are stored in state. Large payloads are sent to stores and transferred via refs.

---

## 13. Schemas package

## 13.1. Purpose

`packages/schemas` is a single point of truth for the system's typed contracts.

## 13.2. Scheme categories

### 13.2.1. API Schemas

- request/response payloads
- task start payloads
- resume payloads
- approval payloads

### 13.2.2. Workflow Schemas

- state contracts
- step result contracts
- decision artifacts
- review artifacts

### 13.2.3. RAG Schemas

- retrieval query
- retrieval filters
- evidence pack
- rerank result
- source refs

### 13.2.4. Documents Schemas

- canonical document
- metadata profile
- template spec
- section contract
- section digest
- final artifact

---

## 14. Domain packages

## 14.1. domain\_docs

Area of ​​responsibility:

- parsing logic;
- canonicalization;
- metadata extraction;
- template interpretation.

### Classes:

- `DocumentParser`
- `DocumentCanonicalizer`
- `MetadataExtractor`
- `TemplateCompiler`
- `SectionContractBuilder`

## 14.2. domain\_rag

Area of ​​responsibility:

- indexing;
- retrieval;
- evidence construction;
- rerank orchestration.

### Classes:

- `IndexingCoordinator`
- `SummaryRetriever`
- `DetailRetriever`
- `RerankService`
- `EvidencePackBuilder`
- `HierarchicalRAGService`

## 14.3. domain\_authoring

Area of ​​responsibility:

- outline;
- section drafting;
- review;
- consistency;
- assembly.

### Classes:

- `OutlinePlanner`
- `SectionAuthoringService`
- `SectionReviewService`
- `ConsistencyReviewService`
- `DocumentAssembler`
- `ArtifactExporter`

---

## 15. MCP contracts

## 15.1. General rules

Each MCP server must have:

- separate service package;
- separate contract module;
- own Pydantic input/output schemas;
- adapter to framework layer.

## 15.2. Retrieval MCP contract

### Tools:

- `search_summaries`
- `search_blocks`
- `build_evidence_pack`
- `lookup_source`
- `find_similar_configuration`

## 15.3. Artifact Writer MCP contract

### Tools:

- `save_section_draft`
- `save_final_document`
- `export_docx`
- `export_json`
- `create_new_version`

## 15.4. Repository MCP contract

### Tools:

- `read_document`
- `read_document_version`
- `list_project_documents`
- `get_canonical_document`
- `get_template_spec`

---

## 16. API boundary design

## 16.1. API Service responsibilities

The API service does not contain workflow business logic. He:

- accepts commands;
- validates payloads;
- initiates workflow execution;
- displays status;
- accepts resume payload;
- publishes the result.

## 16.2. Basic API application services

- `TaskApplicationService`
- `AuthoringApplicationService`
- `RetrievalApplicationService`
- `ApprovalApplicationService`
- `ArtifactApplicationService`

## 16.3. Controllers / Routers

- `TaskRouter`
- `RetrievalRouter`
- `ApprovalRouter`
- `ArtifactRouter`
- `HealthRouter`

---

## 17. Frontend architecture detail

## 17.1. Frontend layers

### 17.1.1. UI Components Layer

Based on shadcn/ui.

### 17.1.2. Feature Layer

Features:

- tasks;
- evidence review;
- outline review;
- section review;
- conflicts;
- artifacts.

### 17.1.3. Data Layer

Based on TanStack Query.

### 17.1.4. Form Layer

Based on React Hook Form + Zod.

## 17.2. Frontend file structure

```text
frontend/
  src/
    app/
    pages/
    widgets/
    features/
      tasks/
      evidence/
      outline/
      sections/
      approvals/
      artifacts/
    entities/
    shared/
      ui/
      api/
      hooks/
      schemas/
      utils/
```

## 17.3. UI principles

- feature-first organization;
- typed API client;
- no business logic in components;
- review actions only through typed mutations;
- reusable review widgets.

---

## 18. Testing

## 18.1. Mandatory testing levels

### 18.1.1. Unit tests

Cover:

- framework layer;
- adapters;
- domain services;
- validators;
- serializers.

### 18.1.2. Integration tests

Cover:

- FastAPI + workflow integration;
- PostgreSQL repositories;
- pgvector integration;
- MCP service integration;
- model gateway integration.

### 18.1.3. Workflow tests

Cover:

- graph paths;
- interrupt/resume;
- error branches;
- fallback logic;
- approval branches.

### 18.1.4. Acceptance tests

Cover:

- scenarios from technical specifications;
- end-to-end use cases.

## 18.2. Framework testing rule

Each framework layer abstraction must have contract tests.

---

## 19. Principles of expanding the framework layer

## 19.1. How new agents are added

A new agent is added by:

1. implementation of the `IAgent` interface or inheritance from `BaseAgent`;
2. registration via factory/registry;
3. Pydantic input/output schemas declarations;
4. connections in workflow.

## 19.2. How new tools are added

A new tool is added via:

1. implementation of `ITool`;
2. registration in `ToolRegistry`;
3. contract tests;
4. optional MCP exposure via adapter.

## 19.3. How new workflows are added

A new workflow is added via:

1. new typed state;
2. new `BaseWorkflow` descendant;
3. node registration;
4. workflow tests.

## 19.4. How storage is changing

The storage layer should allow changing concrete implementations without changing the domain logic.

---

## 20. Limitations of the framework layer

Framework layer should not:

- abstract LangGraph beyond recognition;
- impose one form of prompts;
- hide diagnostics of LLM calls;
- create your own orchestration DSL;
- replace all ecosystem libraries.

The Framework layer must remain small and pragmatic.

---

## 21. Minimum set of concrete classes for the first version

### framework/agents

- `BaseAgent`
- `ToolAgent`
- `SupervisorAgent`
- `ReviewAgent`

### framework/tools

- `BaseTool`
- `ToolRegistry`
- `ToolExecutor`

### framework/workflows

- `BaseWorkflow`
- `SubgraphWorkflow`
- `WorkflowFactory`

### framework/rag

- `BaseRetrievalPipeline`
- `HierarchicalRAGPipeline`
- `EvidenceBuilder`

### framework/stores

- `BaseDocumentStore`
- `BaseKnowledgeStore`
- `BaseVectorStore`
- `BaseArtifactStore`

### framework/db

- `BaseRepository`
- `UnitOfWork`
- `RepositoryFactory`

### framework/models

- `ChatModelGateway`
- `EmbeddingGateway`
- `RerankGateway`

### framework/hitl

- `HumanInterruptService`
- `HumanResumeService`
- `ApprovalPolicy`

### framework/mcp

- `BaseFastMcpService`
- `McpToolAdapter`

---

## 22. Step-by-step plan for implementing the OOP layer

## Phase 1

- schemas package;
- base interfaces;
- base repositories;
- model gateways;
- checkpoint store adapter.

## Phase 2

- base workflow abstraction;
- tool abstraction;
- retrieval pipeline abstraction;
- human review abstraction.

## Phase 3

- section authoring workflow;
- retrieval workflow;
- template compiler workflow;
- MCP adapters.

## Phase 4

- quality evaluation workflows;
- reusable review widgets;
- conflict resolution flows.

---

## 23. Definition of Done for framework layer

Framework layer is considered suitable if:

- a new workflow can be assembled without direct access to concrete infra components;
- a new agent is created through the standard base class;
- the new tool is connected via the registry without fragile glue-code;
- retrieval pipeline is used as a ready-made abstraction;
- state schemas are uniform;
- interrupt/resume is not written manually every time;
- MCP service is built through a single base class;
- contract tests cover basic abstractions.

---

## 24. Next step of detailing

After this blueprint, the following design artifacts should be prepared:

1. ADR on architectural solutions.
2. Full catalog of Pydantic schemas.
3. Skeleton `packages/framework` with empty interfaces and basic implementations.
4. Skeleton `SectionAuthoringWorkflow` on LangGraph.
5. Skeleton `HierarchicalRAGPipeline`.
6. Skeleton `FastMcpRetrievalService`.
7. Skeleton frontend feature map.

