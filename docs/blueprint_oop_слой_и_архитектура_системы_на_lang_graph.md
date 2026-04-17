# Архитектурный blueprint

## OOP-слой, LangGraph workflows, MCP contracts и структура реализации

## 1. Назначение документа

Настоящий документ является следующим уровнем детализации после ТЗ на систему документных AI-агентов на базе LangGraph.

Документ фиксирует:

- архитектурную декомпозицию системы по сервисам и модулям;
- структуру репозиториев и пакетов;
- целевой OOP-слой абстракции над типовыми компонентами;
- состав LangGraph workflows и subgraphs;
- основные contracts между слоями системы;
- состав MCP-серверов и их interfaces;
- принципы реализации reusable framework layer внутри проекта.

Основная цель документа — определить небольшое, строго стандартизированное, объектно-ориентированное внутреннее framework-ядро, которое позволит ускорять разработку новых агентов, retrieval-пайплайнов и document workflows без накопления хаоса.

---

## 2. Главная идея детализации

Система должна состоять из двух уровней:

### 2.1. Product layer

Это прикладная логика конкретной бизнес-системы:

- SAA / BA-агенты;
- retrieval-пайплайны;
- document authoring;
- review и approval flows;
- работа с шаблонами, ТЗ, СТО и проектными артефактами.

### 2.2. Internal framework layer

Это небольшой OOP-слой над типовыми техническими примитивами:

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

Идея состоит в том, чтобы бизнес-команда не собирала каждый новый agent flow вручную из разрозненных библиотек, а работала через устойчивые доменные и инфраструктурные абстракции.

---

## 3. Ключевые архитектурные принципы OOP-слоя

## 3.1. Strict OOP

Framework layer должен строго опираться на объектно-ориентированные принципы.

Обязательные требования:

- SRP — каждый класс отвечает за одну роль;
- OCP — расширение через наследование и композицию, а не через переписывание базовых классов;
- LSP — замена конкретных реализаций не должна ломать поведение системы;
- ISP — маленькие интерфейсы вместо больших “бог-объектов”;
- DIP — бизнес-слой зависит от абстракций, а не от конкретных библиотек.

## 3.2. Composition over inheritance

Наследование используется только для устойчивых базовых ролей. Поведение системы строится преимущественно через композицию.

## 3.3. No hidden magic

Внутренний framework не должен становиться “магическим фреймворком”, который скрывает поведение.

Каждая абстракция должна:

- иметь понятный интерфейс;
- иметь прозрачный lifecycle;
- иметь явные зависимости;
- быть дебажимой.

## 3.4. Typed contracts everywhere

Все интерфейсы должны быть типизированы. Внутренние и внешние данные должны описываться через Pydantic-схемы и/или Protocol/ABC контракты.

## 3.5. LangGraph остается runtime-ядром

OOP-слой не заменяет LangGraph, а организует и стандартизирует работу с ним. LangGraph остается системным runtime для orchestration.

---

## 4. Архитектура репозиториев

## 4.1. Рекомендуемая структура репозиториев

### Вариант A — Monorepo

Предпочтительный вариант для первой production-версии.

Состав:

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

### Вариант B — Multi-repo

Допускается только на более позднем этапе, если монорепозиторий начинает тормозить процессы.

## 4.2. Предпочтение monorepo

На старте предпочтителен monorepo, потому что он:

- упрощает согласование contracts;
- упрощает refactoring framework layer;
- уменьшает транзакционные издержки между сервисами;
- ускоряет развитие reusable abstractions.

---

## 5. Структура Python backend-кода

## 5.1. Верхнеуровневая структура

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

## 6.1. Назначение framework layer

Framework layer должен предоставить ограниченный набор стабильных абстракций, на которых строятся все прикладные flows.

### 6.1.1. Framework layer НЕ должен

- превращаться в второй LangChain;
- скрывать LangGraph слишком глубоко;
- усложнять доступ к низкоуровневым возможностям;
- вводить собственный DSL без необходимости.

### 6.1.2. Framework layer ДОЛЖЕН

- стандартизировать объектные модели;
- стандартизировать lifecycle узлов и агентов;
- унифицировать RAG-паттерны;
- унифицировать tool contracts;
- унифицировать state contracts;
- уменьшать boilerplate.

---

## 7. Базовые абстракции framework layer

## 7.1. Agent layer

### 7.1.1. IAgent

Базовый интерфейс агента.

Назначение:

- определить единый контракт для всех агентных ролей.

Минимальный интерфейс:

