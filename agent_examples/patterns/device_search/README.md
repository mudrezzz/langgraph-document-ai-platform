# device_search - equipment selection agent

Accepts requests in colloquial language (“I need a tablet for reading up to 25,000 rubles.”)
and returns an analytical Markdown report: ranking devices with ratings
according to criteria, links to sources and excerpts from real reviews.

Free search via DuckDuckGo - no API key needed.
Only `OPENROUTER_API_KEY` is required for LLM calls.

---

## Architecture

Three consecutive `BaseWorkflow` with two HITL pauses between them:

```
[Phase 1] DevicePlanningWorkflow
parse_intent - parses the request: device type, budget, goals
map_criteria - decomposes goals into measurable technical criteria

↓ HITL-1: display criteria → confirm or adjust
when adjusted, Phase 1 restarts with clarification

[Phase 2] DeviceResearchWorkflow
search_listings - searches for candidates via DuckDuckGo
gather_evidence - collects benchmarks and reviews for each criterion
enrich_reviews - finds customer reviews, maps to criteria
score_and_compare - scores each device for each criterion

↓ HITL-2: showing rankings with numbers → confirm or leave a comment

[Phase 3] DeviceReportWorkflow
generate_report — generates a Markdown report
```

All three workflows share one `DeviceSearchEventSink` -
a single timeline of node execution is accumulated in memory and printed at the end.

---

## Key Concepts

### Criteria with measurability

Each criterion is labeled `measurability`:

- `searchable` - ​​can be checked through search (ppi, RAM, battery capacity).
For such criteria, the agent actually looks for benchmarks and reviews.
- `inferred` - ​​subjective or not directly verifiable
(comfort to hold, design, ecosystem).
These criteria are included in the evaluation and report, but search queries for them
are not done - there are no objective sources on them.

### Evidence base

Each evaluation (`CriterionScore`) contains a list of `evidence`:
Source URL, Title, Relevant Snippet, Type
(`benchmark/expert_review/user_review`) and confidence.

With HITL-2, the agent does not just show “the screen is not good”,
and the real measurement with threshold and reference:

```
✗ Screen quality: 4.2/10 [required: ppi >= 227, IPS yes]
→ Resolution 1280x800, 189 ppi - significantly below the 227 ppi threshold. TFT matrix.
source: https://gsmarena.com/lenovo_tab_m10-9616.php
```

### Reasoning route

`DeviceSearchState.reasoning_trace` — list of entries, one for each node:

```json
[
{ "node": "parse_intent", "device_type": "tablet", "budget_rub": 25000 },
  { "node": "map_criteria", "criteria": [...] },
  { "node": "search_listings",
"queries_used": ["tablet ppi display up to 25000..."],
    "raw_results_count": 30,
    "will_score": ["Samsung Tab A9", "Xiaomi Pad 6"],
"excluded_from_scoring": [{"name": "Teclast T30", "reason": "position > 4"}] },
  { "node": "gather_evidence",
"criteria_skipped_inferred": ["Comfort in hand"],
    "evidence_items_total": 48 },
  { "node": "score_and_compare", "ranking": [...] }
]
```

The trace ends up in the final JSON under the key `reasoning_trace`.

---

## File structure

```
device_search/
├── agent.py # DeviceSearchAgent - orchestration of three phases + two HITL thresholds
├── workflow.py     # DevicePlanningWorkflow, DeviceResearchWorkflow, DeviceReportWorkflow
│ # + _DeviceSearchHandlersMixin with seven node handlers
├── state.py # Pydantic contracts: DeviceSearchState, ConsumerCriterion,
│                   # CriterionScore, EvidenceItem, DeviceScore, HITLState
├── search_tools.py # DuckDuckGo-wrappers: listings, benchmarks, reviews
├── prompts.py # Six LLM prompts (parse_intent → generate_report)
├── event_sink.py # DeviceSearchEventSink — per-node timings, timeline
├── config.py # DeviceSearchConfig - reads env vars
├── main.py # Entry point with CLI flags
└── sample_input/
└── query.txt # Default query for quick start
```

---

## Launch

### Quick start

```bash
export OPENROUTER_API_KEY="sk-or-..."
export OPENROUTER_MODEL="anthropic/claude-3-5-haiku" # optional

.venv/bin/python agent_examples/patterns/device_search/main.py \
--query "You need a tablet for reading books and browsing, budget up to 25,000 rubles"
```

### Automatic mode (without HITL pauses)

```bash
.venv/bin/python agent_examples/patterns/device_search/main.py \
--query "Reading tablet needed" \
  --non-interactive
```

### Through a shared runner

```bash
.venv/bin/python agent_examples/run_example.py --pattern device_search
```

---

## Parsing the resulting JSON

The agent prints the result to stdout. Key fields:

| Field | What contains |
|---|---|
| `reasoning_trace` | Full route: what I was looking for, what I missed, why |
| `ranking[i].criterion_scores[j].assessment` | Valuation with real numbers |
| `ranking[i].criterion_scores[j].evidence` | Sources with URLs and snippets |
| `ranking[i].review_insights` | Observations from real reviews |
| `node_timeline` | Timings of each node (ms) |
| `node_failures` | Nodes that failed |
| `unresolved_gaps` | What could not be found or confirmed |
| `confidence` | Average confidence by evidence (0–1) |
| `final_report` | Final Markdown report |

Example: view the trace from the command line:

```bash
.venv/bin/python agent_examples/patterns/device_search/main.py \
  --query "..." --non-interactive \
  | python3 -c "
import sys, json
r = json.load(sys.stdin)
for step in r['reasoning_trace']:
    print(json.dumps(step, ensure_ascii=False, indent=2))
"
```

---

## What to change first

**Device type** - just change the query (`--query "laptop for work up to 80,000 rubles."`),
the agent himself will parse the category and translate it into English for search.

**Quality requested** — `search_tools.py::search_marketplace_listings`.
Currently targeting ixbt.com, 4pda, ichip, gsmarena. Add your domains or
change requests for a specific marketplace.

**Criteria** - `prompts.py::MAP_CRITERIA_PROMPT`. If you need specific
technical parameters (for example, for B2B purchases) - specify the prompt.

**Number of candidates** - `workflow.py::MAX_DEVICES_TO_SCORE` (currently 4).
More candidates → more search queries → longer execution time.

**LLM-model** – variable `OPENROUTER_MODEL`. Stronger model
(claude-opus, gpt-4o) gives more accurate estimates, weak (haiku, gemini-flash) -
faster and cheaper.
