# Техническое задание
## Система AI-агентов для работы с проектной документацией на базе LangGraph

## 1. Назначение документа

Настоящее техническое задание описывает целевую архитектуру, технологический стек и принципы реализации системы AI-агентов для работы с проектной документацией в проектах внедрения ПО.

Документ фиксирует:
- архитектуру системы на базе LangGraph;
- стандартизированный технологический стек;
- состав сервисов и границы ответственности;
- подход к иерархическому RAG;
- подход к multi-agent orchestration;
- HITL-модель;
- требования к фронтенду, бекенду, MCP, хранению данных и деплою.

Цель документа — минимизировать количество нестандартизированных решений, уменьшить объем самописной инфраструктуры и использовать зрелые, повторно используемые, понятные в старте компоненты.

---

## 2. Цели системы

Система должна:
- автоматизировать работу бизнес-аналитика с большим массивом проектных документов;
- поддерживать обработку документов разных форматов и качества;
- обеспечивать качественный retrieval по многоуровневому knowledge corpus;
- использовать методологические указания и шаблоны как нормативную основу;
- генерировать новые документы по шаблонам;
- обновлять существующие документы;
- обеспечивать human-in-the-loop на критических этапах;
- работать в закрытом контуре;
- быть пригодной для масштабирования и production-эксплуатации.

---

## 3. Основные архитектурные принципы

### 3.1. LangGraph как единый orchestration runtime
LangGraph используется как основной runtime для:
- stateful agent workflows;
- multi-agent orchestration;
- conditional routing;
- human-in-the-loop;
- interrupt/resume;
- checkpointing и долгоживущих процессов.

### 3.2. Кодовая, а не визуальная оркестрация
Оркестрация бизнес-логики реализуется кодом на Python.
Система не должна опираться на визуальные low-code оркестраторы как на ядро исполнения.

### 3.3. LangChain используется ограниченно
LangChain допускается только как слой адаптеров и готовых интеграций:
- модели;
- embeddings;
- vector store adapters;
- retrievers;
- tools wrappers.

LangChain не должен использоваться как место, где скрыта критическая бизнес-логика системы.

### 3.4. Минимизация числа инфраструктурных компонентов
В первой production-версии необходимо стремиться к небольшому числу обязательных сервисов.
Базовый стек должен быть компактным, предсказуемым и поддерживаемым небольшой инженерной командой.

### 3.5. Один стандартный путь реализации
Для каждого класса задач должны быть зафиксированы стандартные технологии.
Команда не должна выбирать новый стек под каждую подсистему.

---

## 4. Обязательный технологический стек

## 4.1. Backend
Обязательный стек backend:
- Python 3.12;
- FastAPI;
- LangGraph;
- Pydantic v2;
- FastMCP.

### 4.1.1. Роль компонентов
- **FastAPI** — HTTP API, веб-хуки, admin endpoints, runtime endpoints, ingestion endpoints.
- **LangGraph** — оркестрация agent workflows, state machines, multi-agent pipelines, HITL.
- **Pydantic v2** — схемы данных, state contracts, validation.
- **FastMCP** — стандарт для всех MCP-серверов системы.

## 4.2. Frontend
Обязательный стек frontend:
- React;
- TypeScript;
- Vite;
- shadcn/ui;
- Tailwind CSS;
- TanStack Query;
- React Hook Form;
- Zod.

### 4.2.1. Принцип frontend-стека
Frontend должен быть:
- легким в старте;
- быстрым в разработке internal UI;
- пригодным для расширения;
- типобезопасным;
- удобным для форм, таблиц, review-flow и traceability views.

## 4.3. Хранилища и база данных
Обязательный стек хранения:
- PostgreSQL;
- pgvector.

### 4.3.1. PostgreSQL используется как
- основная транзакционная БД;
- хранилище metadata;
- хранилище checkpoint state;
- база для vector search через pgvector;
- база для аудита, очередей задач и служебных таблиц.

### 4.3.2. Принцип минимизации инфраструктуры
На первом этапе не вводится отдельная vector DB, если PostgreSQL + pgvector покрывают требования по объему и latency.

## 4.4. Model serving
Обязательный стек model serving для закрытого контура:
- vLLM — для генеративных LLM;
- Hugging Face Text Embeddings Inference (TEI) — для embeddings и rerank.

### 4.4.1. Роль model serving слоя
- генерация текста;
- structured output;
- embeddings;
- reranking;
- при необходимости классификация и lightweight semantic scoring.

