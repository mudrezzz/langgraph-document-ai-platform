# Maintainer Playbook (Docs)

Update date: 2026-05-27
Status: Active (Increment 33 triage baseline)

The document describes a process for supporting documentation as a living contract surface.

## 1. Maintainer responsibilities

1. Keep docs in sync with code.
2. Protect stable contracts (`public_contract_surface`).
3. Provide a predictable review/merge process.

## 2. Intake and triage

For each docs issue, define:

1. Type:
   - `contract_update`
   - `new_guide`
   - `bugfix/clarification`
2. Priority:
- `P0`: affects stable contract/release path
- `P1`: affects onboarding/operations
- `P2`: improved navigation/examples
3. Scope:
- what documents are affected?
- is a backlog item necessary?

## 3. Change workflow

1. Make a change in docs.
2. Update `docs/DOCS_BACKLOG.md`:
   - `Status`
   - `Last Update`
   - `Notes`
3. If the change affects stable contracts:
- update `public_contract_surface.md`
- update `api_reference.md` and/or `mcp_reference.md`
4. Run docs checks:
   - `.venv/bin/pytest -q backend/tests/unit/test_developer_guide_contracts.py`
5. Commit/PR with short changelog.

## 4. Docs review rules

Review is not skipped if:

1. There are docs edits, but `docs/DOCS_BACKLOG.md` is not updated.
2. The public API/MCP behavior has changed, but the reference docs have not been updated.
3. Added a new guide without connection to the role-based entrypoint (`docs/developer_guide/README.md`).

Review checklist:

1. Factual correctness of the code/scripts.
2. There are no imaginary possibilities.
3. Stability boundaries are clearly indicated.
4. There is a migration note for breaking/deprecation changes.

## 5. Release docs cadence

For each backend/framework increment:

1. Update key docs (README/architecture/developer_guide if necessary).
2. Synchronize the backlog.
3. Record the changelog in the PR description.

Periodically (for example, once every 2-4 weeks):

1. Check the consistency of cross-links.
2. Check the relevance of run commands from `backend/scripts/README.md`.
3. Review P1/P2 backlog when a new scope appears.

## 6. Escalation policy

Escalate to architectural review if:

- breaking change stable contract surface is proposed;
- change of license/governance/security policy is required;
- there is a conflict between ADR and current documentation.

## 7. Definition of done for docs PR

PR is considered ready if:

1. Documentation has been updated to reflect changes.
2. `docs/DOCS_BACKLOG.md` synchronized.
3. Docs tests pass.
4. There is a clear summary of the changes.

## 8. Label taxonomy baseline

Maintainer baseline labels for intake/triage:

- `good first issue`
- `help wanted`
- `docs`
- `examples`
- `ci`
- `packaging`
- `bug`
- `enhancement`
- `question`
- `discussion`
- `needs maintainer review`
- `blocked`
- `security`
- `community`

Rule: each new issue receives at least one label of type (`bug`/`enhancement`/`docs`/`question`) and, if necessary, one workflow label (`needs maintainer review`/`blocked`).

## 9. Triage SLA and status policy

Best-effort SLA:

1. New issue: first reaction/marking within 72 hours.
2. New PR: initial response within 5 working days.
3. Security issue: do not discuss details publicly, redirect to the process from `SECURITY.md`.

Triage status baseline:

- `actionable`
- `needs info`
- `duplicate`
- `not planned`
- `maintainer review`

Minimum for each new issue:

1. label;
2. triage status;
3. short maintainer comment with next step.

Issue closure baseline:

1. `duplicate` -> close with a link to the source issue.
2. `needs info` without response 14-21 days -> close with a comment about the possibility of reopening with data.
3. out-of-scope/support-only requests -> close with an explicit reason and a link to the relevant docs path.
