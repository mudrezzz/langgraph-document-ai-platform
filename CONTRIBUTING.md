# Contributing Guide

Thank you for contributing to `langgraph-document-ai-platform`.

## 1. Scope

This repository evolves as a framework-first platform:

- typed contracts (`schemas`)
- workflow/runtime (`framework`, `application`)
- adapters (`infra`)
- service boundaries (`apps/api`, `apps/mcp_*`)

Change priority: reproducibility, backward-compatible contracts, and observability.

## 2. Why your contribution matters

Contributions to this project create a publicly verifiable engineering track:

- work is visible in issue and PR history;
- changes are validated through tests/smoke checks and review;
- impact is visible in onboarding/docs/examples/packaging/CI quality.

Good places to start:

- `good first issue` for narrow newcomer-friendly tasks;
- `help wanted` for tasks where external help is especially useful;
- `community` for contributor-experience and process improvements.

For vibe-coders:

- this is an open OSS project where you can start with small tasks and produce verifiable results quickly;
- recommended progression path: `docs -> examples -> packaging -> CI -> deeper framework tasks`;
- fast iterations are welcome, but quality is enforced through checks and review;
- in this project, "token contribution" means contribution via AI agents (vibe-coding), not financial donations.
- for local agent setup, you can import GitHub-hosted `SKILL.md/AGENT.md` using `backend/scripts/import_agent_skill.py` (see `docs/developer_guide/vibecoder_skill_import.md`).

AI-assisted contribution policy:

- AI-assisted PRs are accepted by the same bar as any PR: clear scope, reproducible checks, review-ready diff;
- contribution style (manual vs AI-assisted) does not change roadmap priority and does not auto-accelerate merges;
- security and governance requirements are mandatory for all contributors (`SECURITY.md`, contract safety rules).

## 3. Contribution flow

1. Open an issue with a short proposal (problem -> scope -> expected behavior).
2. Prepare changes in a dedicated branch.
3. Update documentation and `docs/DOCS_BACKLOG.md` together with code changes.
4. Run minimal required checks (see below).
5. Open a PR with a short changelog and known risks.
6. For contributor-funnel slices, align scope and DoD with `docs/developer_guide/oss_contributor_funnel_program.md`.

## 4. First-time contributors

If this is your first contribution, start in the safe zone:

- docs (`README`, `developer_guide`, `DOCS_BACKLOG`);
- examples (`agent_examples` docs/tests);
- packaging metadata (`backend/packages/*`).

Recommended first-PR path:

1. Pick an issue labeled `good first issue` or `docs`.
2. Confirm scope in an issue comment before implementation.
3. Keep changes narrow: one PR equals one task.
4. If you touch public contracts, mark the PR with `needs maintainer review`.
5. After 1-2 docs/examples PRs, move to `packaging` or `ci` tasks with verifiable impact.

## 5. Required checks

Minimum before PR:

1. `bash backend/scripts/postgres_migrate.sh`
2. `bash backend/scripts/smoke_retrieval_api.sh`
3. `bash backend/scripts/smoke_release_gate.sh --gate-profile stage`
4. `pytest backend/tests -q` (or targeted subset + explicit explanation in PR)

If changes affect MCP/authoring/indexing paths, include corresponding smoke checks.

For docs/examples/packaging-only PRs (without runtime/API changes), a reduced check set is acceptable:

1. `python -m pytest -q backend/tests/unit/test_developer_guide_contracts.py`
2. targeted tests only for the affected example/module (if applicable)
3. explicit PR note that full smoke was not run because contracts/runtime were not changed

## 6. Contract safety rules

- Do not change public contracts without updating:
  - `docs/developer_guide/public_contract_surface.md`
  - `docs/developer_guide/api_reference.md` and/or `docs/developer_guide/mcp_reference.md`
- For schema changes, use additive migrations.
- Do not break latest/history semantics for canonical/versioned stores.

## 7. Commit and PR style

- Commit messages should be short and specific (`docs: ...`, `feat: ...`, `fix: ...`).
- Every PR must include:
  - what changed;
  - how it was validated;
  - what risks/limitations remain.

## 8. Communication

- Respect review feedback.
- For disputed architecture decisions, add or update an ADR.
- For contributor-experience feedback and periodic updates, use `FEEDBACK.md` and `docs/project_update_template.md`.

## 9. Code of Conduct

This project follows `CODE_OF_CONDUCT.md`.
