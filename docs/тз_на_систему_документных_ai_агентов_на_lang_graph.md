# Terms of reference
## System of AI agents for working with project documentation based on LangGraph

## 1. Purpose of the document

This technical specification describes the target architecture, technology stack and principles for implementing an AI agent system for working with project documentation in software implementation projects.

The document records:
- system architecture based on LangGraph;
- standardized technology stack;
- composition of services and boundaries of responsibility;
- approach to hierarchical RAG;
- approach to multi-agent orchestration;
- HITL model;
- requirements for frontend, backend, MCP, data storage and deployment.

The purpose of the document is to minimize the number of non-standardized solutions, reduce the amount of self-written infrastructure and use mature, reusable components that are understandable at the start.

---

## 2. System goals

The system should:
- automate the work of a business analyst with a large array of project documents;
- support processing of documents of different formats and quality;
- provide high-quality retrieval on a multi-level knowledge corpus;
- use methodological guidelines and templates as a normative basis;
- generate new documents using templates;
- update existing documents;
- provide human-in-the-loop at critical stages;
- work in a closed circuit;
- be suitable for scaling and production operation.

---

## 3. Basic architectural principles

### 3.1. LangGraph as a single orchestration runtime
LangGraph is used as the main runtime for:
- stateful agent workflows;
- multi-agent orchestration;
- conditional routing;
- human-in-the-loop;
- interrupt/resume;
- checkpointing and long-lived processes.

### 3.2. Code-based, not visual, orchestration
Orchestration of business logic is implemented by Python code.
The system should not rely on visual low-code orchestrators as the execution core.

### 3.3. LangChain has limited use
LangChain is only allowed as a layer of adapters and ready-made integrations:
- models;
- embeddings;
- vector store adapters;
- retrievers;
- tools wrappers.

LangChain should not be used as a place where critical business logic of the system is hidden.

### 3.4. Minimizing the number of infrastructure components
In the first production version, you should aim for a small number of required services.
The core stack should be compact, predictable, and supported by a small engineering team.

### 3.5. One standard implementation path
For each class of tasks, standard technologies must be recorded.
The team should not choose a new stack for each subsystem.

---

## 4. Mandatory technology stack

## 4.1. Backend
Required backend stack:
- Python 3.12;
- FastAPI;
- LangGraph;
- Pydantic v2;
- FastMCP.

### 4.1.1. Role of Components
- **FastAPI** - HTTP API, webhooks, admin endpoints, runtime endpoints, ingestion endpoints.
- **LangGraph** - orchestration of agent workflows, state machines, multi-agent pipelines, HITL.
- **Pydantic v2** - data schemas, state contracts, validation.
- **FastMCP** - standard for all MCP servers in the system.

## 4.2. Frontend
Required frontend stack:
- React;
- TypeScript;
- Vite;
- shadcn/ui;
- Tailwind CSS;
- TanStack Query;
- React Hook Form;
- Zod.

### 4.2.1. Frontend stack principle
Frontend should be:
- easy to start;
- quick development of internal UI;
- suitable for expansion;
- type safe;
- convenient for forms, tables, review-flow and traceability views.

## 4.3. Storage and database
Required storage stack:
- PostgreSQL;
- pgvector.

### 4.3.1. PostgreSQL is used as
- main transactional database;
- metadata storage;
- checkpoint state storage;
- base for vector search via pgvector;
- basis for auditing, task queues and service tables.

### 4.3.2. The principle of minimizing infrastructure
At the first stage, a separate vector DB is not introduced if PostgreSQL + pgvector covers the volume and latency requirements.

## 4.4. Model serving
Required model serving stack for closed loop:
- vLLM - for generative LLMs;
- Hugging Face Text Embeddings Inference (TEI) - for embeddings and rerank.

### 4.4.1. The role of the model serving layer
- text generation;
- structured output;
- embeddings;
- reranking;
- if necessary, classification and lightweight semantic scoring.

