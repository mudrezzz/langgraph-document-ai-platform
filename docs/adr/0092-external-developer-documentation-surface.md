# ADR-0092: External developer documentation surface

- Status: Accepted
- Date: 2026-04-29

## Context

The backend/framework foundation reached the production-ready stage (Increment 32), but the input for an external developer was spread out between `README.md`, runbooks and ADR.

To integrate the reusable library and manual demo verification (including binary parsers PDF/PPTX), you need a single, short and operationally practical documentation surface.

## Solution

1. Added a single external docs entrypoint:
   - `docs/developer_guide/README.md`.
2. The documentation is divided into 4 practical layers:
- `quickstart.md` (bootstrap + first smoke);
- `manual_demo_checks.md` (manual proof PDF/PPTX + multifile demo report);
   - `extension_recipes.md` (workflow/tool/MCP/persistence extension path);
- `operations_and_release.md` (release-gate and full pytest gate).
3. An explicit navigation section for the new developer guide has been added to `README.md`.
4. Added docs-contract test, which checks for the presence of key sections and critical links.

## Consequences

Pros:

- an external developer receives a predictable onboarding path without reading the entire ADR archive;
- manual validation of binary parsing path (PDF/PPTX) becomes reproducible;
- the risk of desynchronization between scripts, runbooks and external documentation is reduced.

Cons:

- a new documentation surface is added, which needs to be supported synchronously with runtime contracts;
- some of the information is duplicated with `README.md` and runbooks, which requires contract tests for relevance.
