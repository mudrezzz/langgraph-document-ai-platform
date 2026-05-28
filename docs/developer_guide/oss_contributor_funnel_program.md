# OSS Contributor Funnel Program (Increment 33)

Date: 2026-05-26
Status: Planned
Scope: community/onboarding/documentation packaging without changing backend public contracts.

## 1. Goal

Reduce the entry threshold for external users and contributors without breaking the production-first positioning of the project.

The program closes the path:

`value -> first demo -> question -> issue -> first PR -> return contributor`.

## 2. Boundaries and restrictions

1. Do not change stable API/MCP contracts without maintainer review and synchronization:
   - `docs/developer_guide/public_contract_surface.md`
   - `docs/developer_guide/api_reference.md`
   - `docs/developer_guide/mcp_reference.md`
2. Synchronize all docs changes via `docs/DOCS_BACKLOG.md`.
3. Do not delete Production smoke/release path; just rearrange the priorities of onboarding entrypoints.
4. Communication with contributors within the framework of `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `SECURITY.md`, `SUPPORT.md`.

## 3. Iteration plan and slices

## Iteration 33.1 (P0): Foundation Fixes

Duration: Day 1-5.

Slice 33.1.1: License/package consistency
- Update `backend/packages/pyproject.toml`: `license = { text = "Apache-2.0" }`.
- Check consistency claims in root `README.md`.
- Result: there is no discrepancy between the root license and package metadata.

Slice 33.1.2: Package README
- Add `backend/packages/README.md`.
- Enable blocks: `Install`, `Included`, `Not Included`, `Minimal example`.
- Result: package metadata `readme = "README.md"` is valid and useful for external users.

Slice 33.1.3: No-infra first success path
- Add `2-Minute Demo: No Docker, No Postgres` block to root README.
- Base: `agent_examples/run_example.py --pattern retrieval_first` (+ `--dry-run`).
- Result: first launch without FastAPI/PostgreSQL/Celery/Redis/MCP.

Slice 33.1.4: Contribution entrypoint cleanup
- Fix broken/ambiguous docs links in `CONTRIBUTING.md`.
- Add section `First-time contributors` with a safe task area (docs/examples/packaging).
- Result: a clear, safe path for the first PR without diving into the entire runtime.

## Iteration 33.2 (P1): Contributor Funnel

Duration: Day 6-14.

Slice 33.2.1: GitHub templates
- Add `.github/ISSUE_TEMPLATE/` (bug/documentation/feature/question).
- Add `.github/pull_request_template.md`.
- Result: structured inputs issue/PR.

Slice 33.2.2: Labels and triage baseline
- Add labels to a set of technical specifications (`docs`, `examples`, `ci`, `packaging`, `community`, `needs maintainer review`, `blocked`, `security`, etc.).
- Result: each new issue receives a type and triage status.

Slice 33.2.3: Initial public backlog
- Create 15-20 issues; minimum 8 mark `good first issue`.
- For each task: `Context`, `Scope`, `Suggested files`, `Acceptance criteria`, `Notes for first-time contributors`.
- Result: public task queue for external contribution.

## Iteration 33.3 (P2): Public Front Door

Duration: Day 15-21.

Slice 33.3.1: README restructure
- Rebuild the README in order: who-for, when-not-to-use, 2-minute demo, example output, architecture, production path, docs map, contributing, license.
- Result: quick success to deep production documentation.

Slice 33.3.2: Positioning clarity
- Add comparison/use-case table (`Need / Use this project? / Why`).
- Result: honest user qualification and fewer untargeted requests.

Slice 33.3.3: Repository discoverability
- Add GitHub topics on actual features (<=20).
- Result: improved discoverability without misrepresentation.

## Iteration 33.4 (P2): Community Messaging + Feedback Loop

Duration: Day 22-30.

Slice 33.4.1: Contributor motivation copy
- Add `Why contribute` block to README/CONTRIBUTING:
- public OSS track as a verifiable engineering contribution;
- the opportunity to express yourself through real merged changes.
- Result: clear motivation for first-time contributors.

Slice 33.4.2: Token support policy
- Add a neutral block about voluntary support of the project with “tokens” (if the maintainer confirms the channel).
- Fix restrictions: no pay-to-prioritize, no feature guarantees, no bypass security/governance.
- Result: project support without conflict with roadmap governance.

Slice 33.4.3: Updates and feedback tracker
- Add template `Project update` (once every 2 weeks).
- Add `FEEDBACK.md` with fields from the TK.
- Result: system collection of onboarding blockers and their transfer to the backlog.

## 4. Definition of Done (30 days)

1. README shows no-infra demo before production setup.
2. Package/license metadata are agreed upon.
3. Added issue/PR templates.
4. A backlog of 15+ public issues, 8+ `good first issue` has been generated.
5. `CONTRIBUTING.md` contains the first-time contributor path.
6. Added GitHub topics.
7. There is at least 1 public update and 1 external technical post draft.
8. Feedback tracker launched.

## 5. Mapping to Backlogs

- Implementation track: `BACKLOG.md` -> `Increment 33: OSS Contributor Funnel and Community Readiness`.
- Documentation track: `docs/DOCS_BACKLOG.md` -> `DOC-036..DOC-044`.