## 4.5. Parsing and extraction
Standard document processing stack:
- PyMuPDF — PDF;
- OCRmyPDF + Tesseract OCR — scanned PDF;
- python-docx — DOCX;
- openpyxl — XLS/XLSX;
- python-pptx — PPT/PPTX.

### 4.5.1. The extraction stack principle
The most standard and mature library is used for each format.
It is not allowed to build key extraction logic on random or poorly controlled tools unless necessary.

## 4.6. API integration and service contract
Interservice contracts:
- HTTP/JSON via FastAPI;
- MCP via FastMCP;
- OpenAPI for typing and contracts;
- Pydantic schemes as a source of truth for payload contracts.

---

## 5. System components

## 5.1. Composition of services
The minimum production circuit should consist of the following services.

### 5.1.1. API Service
Purpose:
- entry point for the UI;
- creation and launch of tasks;
- issuing statuses;
- resume for HITL;
- management of retrieval and authoring request lifecycle.

Technologies:
- FastAPI;
- Pydantic;
- LangGraph runtime integration.

### 5.1.2. LangGraph Orchestrator Service
Purpose:
- execution of agent workflows;
- stateful orchestration;
- checkpointing;
- multi-agent coordination;
- interrupt/resume.

Technologies:
- LangGraph;
- PostgreSQL-based checkpointer.

### 5.1.3. Ingestion Worker Service
Purpose:
- bypassing file sources;
- document parsing;
- normalization;
- metadata extraction;
- summary building;
- chunking;
- upsert in knowledge stores.

Technologies:
- Python;
- FastAPI task endpoints or CLI entrypoints;
- extraction stack;
- PostgreSQL + pgvector.

### 5.1.4. MCP Services
Purpose:
- standardized access of agents to external actions and resources.

All MCP servers are implemented only on FastMCP.

Minimum set of MCP servers:
- Document Repository MCP;
- Retrieval MCP;
- Artifact Writer MCP;
- Review / Approval MCP;
- Configuration Library MCP.

### 5.1.5. Model Serving Services
Purpose:
- inference for LLM;
- embeddings;
- rerank.

Services:
- vLLM;
- TEI.

### 5.1.6. Frontend Application
Purpose:
- launch user tasks;
- viewing statuses;
- review and approval;
- viewing evidence pack;
- view section digests;
- view traceability;
- manual editing and confirmation of artifacts.

---

## 6. Architectural domains

## 6.1. Knowledge Factory
Purpose:
- preparation and indexing of knowledge;
- extraction;
- metadata enrichment;
- summaries;
- chunking;
- indexing.

## 6.2. Retrieval Fabric
Purpose:
- query understanding;
- retrieval planning;
- metadata filtering;
- summary retrieval;
- detailed retrieval;
- rerank;
- evidence pack construction.

## 6.3. Authoring Workflow
Purpose:
- interpretation of methodology;
- template selection;
- outline generation;
- section drafting;
- review;
- consistency checks;
- deterministic assembly.

## 6.4. Governance & Quality
Purpose:
- parsing quality control;
- retrieval quality control;
- output quality control;
- drift monitoring;
- traceability and audit.

---

## 7. Standardized stack by domain

## 7.1. Knowledge Factory
Required components:
- Python 3.12;
- FastAPI or CLI workers;
- PyMuPDF / OCRmyPDF / python-docx / openpyxl / python-pptx;
- Pydantic schemas;
- PostgreSQL + pgvector;
- TEI embeddings.

### 7.1.1. Knowledge Factory outputs
- canonical document JSON;
- metadata profile;
- summary artifacts;
- detailed content blocks;
- vector embeddings;
- indexing records.

## 7.2. Retrieval Fabric
Required components:
- LangGraph subgraphs;
- LangChain retriever adapters;
- PostgreSQL + pgvector;
- TEI rerank;
- FastMCP Retrieval Server.