## 4.5. Parsing и extraction
Стандартный стек обработки документов:
- PyMuPDF — PDF;
- OCRmyPDF + Tesseract OCR — scanned PDF;
- python-docx — DOCX;
- openpyxl — XLS/XLSX;
- python-pptx — PPT/PPTX.

### 4.5.1. Принцип extraction-стека
Для каждого формата используется наиболее стандартная и зрелая библиотека.
Не допускается построение ключевой extraction-логики на случайных или малоуправляемых инструментах без необходимости.

## 4.6. API integration и сервисный контракт
Межсервисные контракты:
- HTTP/JSON через FastAPI;
- MCP через FastMCP;
- OpenAPI для типизации и контрактов;
- Pydantic-схемы как источник истины для payload contracts.

---

## 5. Компоненты системы

## 5.1. Состав сервисов
Минимальный production-контур должен состоять из следующих сервисов.

### 5.1.1. API Service
Назначение:
- входная точка для UI;
- создание и запуск задач;
- выдача статусов;
- resume для HITL;
- управление retrieval и authoring request lifecycle.

Технологии:
- FastAPI;
- Pydantic;
- LangGraph runtime integration.

### 5.1.2. LangGraph Orchestrator Service
Назначение:
- исполнение agent workflows;
- stateful orchestration;
- checkpointing;
- multi-agent coordination;
- interrupt/resume.

Технологии:
- LangGraph;
- PostgreSQL-based checkpointer.

### 5.1.3. Ingestion Worker Service
Назначение:
- обход файловых источников;
- парсинг документов;
- нормализация;
- metadata extraction;
- summary building;
- chunking;
- upsert в knowledge stores.

Технологии:
- Python;
- FastAPI task endpoints или CLI entrypoints;
- extraction stack;
- PostgreSQL + pgvector.

### 5.1.4. MCP Services
Назначение:
- стандартизированный доступ агентов к внешним действиям и ресурсам.

Все MCP-сервера реализуются только на FastMCP.

Минимальный набор MCP-серверов:
- Document Repository MCP;
- Retrieval MCP;
- Artifact Writer MCP;
- Review / Approval MCP;
- Configuration Library MCP.

### 5.1.5. Model Serving Services
Назначение:
- inference для LLM;
- embeddings;
- rerank.

Сервисы:
- vLLM;
- TEI.

### 5.1.6. Frontend Application
Назначение:
- запуск user tasks;
- просмотр статусов;
- review и approval;
- просмотр evidence pack;
- просмотр section digests;
- просмотр traceability;
- ручное редактирование и подтверждение артефактов.

---

## 6. Архитектурные домены

## 6.1. Knowledge Factory
Назначение:
- подготовка и индексация знаний;
- extraction;
- metadata enrichment;
- summaries;
- chunking;
- indexing.

## 6.2. Retrieval Fabric
Назначение:
- query understanding;
- retrieval planning;
- metadata filtering;
- summary retrieval;
- detailed retrieval;
- rerank;
- evidence pack construction.

## 6.3. Authoring Workflow
Назначение:
- интерпретация методологии;
- выбор шаблона;
- outline generation;
- section drafting;
- review;
- consistency checks;
- deterministic assembly.

## 6.4. Governance & Quality
Назначение:
- контроль качества parsing;
- контроль retrieval quality;
- контроль output quality;
- drift monitoring;
- traceability and audit.

---

## 7. Стандартизированный стек по доменам

## 7.1. Knowledge Factory
Обязательные компоненты:
- Python 3.12;
- FastAPI или CLI workers;
- PyMuPDF / OCRmyPDF / python-docx / openpyxl / python-pptx;
- Pydantic schemas;
- PostgreSQL + pgvector;
- TEI embeddings.

### 7.1.1. Выходы Knowledge Factory
- canonical document JSON;
- metadata profile;
- summary artifacts;
- detailed content blocks;
- vector embeddings;
- indexing records.

## 7.2. Retrieval Fabric
Обязательные компоненты:
- LangGraph subgraphs;
- LangChain retriever adapters;
- PostgreSQL + pgvector;
- TEI rerank;
- FastMCP Retrieval Server.

### 7.2.1. Принцип retrieval
Retrieval не должен быть single-stage semantic search.
Должен использоваться иерархический каскад.

## 7.3. Authoring Workflow
Обязательные компоненты:
- LangGraph;
- FastMCP tool layer;
- Pydantic structured outputs;
- FastAPI resume endpoints;
- frontend review UI.

## 7.4. Frontend
Обязательные компоненты:
- React + TypeScript;
- Vite;
- shadcn/ui + Tailwind;
- TanStack Query;
- React Hook Form + Zod.