- `name`;
- `description`;
- `invoke(input, context)`;
- `supports_tools()`;
- `supports_structured_output()`;
- `build_prompt()`;
- `handle_result()`.

### 7.1.2. BaseAgent

Абстрактная базовая реализация.

Ответственность:

- общее поведение lifecycle;
- интеграция с model gateway;
- логирование;
- обработка structured output;
- стандартная обработка ошибок.

### 7.1.3. ToolAgent

Агент, умеющий работать с toolset.

### 7.1.4. ReviewAgent

Специализация агента для reviewer-паттернов.

### 7.1.5. SupervisorAgent

Специализация агента, которая возвращает routing/decision artifact.

### 7.1.6. HumanGateAgent

Специализация для human-interrupt boundary.

## 7.2. Tool layer

### 7.2.1. ITool

Базовый интерфейс tool.

Методы:

- `name()`;
- `description()`;
- `input_schema()`;
- `output_schema()`;
- `execute(command)`.

### 7.2.2. BaseTool

Абстрактная реализация tool.

Общие обязанности:

- validation;
- tracing;
- error handling;
- serialization.

### 7.2.3. ToolRegistry

Реестр tool-объектов.

Задачи:

- регистрация;
- lookup;
- policy filtering;
- capability discovery.

### 7.2.4. ToolExecutor

Сервис выполнения tool-команд.

Нужен для:

- унифицированного вызова tools;
- retries;
- timeouts;
- idempotency handling;
- audit logging.

## 7.3. Workflow layer

### 7.3.1. IWorkflow

Базовый интерфейс workflow.

### 7.3.2. BaseWorkflow

Абстракция для LangGraph-backed workflow.

Обязанности:

- объявление state schema;
- регистрация nodes;
- регистрация edges;
- compile();
- invoke();
- resume();

### 7.3.3. SubgraphWorkflow

Абстракция для reusable subgraph.

### 7.3.4. WorkflowFactory

Фабрика создания workflow-объектов по типу задачи.

## 7.4. State layer

### 7.4.1. IStateModel

Контракт для workflow state.

### 7.4.2. BaseStateModel

Базовая обертка над Pydantic state contract.

### 7.4.3. StateSerializer

Сериализация/десериализация state.

### 7.4.4. StatePatch

Контракт частичных обновлений state.

## 7.5. RAG layer

### 7.5.1. IRetriever

Контракт retriever’а.

Методы:

- `retrieve(query, filters, context)`.

### 7.5.2. IReranker

Контракт reranker’а.

### 7.5.3. IEvidenceBuilder

Контракт сборщика evidence pack.

### 7.5.4. BaseRetrievalPipeline

Базовый класс иерархического retrieval pipeline.

Шаги:

- prefilter;
- summary retrieve;
- detail retrieve;
- rerank;
- evidence build.

### 7.5.5. HierarchicalRAGPipeline

Конкретная реализация базового pipeline.

## 7.6. Storage layer

### 7.6.1. IDocumentStore

Контракт доступа к документам.

### 7.6.2. IKnowledgeStore

Контракт работы с canonical documents и knowledge blocks.

### 7.6.3. IVectorStore

Контракт работы с vector storage.

### 7.6.4. ICheckpointStore

Контракт checkpoint storage.

### 7.6.5. IArtifactStore

Контракт хранения generated artifacts.

## 7.7. DB layer

### 7.7.1. IRepository

Базовый repository contract.

### 7.7.2. BaseRepository

Абстрактная база для PostgreSQL-backed repository.

### 7.7.3. UnitOfWork

Абстракция транзакционной границы.

### 7.7.4. RepositoryFactory

Фабрика репозиториев.

## 7.8. Model layer

### 7.8.1. IChatModelGateway

Контракт доступа к генеративной модели.

### 7.8.2. IEmbeddingGateway

Контракт embeddings.

### 7.8.3. IRerankGateway

Контракт rerank.

### 7.8.4. ModelGatewayFactory

Фабрика model gateways.

## 7.9. HITL layer

### 7.9.1. IHumanReviewPort

Контракт связи с human review boundary.

### 7.9.2. HumanInterruptService

Сервис создания interrupt payloads.

### 7.9.3. HumanResumeService

Сервис обработки resume payloads.

### 7.9.4. ApprovalPolicy

Политика обязательных approval points.

## 7.10. MCP layer

### 7.10.1. IMcpService

Контракт MCP-сервиса.

### 7.10.2. BaseFastMcpService

Базовая реализация MCP-сервиса на FastMCP.

### 7.10.3. McpToolAdapter

Адаптер между framework tools и MCP tools.

---

## 8. Рекомендуемая объектная модель