### 7.2.1. Retrieval principle
Retrieval should not be a single-stage semantic search.
A hierarchical cascade must be used.

## 7.3. Authoring Workflow
Required components:
- LangGraph;
- FastMCP tool layer;
- Pydantic structured outputs;
- FastAPI resume endpoints;
- frontend review UI.

## 7.4. Frontend
Required components:
- React + TypeScript;
- Vite;
- shadcn/ui + Tailwind;
- TanStack Query;
- React Hook Form + Zod.

---

## 8. Hierarchical RAG

## 8.1. General scheme
For all knowledge-intensive scenarios, a hierarchical RAG is used.

Stages:
1. metadata pre-filter;
2. retrieval by summary layer;
3. narrowing candidate documents;
4. retrieval by detailed block layer;
5. rerank;
6. evidence pack assembly.

## 8.2. Knowledge layers
Required index layers:

### 8.2.1. Methodology / Templates Layer
Contains:
- methodological documents;
- templates;
- regulatory guidelines;
- style rules;
- section rules.

### 8.2.2. Summary Layer
Contains:
- document summary;
- section summaries;
- extracted entities;
- decisions;
- assumptions;
- constraints;
- source profiles.

### 8.2.3. Detailed Blocks Layer
Contains:
- structural blocks of documents;
- section-aware chunks;
- table-derived semantic records;
- slide blocks;
- source references.

## 8.3. Chunking
Chunking should be structural, not just dimensional.

Approaches:
- DOCX - by heading hierarchy and tables;
- PDF - by logical blocks and sections;
- XLSX - by sheets, logical tables and rows as semantic units;
- PPTX - by slides and sections.

## 8.4. Rerank
Rerank is required for authoring and complex QA scenarios.
The standard rerank tool is TEI rerank endpoint.

## 8.5. Evidence Pack
Evidence pack should be a standard artifact between retrieval and authoring.

Compound:
- selected sources;
- selected blocks;
- methodology refs;
- template refs;
- unresolved gaps;
- traceability map;
- confidence notes.

---

## 9. LangGraph-first orchestration

## 9.1. General principle
Each complex process is implemented as a LangGraph workflow or subgraph.

### 9.1.1. Not allowed in the system
- hide orchestration logic in the UI;
- hide orchestration logic in prompts without an explicit graph structure;
- build critical processes as long linear chains without state.

## 9.2. Types of graph processes

### 9.2.1. Long-running workflows
Used for:
- ingestion;
- authoring;
- review cycles;
- conflict resolution;
- resumable tasks.

### 9.2.2. Subgraphs
Used for:
- retrieval pack builder;
- section authoring engine;
- template compiler;
- consistency checker;
- review engine.

### 9.2.3. Interrupt-driven workflows
Used for:
- human approval;
- conflict resolution;
- low-confidence cases;
- version replacement approval;
- unresolved evidence gaps.

## 9.3. Checkpointing
Checkpointing is required for all long-lived processes.
State must be saved in PostgreSQL.

## 9.4. Multi-agent orchestration
The multi-agent scheme is implemented as a set of specialized subagents in LangGraph.

Minimum set of agent roles:
- Supervisor;
- Research Agent;
- Retrieval Planner Agent;
- Writer Agent;
- Reviewer Agent;
- Consistency Reviewer;
- Human Gate Agent.

---

## 10. MCP standard

## 10.1. General principle
All MCP servers of the system are implemented only through FastMCP.
Other MCP frameworks are not used in the project.

## 10.2. Required MCP servers

### 10.2.1. Document Repository MCP
Functions:
- reading source documents;
- reading generated artifacts;
- access to canonical representations;
- version-aware read.

### 10.2.2. Retrieval MCP
Functions:
- search by knowledge layers;
- metadata filtering;
- summary retrieval;
- detailed retrieval;
- rerank orchestration;
- issuance of evidence pack.

### 10.2.3. Artifact Writer MCP
Functions:
- recording drafts;
- recording of final documents;
- export to target formats;
- version-aware write.