---

## 8. Иерархический RAG

## 8.1. Общая схема
Для всех knowledge-intensive сценариев используется иерархический RAG.

Этапы:
1. metadata pre-filter;
2. retrieval по summary layer;
3. narrowing candidate documents;
4. retrieval по detailed block layer;
5. rerank;
6. evidence pack assembly.

## 8.2. Knowledge layers
Обязательные слои индекса:

### 8.2.1. Methodology / Templates Layer
Содержит:
- методологические документы;
- шаблоны;
- нормативные указания;
- style rules;
- section rules.

### 8.2.2. Summary Layer
Содержит:
- document summary;
- section summaries;
- extracted entities;
- decisions;
- assumptions;
- constraints;
- source profiles.

### 8.2.3. Detailed Blocks Layer
Содержит:
- структурные блоки документов;
- section-aware chunks;
- table-derived semantic records;
- slide blocks;
- source references.

## 8.3. Chunking
Chunking должен быть структурным, а не только размерным.

Подходы:
- DOCX — по heading hierarchy и таблицам;
- PDF — по логическим блокам и секциям;
- XLSX — по листам, логическим таблицам и строкам как semantic units;
- PPTX — по слайдам и секциям.

## 8.4. Rerank
Rerank обязателен для authoring и complex QA сценариев.
Стандартный инструмент rerank — TEI rerank endpoint.

## 8.5. Evidence Pack
Evidence pack должен быть стандартным артефактом между retrieval и authoring.

Состав:
- selected sources;
- selected blocks;
- methodology refs;
- template refs;
- unresolved gaps;
- traceability map;
- confidence notes.

---

## 9. LangGraph-first orchestration

## 9.1. Общий принцип
Каждый сложный процесс реализуется как LangGraph workflow или subgraph.

### 9.1.1. В системе не допускается
- прятать orchestration-логику в UI;
- прятать orchestration-логику в промптах без явного graph structure;
- строить критические процессы как длинные линейные цепочки без state.

## 9.2. Типы graph-процессов

### 9.2.1. Long-running workflows
Используются для:
- ingestion;
- authoring;
- review cycles;
- conflict resolution;
- resumable tasks.

### 9.2.2. Subgraphs
Используются для:
- retrieval pack builder;
- section authoring engine;
- template compiler;
- consistency checker;
- review engine.

### 9.2.3. Interrupt-driven workflows
Используются для:
- human approval;
- conflict resolution;
- low-confidence cases;
- version replacement approval;
- unresolved evidence gaps.

## 9.3. Checkpointing
Checkpointing обязателен для всех долгоживущих процессов.
State должен сохраняться в PostgreSQL.

## 9.4. Multi-agent orchestration
Multi-agent схема реализуется как набор специализированных subagents в LangGraph.

Минимальный набор agent roles:
- Supervisor;
- Research Agent;
- Retrieval Planner Agent;
- Writer Agent;
- Reviewer Agent;
- Consistency Reviewer;
- Human Gate Agent.

---

## 10. MCP-стандарт

## 10.1. Общий принцип
Все MCP-сервера системы реализуются только через FastMCP.
Другие MCP-фреймворки в проекте не используются.

## 10.2. Обязательные MCP-серверы

### 10.2.1. Document Repository MCP
Функции:
- чтение исходных документов;
- чтение generated artifacts;
- доступ к canonical representations;
- version-aware read.

### 10.2.2. Retrieval MCP
Функции:
- поиск по knowledge layers;
- metadata filtering;
- summary retrieval;
- detailed retrieval;
- rerank orchestration;
- выдача evidence pack.

### 10.2.3. Artifact Writer MCP
Функции:
- запись черновиков;
- запись финальных документов;
- экспорт в целевые форматы;
- version-aware write.

### 10.2.4. Review / Approval MCP
Функции:
- фиксация review outcomes;
- регистрация human approvals;
- resume payload delivery.

### 10.2.5. Configuration Library MCP
Функции:
- работа с библиотекой типовых конфигураций;
- поиск аналогов;
- сравнение конфигураций;
- сохранение и версионирование конфигурационных артефактов.

---

## 11. Frontend

## 11.1. Назначение UI
UI является базовым рабочим интерфейсом аналитика и reviewer’а.
UI не является местом выполнения агентной логики.

## 11.2. Обязательные разделы UI

### 11.2.1. Task Dashboard
- список задач;
- статусы;
- типы задач;
- фильтры;
- запуск новых задач.

