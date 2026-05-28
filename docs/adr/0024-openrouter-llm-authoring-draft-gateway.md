# ADR-0024: OpenRouter LLM Gateway for authoring draft

- Status: Accepted
- Date: 2026-04-20

## Context

After `Increment 18`, the authoring flow only worked in deterministic mode (`retrieval -> draft -> artifact`) and was useful as a technical outline, but looked too static for the demo.

It was necessary:

- connect a real LLM without breaking the current API;
- maintain predictability of regression tests;
- add controlled fallback for `prod`-compatible circuit.

## Solution

1. Add OpenRouter chat gateway to the infra layer:
   - `infra/openrouter/OpenRouterChatModelGateway`;
- integration through the existing `IChatModelGateway` contract.
2. Expand the authoring API contract with the `draft_strategy` field:
- `auto` (uses LLM if included in env);
- `deterministic` (forced without LLM);
- `llm` (forced via LLM).
3. Enter the LLM runtime env configuration:
   - `APP_LLM_ENABLED`, `APP_LLM_PROVIDER`, `APP_LLM_STRICT`;
   - `OPENROUTER_API_KEY`, `OPENROUTER_MODEL`, `OPENROUTER_BASE_URL`, `OPENROUTER_TIMEOUT_SEC`.
4. Add safe fallback:
- if `APP_LLM_STRICT=false` and an error, the gateway draft is built using deterministic logic;
- in the metadata of the artifact it is written `draft_generation_mode` and the reason for fallback.
5. Add a separate external real LLM test:
   - `backend/tests/integration/test_authoring_openrouter_external.py`;
- runs only when `RUN_EXTERNAL_LLM_TESTS=1`.

## Consequences

Pros:

- demo authoring became “live” thanks to real text generation;
- API remains backward compatible (default `draft_strategy=auto`);
- the regression suite remains deterministic (`draft_strategy=deterministic` in regular integration/e2e tests).

Cons:

- added dependency on external LLM provider for external smoke;
- draft quality depends on the selected model and network stability;
- there is no multi-step authoring cycle and reviewer loop yet.