### 10.2.4. Review / Approval MCP
Functions:
- recording review outcomes;
- registration of human approvals;
- resume payload delivery.

### 10.2.5. Configuration Library MCP
Functions:
- working with a library of standard configurations;
- search for analogues;
- comparison of configurations;
- saving and versioning configuration artifacts.

---

## 11. Frontend

## 11.1. Purpose of the UI
UI is the basic working interface of the analyst and reviewer.
The UI is not where agent logic is executed.

## 11.2. Required UI Sections

### 11.2.1. Task Dashboard
- list of tasks;
- statuses;
- types of tasks;
- filters;
- launching new tasks.

### 11.2.2. Evidence Review Screen
- viewing evidence pack;
- viewing sources;
- traceability;
- unresolved gaps.

### 11.2.3. Outline Review Screen
- view outline;
- confirmation of the structure;
- analyst comments.

### 11.2.4. Section Review Screen
- draft section;
- review issues;
- editing;
- approve / send back.

### 11.2.5. Conflict Resolution Screen
- conflicting sources;
- selection options;
- analyst comment;
- fixation of the decision.

### 11.2.6. Generated Artifacts Screen
- viewing the final document;
- viewing versions;
- download;
- publication.

## 11.3. Frontend engineering requirements
Frontend should use:
- typed API client;
- TanStack Query for working with backend data lifecycle;
- React Hook Form + Zod for forms and review payloads;
- shadcn/ui for basic components;
- Tailwind CSS for layout and theme layer.

---

## 12. Parsing and canonical document model

## 12.1. General principle
All source documents must be converted to canonical internal representation.

## 12.2. Canonical document model must contain
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
- text extraction via PyMuPDF;
- scanned PDF via OCRmyPDF + Tesseract;
- allocation of logical blocks;
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

## 13. Document generation

## 13.1. General principle
Long documents are generated as a managed tree of artifacts rather than as a single text.

## 13.2. Template Compiler
Each template must first be converted to:
- template spec;
- section contracts;
- validation rules;
- assembly rules.

## 13.3. Authoring sequence
General sequence:
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
Each writer agent should only receive the section packet.
Section packet includes:
- section contract;
- local objective;
- project context;
- evidence pack;
- relevant dependency summaries;
- relevant state excerpts.

## 13.5. Section outputs
Each section writer returns:
- prose draft;
- section digest.

Section digest contains:
- entities;
- decisions;
- assumptions;
- constraints;
- covered requirements;
- open questions;
- source refs.

## 13.6. Final assembly
The final build must be deterministic.
The LLM should not rewrite the entire final document in one big call.

---

## 14. HITL

## 14.1. Mandatory HITL points
The system must support interrupt/resume in the following steps:
- outline approval;
- source conflict resolution;
- low confidence clarification;
- version replacement approval;
- final document approval.

## 14.2. Resume contract
All resume payloads must be strongly typed by Pydantic schemas.

## 14.3. HITL state rules
After resume, the process should continue from the last checkpoint without manually restoring the state.

---

## 15. Data storage

## 15.1. PostgreSQL schema domains
In PostgreSQL, logical table domains must be allocated:
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
Vector storage is implemented via pgvector.

## 15.3. Metadata filtering
Metadata filters should use PostgreSQL SQL/JSONB fields and not depend on external proprietary logic.

---

## 16. API and contracts

## 16.1. Basic API endpoints
The minimum API should include:
- launch of ingestion;
- launch retrieval preview;
- launch authoring task;
- getting task status;
- receiving evidence pack;
- receiving a draft section;
- resume HITL task;
- approve/reject task;
- receiving the final artifact;
- viewing document versions.

## 16.2. Contractuality
All API payloads must be described by Pydantic schemas and exported to OpenAPI.

## 16.3. Frontend-backend contract
Frontend does not work with arbitrary JSON structures without schemas.
All forms and payloads must use consistent schemas.