### 11.2.2. Evidence Review Screen
- просмотр evidence pack;
- просмотр источников;
- traceability;
- unresolved gaps.

### 11.2.3. Outline Review Screen
- просмотр outline;
- подтверждение структуры;
- комментарии аналитика.

### 11.2.4. Section Review Screen
- черновик раздела;
- review issues;
- редактирование;
- approve / send back.

### 11.2.5. Conflict Resolution Screen
- conflicting sources;
- варианты выбора;
- комментарий аналитика;
- фиксация решения.

### 11.2.6. Generated Artifacts Screen
- просмотр итогового документа;
- просмотр версий;
- скачивание;
- публикация.

## 11.3. Frontend engineering requirements
Frontend должен использовать:
- типизированный API client;
- TanStack Query для работы с backend data lifecycle;
- React Hook Form + Zod для форм и review payloads;
- shadcn/ui для базовых компонентов;
- Tailwind CSS для layout и theme layer.

---

## 12. Parsing и canonical document model

## 12.1. Общий принцип
Все исходные документы должны быть приведены к canonical internal representation.

## 12.2. Canonical document model должен содержать
- doc_id;
- source_path;
- version;
- file_type;
- metadata profile;
- structure tree;
- content blocks;
- extracted tables;
- section summaries;
- quality flags.

## 12.3. Parsing rules by format

### 12.3.1. PDF
- text extraction через PyMuPDF;
- scanned PDF через OCRmyPDF + Tesseract;
- выделение логических блоков;
- page and section mapping.

### 12.3.2. DOCX
- headings;
- paragraphs;
- tables;
- lists;
- appendices.

### 12.3.3. XLS/XLSX
- workbook metadata;
- worksheets;
- logical table ranges;
- semantic row records;
- column semantics.

### 12.3.4. PPT/PPTX
- presentation metadata;
- slides;
- slide titles;
- bullet content;
- notes;
- sections.

---

## 13. Генерация документов

## 13.1. Общий принцип
Длинные документы генерируются как управляемое дерево артефактов, а не как единый текст.

## 13.2. Template Compiler
Каждый шаблон должен быть предварительно преобразован в:
- template spec;
- section contracts;
- validation rules;
- assembly rules.

## 13.3. Authoring sequence
Общая последовательность:
1. template resolution;
2. methodology interpretation;
3. outline generation;
4. outline approval;
5. section-by-section drafting;
6. local review;
7. chapter synthesis;
8. global consistency review;
9. final approval;
10. deterministic assembly;
11. save/export.

## 13.4. Section packet
Каждый writer agent должен получать только section packet.
Section packet включает:
- section contract;
- local objective;
- project context;
- evidence pack;
- relevant dependency summaries;
- relevant state excerpts.

## 13.5. Section outputs
Каждый section writer возвращает:
- prose draft;
- section digest.

Section digest содержит:
- entities;
- decisions;
- assumptions;
- constraints;
- covered requirements;
- open questions;
- source refs.

## 13.6. Final assembly
Финальная сборка должна быть детерминированной.
LLM не должен переписывать весь итоговый документ одним большим вызовом.

---

## 14. HITL

## 14.1. Обязательные точки HITL
Система должна поддерживать interrupt/resume на следующих шагах:
- outline approval;
- source conflict resolution;
- low confidence clarification;
- version replacement approval;
- final document approval.

## 14.2. Resume contract
Все resume payloads должны быть строго типизированы Pydantic-схемами.

## 14.3. HITL state rules
После resume процесс должен продолжаться с точки последнего checkpoint без ручного восстановления state.

---

## 15. Хранение данных

## 15.1. PostgreSQL schema domains
В PostgreSQL должны быть выделены логические домены таблиц:
- documents;
- document_versions;
- canonical_documents;
- knowledge_blocks;
- embeddings;
- checkpoints;
- tasks;
- approvals;
- review_events;
- generated_artifacts;
- configuration_library;
- audit_log.

## 15.2. Vector storage
Vector storage реализуется через pgvector.

## 15.3. Metadata filtering
Metadata filters должны использовать SQL/JSONB поля PostgreSQL и не зависеть от внешней proprietary логики.

---

## 16. API и контракты

## 16.1. Основные API endpoints
Минимальный API должен включать:
- запуск ingestion;
- запуск retrieval preview;
- запуск authoring task;
- получение task status;
- получение evidence pack;
- получение draft section;
- resume HITL task;
- approve/reject task;
- получение финального артефакта;
- просмотр версий документов.

