# Agent Examples

A catalog of Python agents demonstrating different ways of working with the framework.
Each example is a self-contained pattern: its own folder, its own `agent.py`, its own README.

---

## Pattern catalog

| Pattern | What shows | Execution model | Infrastructure |
|---|---|---|---|
| [`retrieval_first`](#retrieval_first) | Document Search + EvidencePack | In-process (direct workflow call) | Not needed |
| [`authoring_first`](#authoring_first) | Creating an artifact via API | API-driven (HTTP → framework) | PostgreSQL |
| [`hitl_gate`](#hitl_gate) | Asynchronous review cycle with HITL | API-driven async + polling | PostgreSQL + async worker |
| [`device_search`](#device_search) | Product search by request in spoken language | In-process, three phases, two HITL | Not needed |

---

## Architectural context

Patterns are divided into two classes according to their execution model:

**In-process** - the agent imports the framework as a library and calls
`workflow.invoke()` directly inside one Python process. No HTTP needed
there are no network delays, the execution trace is completely visible in memory.
This is the target model for new agents.

**API-driven** - the agent communicates with the deployed backend via HTTP (`/start`,
`/task/{id}`, `/hitl/submit`). You need PostgreSQL and, for the async path, a worker.
`authoring_first` and `hitl_gate` are still in this mode, a replatform is planned.

---

## Patterns

### retrieval_first

A minimal search agent for a documentary corpus. Accepts text
request, runs it through `RetrievalWorkflow` (in-process), returns
`EvidencePack` - ​​found blocks of documents with sources and confidence.

Shows: how to build an agent as a Python composition on top of the framework
contracts without a single HTTP call.

```
Request → RetrievalWorkflow.invoke() → EvidencePack (blocks, sources, gaps)
```

**Launch:**
```bash
.venv/bin/python agent_examples/patterns/retrieval_first/main.py
```

[Detailed README →](patterns/retrieval_first/README.md)

---

### authoring_first

Artifact creation agent: asks a question to the framework API, waits
synchronous response, returns a finished artifact with traceability sections.

Shows: how `/authoring/start` → `/task/{id}` → `/artifact/{id}` works
cycle; how to get a final document with full traceability.

```
Request → POST /authoring/start → GET /task/{id} → GET /artifact/{id} → Artifact
```

**Launch:**
```bash
bash backend/scripts/postgres_up.sh
bash backend/scripts/postgres_migrate.sh
.venv/bin/python agent_examples/run_example.py --pattern authoring_first
```

[Detailed README →](patterns/authoring_first/README.md)

---

### hitl_gate

Agent with an asynchronous review cycle. Starts a task via `start_async`,
pollit status, with `waiting_human` submits the reviewer's decision (`needs_changes`
or `approve`), repeats until completion.

Shows: how to integrate reviewer-in-the-loop into an agent; how to manage
idempotent HITL solutions via API.

```
start_async → poll(waiting_human) → submit_hitl_review → poll → … → completed
```

**Launch:**
```bash
bash backend/scripts/postgres_up.sh
bash backend/scripts/postgres_migrate.sh
bash backend/scripts/async_up.sh
.venv/bin/python agent_examples/run_example.py --pattern hitl_gate --hitl-decisions needs_changes,approve
```

[Detailed README →](patterns/hitl_gate/README.md)

---

### device_search

Agent for searching and selecting equipment upon request in spoken language. Takes the request
like “you need a tablet for reading up to 25,000 rubles.” and returns a Markdown report
with ranking of devices, ratings based on criteria and links to sources.

Shows: three-phase orchestration on `BaseWorkflow`; two interactive
HITL threshold; evidence base (each assessment is supported by real URLs);
`WorkflowNodeEventSink` for node timing.

```
parse_intent → map_criteria
↓ HITL-1: harmonization of criteria
search_listings → gather_evidence → enrich_reviews → score_and_compare
↓ HITL-2: harmonization of results
generate_report
```

**Launch (interactive):**
```bash
export OPENROUTER_API_KEY="sk-or-..."
.venv/bin/python agent_examples/patterns/device_search/main.py \
--query "Need a tablet for reading books, budget up to 25,000 rubles"
```

**Start (automatic, without pauses):**
```bash
.venv/bin/python agent_examples/run_example.py --pattern device_search
```

[Detailed README →](patterns/device_search/README.md)

---

## General runner

All patterns can be launched through a single runner:

```bash
.venv/bin/python agent_examples/run_example.py --pattern <name>
```

Available names: `retrieval_first`, `authoring_first`, `hitl_gate`, `device_search`.

Dry-run (no real LLM/API calls):
```bash
.venv/bin/python agent_examples/run_example.py --pattern retrieval_first --dry-run
```

---

## Tests

```bash
# Unit + smoke — retrieval_first
.venv/bin/pytest -q agent_examples/patterns/retrieval_first/tests/test_agent.py

# Contract structure of all patterns
.venv/bin/pytest -q backend/tests/unit/test_agent_examples_contracts.py

# General runner
.venv/bin/pytest -q agent_examples/tests/test_run_example.py
```

---

## Structure

```
agent_examples/
├── run_example.py # general runner
├── common/                  # FrameworkClient, shared utilities
└── patterns/
    ├── retrieval_first/     # in-process document retrieval
    ├── authoring_first/     # API-driven artifact authoring
    ├── hitl_gate/           # async HITL review loop
    └── device_search/       # in-process marketplace search
```