---

## 17. Observability and Operation

## 17.1. Minimum Requirements
The system must support:
- structured JSON logging;
- correlation IDs;
- traceable task lifecycle;
- logging for interrupt/resume;
- audit trail for approvals;
- measurable metrics for quality and latency.

## 17.2. Mandatory operational events
Must be logged:
- starting and completing a task;
- transition between graph nodes;
- retrieval decisions;
- low confidence events;
- human approvals;
- save/export actions;
- parsing failures;
- rerank anomalies.

---

## 18. Security

## 18.1. General requirements
The system must operate in a closed loop.
Data should not be transferred to public SaaS services without separate approval.

## 18.2. Model serving isolation
LLM inference, embeddings and rerank should be served by self-hosted model services.

## 18.3. MCP security
All MCP servers must:
- have a limited scope;
- perform only permitted operations;
- conduct an audit trail;
- use explicit input/output contracts.

## 18.4. Frontend and API security
- authentication via corporate SSO / OIDC-compatible mechanism;
- authorization by roles;
- approve/resume endpoints protection;
- audit of user actions.

---

## 19. Implementation stages

## 19.1. Stage 1 - Core Platform
Compound:
- FastAPI;
- LangGraph;
- PostgreSQL + pgvector;
- vLLM;
- TEI;
- basic frontend shell;
- FastMCP skeleton.

Target:
launch a single standardized platform framework.

## 19.2. Stage 2 - Knowledge Factory
Compound:
- parsing stack;
- canonical document model;
- metadata extraction;
- summaries;
- vector indexing.

Target:
get a stable indexing pipeline.

## 19.3. Stage 3 - Retrieval Fabric
Compound:
- hierarchical retrieval;
- rerank;
- evidence pack builder;
- retrieval MCP.

Target:
get production-grade retrieval layer.

## 19.4. Stage 4 - Authoring Workflow
Compound:
- template compiler;
- section authoring engine;
- review flows;
- HITL UI;
- deterministic assembly.

Target:
get a working document generation system.

## 19.5. Stage 5 - Governance & Quality
Compound:
- quality evaluation;
- drift monitoring;
- audit dashboards;
- review analytics.

Target:
get a managed production system.

---

## 20. Acceptance criteria

## 20.1. By platform
- LangGraph is the only orchestration runtime;
- FastMCP is used for all MCP servers;
- PostgreSQL + pgvector cover state, metadata and vectors;
- frontend uses a consistent React stack.

## 20.2. By retrieval
- retrieval is hierarchical;
- evidence pack is assembled in a standard way;
- rerank is included in the authoring path.

## 20.3. By authoring
- documents are created section-by-section;
- HITL works via interrupt/resume;
- the final document is assembled deterministically;
- source traceability is preserved.

## 20.4. Instructions for use
- tasks can be safely resumed after interruption;
- state is saved in PostgreSQL;
- all critical actions are audited.

---

## 21. Standards that the team must comply with

1. Orchestration - LangGraph only.
2. MCP - FastMCP only.
3. HTTP backend - FastAPI only.
4. Data contracts - Pydantic only.
5. Frontend base stack — React + TS + Vite + shadcn/ui + Tailwind + TanStack Query + RHF + Zod.
6. Primary storage — PostgreSQL + pgvector.
7. LLM serving — vLLM.
8. Embeddings and rerank — TEI.
9. Parsing stack — PyMuPDF / OCRmyPDF / python-docx / openpyxl / python-pptx.
10. Business logic should not be hidden in prompts or integration glue scripts without explicit graph/state representation.

---

## 22. Next level of detail

The next document after this TOR should be an architectural blueprint, including:
- list of services and their repositories;
- accurate Pydantic diagrams;
- list of LangGraph workflows and subgraphs;
- list of MCP servers and tool contracts;
- PostgreSQL schema design;
- API contract catalog;
- frontend screen map;
- deployment topology for dev/stage/prod.