## 16.2. Контрактность
Все API payloads должны быть описаны Pydantic-схемами и экспортируемы в OpenAPI.

## 16.3. Frontend-backend contract
Frontend не работает с произвольными JSON-структурами без схем.
Все формы и payloads должны использовать согласованные схемы.

---

## 17. Наблюдаемость и эксплуатация

## 17.1. Минимальные требования
Система должна поддерживать:
- structured JSON logging;
- correlation IDs;
- traceable task lifecycle;
- logging для interrupt/resume;
- audit trail по approvals;
- измеримые metrics по quality и latency.

## 17.2. Обязательные эксплуатационные события
Должны логироваться:
- запуск и завершение task;
- переход между graph nodes;
- retrieval decisions;
- low confidence events;
- human approvals;
- save/export actions;
- parsing failures;
- rerank anomalies.

---

## 18. Безопасность

## 18.1. Общие требования
Система должна работать в закрытом контуре.
Данные не должны передаваться в публичные SaaS-сервисы без отдельного согласования.

## 18.2. Model serving isolation
LLM inference, embeddings и rerank должны обслуживаться self-hosted model services.

## 18.3. MCP security
Все MCP-серверы должны:
- иметь ограниченный scope;
- выполнять только разрешенные операции;
- вести audit trail;
- использовать явные контракты входов/выходов.

## 18.4. Frontend and API security
- аутентификация через корпоративный SSO / OIDC-совместимый механизм;
- авторизация по ролям;
- защита approve/resume endpoints;
- аудит пользовательских действий.

---

## 19. Этапы внедрения

## 19.1. Этап 1 — Core Platform
Состав:
- FastAPI;
- LangGraph;
- PostgreSQL + pgvector;
- vLLM;
- TEI;
- базовый frontend shell;
- FastMCP skeleton.

Цель:
запустить единый стандартизированный каркас платформы.

## 19.2. Этап 2 — Knowledge Factory
Состав:
- parsing stack;
- canonical document model;
- metadata extraction;
- summaries;
- vector indexing.

Цель:
получить устойчивый indexing pipeline.

## 19.3. Этап 3 — Retrieval Fabric
Состав:
- hierarchical retrieval;
- rerank;
- evidence pack builder;
- retrieval MCP.

Цель:
получить production-grade retrieval layer.

## 19.4. Этап 4 — Authoring Workflow
Состав:
- template compiler;
- section authoring engine;
- review flows;
- HITL UI;
- deterministic assembly.

Цель:
получить рабочую систему генерации документов.

## 19.5. Этап 5 — Governance & Quality
Состав:
- quality evaluation;
- drift monitoring;
- audit dashboards;
- review analytics.

Цель:
получить управляемую production-систему.

---

## 20. Критерии приемки

## 20.1. По платформе
- LangGraph является единственным orchestration runtime;
- FastMCP используется для всех MCP-серверов;
- PostgreSQL + pgvector покрывают state, metadata и vectors;
- frontend использует согласованный React stack.

## 20.2. По retrieval
- retrieval является иерархическим;
- evidence pack собирается стандартным образом;
- rerank включен в authoring path.

## 20.3. По authoring
- документы создаются section-by-section;
- HITL работает через interrupt/resume;
- итоговый документ собирается детерминированно;
- source traceability сохраняется.

## 20.4. По эксплуатации
- задачи можно безопасно возобновлять после interrupt;
- state сохраняется в PostgreSQL;
- все критические действия аудируются.

---

## 21. Стандарты, которые команда обязана соблюдать

1. Оркестрация — только LangGraph.
2. MCP — только FastMCP.
3. HTTP backend — только FastAPI.
4. Data contracts — только Pydantic.
5. Frontend base stack — React + TS + Vite + shadcn/ui + Tailwind + TanStack Query + RHF + Zod.
6. Primary storage — PostgreSQL + pgvector.
7. LLM serving — vLLM.
8. Embeddings and rerank — TEI.
9. Parsing stack — PyMuPDF / OCRmyPDF / python-docx / openpyxl / python-pptx.
10. Бизнес-логика не должна быть спрятана в промптах или интеграционных glue scripts без явного graph/state representation.

---

## 22. Следующий уровень детализации

Следующим документом после данного ТЗ должен стать архитектурный blueprint, включающий:
- список сервисов и их репозиториев;
- точные Pydantic-схемы;
- перечень LangGraph workflows и subgraphs;
- перечень MCP-серверов и tool contracts;
- PostgreSQL schema design;
- API contract catalog;
- frontend screen map;
- deployment topology для dev / stage / prod.