## 8.1. Композиция уровня agent

Каждый агент должен собираться из следующих зависимостей:

- model gateway;
- prompt builder;
- tool registry;
- output parser;
- logger;
- policies;
- optional memory/state accessor.

### Пример композиции

`SupervisorAgent = BaseAgent + DecisionPromptBuilder + StructuredOutputParser + RoutingPolicy`

## 8.2. Композиция retrieval pipeline

`HierarchicalRAGPipeline = Prefilter + SummaryRetriever + DetailRetriever + Reranker + EvidenceBuilder`

## 8.3. Композиция workflow

`SectionAuthoringWorkflow = SupervisorAgent + ResearchAgent + WriterAgent + ReviewerAgent + HITL Service + Artifact Builder`

---

## 9. Обязательные abstract contracts

## 9.1. Базовые ABC / Protocol contracts

Проект должен содержать следующие обязательные абстракции:

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

## 9.2. Правило зависимости

Все прикладные domain-классы должны зависеть только от этих абстракций, а не от concrete adapters.

---

## 10. Concrete adapters

## 10.1. Infrastructure adapters

Concrete-адаптеры должны быть вынесены в `infra/` и не должны протекать в domain logic.

Минимальный набор concrete adapters:

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

Concrete adapter всегда реализует интерфейс framework layer.

Пример:

- `PgVectorStoreAdapter implements IVectorStore`
- `VllmChatModelGateway implements IChatModelGateway`
- `FastMcpRetrievalService extends BaseFastMcpService`

---

## 11. LangGraph workflows и subgraphs

## 11.1. Каталог workflows

### 11.1.1. KnowledgeIndexingWorkflow

Назначение:

- обход источников;
- parsing;
- canonicalization;
- metadata extraction;
- summary generation;
- block generation;
- embeddings;
- index write.

### 11.1.2. RetrievalPackWorkflow

Назначение:

- task understanding;
- filter building;
- hierarchical retrieval;
- rerank;
- evidence pack.

### 11.1.3. TemplateCompileWorkflow

Назначение:

- parsing шаблона;
- template spec;
- section contracts;
- validation rules.

### 11.1.4. SectionAuthoringWorkflow

Назначение:

- supervisor routing;
- research;
- write;
- review;
- human gate;
- finalize.

### 11.1.5. DocumentAssemblyWorkflow

Назначение:

- section collection;
- chapter summaries;
- consistency review;
- final assembly;
- export.

### 11.1.6. ExistingDocumentUpdateWorkflow

Назначение:

- diff detection;
- impacted sections;
- selective rewrite;
- review;
- save new version.

### 11.1.7. QualityEvaluationWorkflow

Назначение:

- retrieval evaluation;
- parsing evaluation;
- output evaluation;
- drift reporting.

## 11.2. Каталог subgraphs

### 11.2.1. MetadataExtractionSubgraph

### 11.2.2. SummaryBuildSubgraph

### 11.2.3. HierarchicalRetrievalSubgraph

### 11.2.4. SectionReviewSubgraph

### 11.2.5. HumanApprovalSubgraph

### 11.2.6. ConsistencyCheckSubgraph

### 11.2.7. VersionConflictResolutionSubgraph

---

## 12. Workflow state contracts

## 12.1. Общий принцип

Каждый workflow должен иметь собственный typed state contract.

## 12.2. Базовые state contracts

### 12.2.1. RetrievalWorkflowState

Поля:

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

Поля:

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

Поля:

- template\_spec
- section\_artifacts
- chapter\_summaries
- consistency\_report
- final\_document
- export\_result

## 12.3. State policy

State не должен хранить все подряд. В state сохраняются только артефакты, нужные для orchestration. Большие payloads выносятся в stores и передаются по refs.

---

## 13. Schemas package

## 13.1. Назначение

`packages/schemas` — единая точка истины для типизированных контрактов системы.

## 13.2. Категории схем

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

Зона ответственности:

- parsing logic;
- canonicalization;
- metadata extraction;
- template interpretation.

### Классы:

- `DocumentParser`
- `DocumentCanonicalizer`
- `MetadataExtractor`
- `TemplateCompiler`
- `SectionContractBuilder`

## 14.2. domain\_rag

Зона ответственности:

- indexing;
- retrieval;
- evidence construction;
- rerank orchestration.

### Классы:

- `IndexingCoordinator`
- `SummaryRetriever`
- `DetailRetriever`
- `RerankService`
- `EvidencePackBuilder`
- `HierarchicalRAGService`

## 14.3. domain\_authoring

Зона ответственности:

- outline;
- section drafting;
- review;
- consistency;
- assembly.

