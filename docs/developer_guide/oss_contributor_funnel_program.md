# OSS Contributor Funnel Program (Increment 33)

Date: 2026-05-28  
Status: Active  
Scope: community/onboarding/documentation/packaging improvements without changing backend stable public contracts.

## 1. Goal

Reduce the entry threshold for external users and contributors while preserving the production-first position of the project.

Target path:

`value -> first demo -> question -> issue -> first PR -> repeat contributor`.

## 2. Boundaries and restrictions

1. Do not change stable API/MCP contracts without maintainer review and synchronization:
   - `docs/developer_guide/public_contract_surface.md`
   - `docs/developer_guide/api_reference.md`
   - `docs/developer_guide/mcp_reference.md`
2. Sync every documentation change through `docs/DOCS_BACKLOG.md`.
3. Do not remove production smoke/release paths; only reorder onboarding entrypoints.
4. Communication and contribution rules are governed by:
   - `CONTRIBUTING.md`
   - `CODE_OF_CONDUCT.md`
   - `SECURITY.md`
   - `SUPPORT.md`
5. "Token contribution" in this project means contribution done with AI coding agents (vibe-coding), not financial/token donations.

## 3. Iteration plan and slice tracking

| Iteration | Window (30-day program) | Focus | Slices | Status |
|---|---|---|---|---|
| 33.1 | Day 1-5 | Foundation fixes | 33.1.1, 33.1.2, 33.1.3, 33.1.4 | Done |
| 33.2 | Day 6-14 | Contributor funnel | 33.2.1, 33.2.2, 33.2.3 | Done |
| 33.3 | Day 15-21 | Public front door | 33.3.1, 33.3.2, 33.3.3 | Done |
| 33.4 | Day 22-30 | Community messaging + feedback loop | 33.4.1, 33.4.2, 33.4.3 | Done |
| 33.8 | Day 30+ hardening | Program operationalization and KPI baseline | 33.8.1 | In Progress |

## 4. Slice register (completed and active)

### Iteration 33.1 (P0)

Slice 33.1.1: License/package consistency  
DoD:
- package metadata and root license are aligned;
- no contradiction in package install docs.

Slice 33.1.2: Package README  
DoD:
- `backend/packages/README.md` includes install/scope/minimal usage;
- package metadata points to a valid README.

Slice 33.1.3: No-infra first success path  
DoD:
- root README contains `2-Minute Demo: No Docker, No Postgres`;
- first-run path works without FastAPI/PostgreSQL/Celery/Redis/MCP.

Slice 33.1.4: Contribution entrypoint cleanup  
DoD:
- `CONTRIBUTING.md` contains first-time contributor safe path;
- broken or ambiguous links are removed.

### Iteration 33.2 (P1)

Slice 33.2.1: GitHub templates  
DoD:
- issue forms and PR template exist and are usable.

Slice 33.2.2: Labels and triage baseline  
DoD:
- working label taxonomy is defined and applied;
- new issues can be typed and triaged consistently.

Slice 33.2.3: Initial public backlog  
DoD:
- at least 15 public issues created;
- at least 8 issues marked `good first issue`;
- each issue has context, scope, and acceptance criteria.

### Iteration 33.3 (P2)

Slice 33.3.1: README restructure  
DoD:
- root README follows front-door order from quick success to deep docs.

Slice 33.3.2: Positioning clarity  
DoD:
- use-case fit table added (`Need / Use this project? / Why`).

Slice 33.3.3: Repository discoverability  
DoD:
- capability-aligned repository topics added (<=20).

### Iteration 33.4 (P2)

Slice 33.4.1: Contributor motivation copy  
DoD:
- README/CONTRIBUTING include `Why Contribute` and growth path.

Slice 33.4.2: AI-assisted contribution policy  
DoD:
- policy explicitly states equal quality bar for manual and AI-assisted contributions;
- policy explicitly states no financial token donation semantics.

Slice 33.4.3: Updates and feedback tracker  
DoD:
- `FEEDBACK.md` is added;
- `docs/project_update_template.md` is added;
- links are present in front-door contributor routes.

### Iteration 33.8 (P0 hardening)

Slice 33.8.1: Program operationalization and KPI baseline  
DoD:
- this program document is updated to an operational state (status, iteration table, slice DoD);
- KPI section has a measurable baseline-ready input/output list;
- links to this program are synchronized in contributor-facing docs.

## 5. KPI baseline (input/output)

Track these metrics weekly (UTC week):

1. Input funnel:
   - `issues_opened_total` (all new issues);
   - `good_first_issue_open_total`;
   - `community_labeled_issues_total`;
   - `first_time_contributor_pr_open_total`.
2. Throughput/output:
   - `issues_closed_total`;
   - `good_first_issue_closed_total`;
   - `merged_pr_total`;
   - `first_time_contributor_pr_merged_total`.
3. Cycle-time and quality:
   - `pr_time_to_first_review_hours` (median);
   - `pr_open_to_merge_hours` (median);
   - `docs_contract_failures_total` (count per week);
   - `reopened_issue_total` (quality signal).

## 6. Program-level Definition of Done (30-day cycle)

1. README shows no-infra demo before production setup.
2. Package/license metadata are aligned.
3. Issue/PR templates are active.
4. Public backlog exists with 15+ issues and 8+ `good first issue`.
5. `CONTRIBUTING.md` has first-time contributor path.
6. Repository topics are capability-aligned.
7. Feedback loop is active (`FEEDBACK.md` + update template).
8. KPI baseline is defined and used for weekly program review.

## 7. Mapping to Backlogs

- Implementation track: `BACKLOG.md` -> `Increment 33: OSS Contributor Funnel and Community Readiness`.
- Documentation track: `docs/DOCS_BACKLOG.md` -> `DOC-036..DOC-046`.