### Классы:

- `OutlinePlanner`
- `SectionAuthoringService`
- `SectionReviewService`
- `ConsistencyReviewService`
- `DocumentAssembler`
- `ArtifactExporter`

---

## 15. MCP contracts

## 15.1. Общие правила

Каждый MCP-сервер должен иметь:

- отдельный service package;
- отдельный contract module;
- собственные Pydantic input/output schemas;
- адаптер к framework layer.

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

API сервис не содержит бизнес-логики workflow. Он:

- принимает команды;
- валидирует payloads;
- инициирует workflow execution;
- выдает status;
- принимает resume payload;
- публикует результат.

## 16.2. Основные API application services

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

На базе shadcn/ui.

### 17.1.2. Feature Layer

Фичи:

- tasks;
- evidence review;
- outline review;
- section review;
- conflicts;
- artifacts.

### 17.1.3. Data Layer

На базе TanStack Query.

### 17.1.4. Form Layer

На базе React Hook Form + Zod.

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
- review actions only через typed mutations;
- reusable review widgets.

---

## 18. Тестирование

## 18.1. Обязательные уровни тестирования

### 18.1.1. Unit tests

Покрывают:

- framework layer;
- adapters;
- domain services;
- validators;
- serializers.

### 18.1.2. Integration tests

Покрывают:

- FastAPI + workflow integration;
- PostgreSQL repositories;
- pgvector integration;
- MCP service integration;
- model gateway integration.

### 18.1.3. Workflow tests

Покрывают:

- graph paths;
- interrupt/resume;
- error branches;
- fallback logic;
- approval branches.

### 18.1.4. Acceptance tests

Покрывают:

- сценарии из ТЗ;
- end-to-end use cases.

## 18.2. Framework testing rule

Каждая абстракция framework layer должна иметь contract tests.

---

## 19. Принципы расширения framework layer

## 19.1. Как добавляются новые агенты

Новый агент добавляется путем:

1. реализации интерфейса `IAgent` или наследования от `BaseAgent`;
2. регистрации через factory/registry;
3. объявления Pydantic input/output schemas;
4. подключения в workflow.

## 19.2. Как добавляются новые tools

Новый tool добавляется через:

1. реализацию `ITool`;
2. регистрацию в `ToolRegistry`;
3. contract tests;
4. optional MCP exposure через adapter.

## 19.3. Как добавляются новые workflows

Новый workflow добавляется через:

1. новый typed state;
2. новый `BaseWorkflow` descendant;
3. node registration;
4. workflow tests.

## 19.4. Как меняется storage

Storage layer должен позволять менять concrete реализации без изменения domain logic.

---

## 20. Ограничения framework layer

Framework layer не должен:

- абстрагировать LangGraph до неузнаваемости;
- навязывать одну форму prompts;
- скрывать диагностику LLM-вызовов;
- создавать собственный orchestration DSL;
- заменять собой все библиотеки экосистемы.

Framework layer должен оставаться небольшим и прагматичным.

---

## 21. Минимальный набор concrete классов для первой версии

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

## 22. Пошаговый план реализации OOP-слоя

## Фаза 1

- schemas package;
- base interfaces;
- base repositories;
- model gateways;
- checkpoint store adapter.

## Фаза 2

- base workflow abstraction;
- tool abstraction;
- retrieval pipeline abstraction;
- human review abstraction.

## Фаза 3

- section authoring workflow;
- retrieval workflow;
- template compiler workflow;
- MCP adapters.

## Фаза 4

- quality evaluation workflows;
- reusable review widgets;
- conflict resolution flows.

---

## 23. Definition of Done для framework layer

Framework layer считается пригодным, если:

- новый workflow можно собрать без прямого доступа к concrete infra-компонентам;
- новый agent создается через стандартный base class;
- новый tool подключается через registry без хрупкого glue-code;
- retrieval pipeline используется как готовая абстракция;
- state schemas единообразны;
- interrupt/resume не пишется вручную каждый раз;
- MCP service строится через единый base class;
- contract tests покрывают базовые абстракции.

---

## 24. Следующий шаг детализации

После данного blueprint должны быть подготовлены следующие проектные артефакты:

1. ADR по архитектурным решениям.
2. Полный каталог Pydantic schemas.
3. Скелет `packages/framework` с пустыми интерфейсами и базовыми реализациями.
4. Скелет `SectionAuthoringWorkflow` на LangGraph.
5. Скелет `HierarchicalRAGPipeline`.
6. Скелет `FastMcpRetrievalService`.
7. Скелет frontend feature map.

